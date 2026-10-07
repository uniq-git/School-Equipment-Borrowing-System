"""Logic tests that run without MySQL or a display (the database layer is replaced by stubs)."""
import sys
import types
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Stub the modules that need MySQL / SMTP so the pure logic can be imported anywhere.
db = types.ModuleType("database")
db.get_connection = lambda: (_ for _ in ()).throw(RuntimeError("no database in tests"))
sys.modules.setdefault("database", db)

import services  # noqa: E402

equipment_stub = types.ModuleType("services.equipment_service")
sys.modules.setdefault("services.equipment_service", equipment_stub)
services.equipment_service = equipment_stub

from services import borrow_service, report_service  # noqa: E402


class BorrowStateTests(unittest.TestCase):
    today = date(2026, 10, 7)

    def row(self, status="Approved", due=None):
        return {"status": status, "due_date": due}

    def test_not_overdue_on_due_day(self):
        self.assertEqual(borrow_service.get_borrow_state(self.row(due=self.today), self.today), "Active")

    def test_overdue_after_due_day(self):
        row = self.row(due=self.today - timedelta(days=2))
        self.assertEqual(borrow_service.get_borrow_state(row, self.today), "Overdue")
        self.assertEqual(borrow_service.get_days_overdue(row, self.today), 2)

    def test_returned_is_never_overdue(self):
        row = self.row("Returned", self.today - timedelta(days=9))
        self.assertEqual(borrow_service.get_borrow_state(row, self.today), "Returned")
        self.assertEqual(borrow_service.get_days_overdue(row, self.today), 0)


class ValidationTests(unittest.TestCase):
    """These fail before touching the database."""

    def test_request_validation(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.assertFalse(borrow_service.create_request(1, 1, "abc", tomorrow)[0])
        self.assertFalse(borrow_service.create_request(1, 1, "0", tomorrow)[0])
        self.assertFalse(borrow_service.create_request(1, 1, "1", "")[0])
        self.assertFalse(borrow_service.create_request(1, 1, "1", date.today().isoformat())[0])
        self.assertFalse(borrow_service.create_request(1, 1, "1", tomorrow, "x" * 300)[0])

    def test_return_validation(self):
        self.assertFalse(borrow_service.process_return(1, 1, "Broken")[0])
        self.assertIn("describe", borrow_service.process_return(1, 1, "Damaged", "")[1])
        self.assertIn("describe", borrow_service.process_return(1, 1, "Lost", "  ")[1])

    def test_split_return_parts(self):
        ok, _, cleaned = borrow_service.check_split_parts({"Good": "2", "Damaged": "2", "Lost": "0"}, "handle broke")
        self.assertTrue(ok)
        self.assertEqual(cleaned, {"Good": 2, "Damaged": 2})
        self.assertFalse(borrow_service.check_split_parts({"Good": "2", "Damaged": "2"}, "")[0])  # notes needed
        self.assertFalse(borrow_service.check_split_parts({"Good": "0", "Damaged": "0", "Lost": "0"}, "")[0])
        self.assertFalse(borrow_service.check_split_parts({"Good": "-1"}, "")[0])
        self.assertFalse(borrow_service.check_split_parts({"Good": "x"}, "")[0])

    def test_date_range(self):
        self.assertEqual(borrow_service.parse_date_range("", ""), (None, None))
        self.assertEqual(borrow_service.parse_date_range("2026-10-01", "2026-10-31"),
                         (date(2026, 10, 1), date(2026, 10, 31)))
        with self.assertRaises(ValueError):
            borrow_service.parse_date_range("2026-10-31", "2026-10-01")
        with self.assertRaises(ValueError):
            borrow_service.parse_date_range("10/01/2026", "")


class ReportTests(unittest.TestCase):
    def test_in_range(self):
        d = report_service._in_range
        self.assertTrue(d(None, None, None))
        self.assertFalse(d(None, date(2026, 10, 1), None))
        self.assertTrue(d(datetime(2026, 10, 5, 9, 0), date(2026, 10, 1), date(2026, 10, 31)))
        self.assertFalse(d(date(2026, 11, 1), date(2026, 10, 1), date(2026, 10, 31)))

    def test_every_report_has_builder_and_columns(self):
        for name in report_service.REPORT_TYPES:
            self.assertIn(name, report_service._BUILDERS)
            self.assertIn(name, report_service.REPORT_COLUMNS)

    def test_print_page_includes_period(self):
        page = report_service.build_print_html("T", ["A"], [("x",)], " · 2026-10-01 to today")
        self.assertIn("2026-10-01 to today", page)


class FakeCursor:
    """Records every SQL statement; rowcount is 0 for statements that match `fail_on`."""

    def __init__(self, log, fail_on=None):
        self.log, self.fail_on, self.rowcount = log, fail_on, 1

    def execute(self, sql, params=()):
        self.log.append((" ".join(sql.split()), params))
        self.rowcount = 0 if self.fail_on and self.fail_on in " ".join(sql.split()) else 1
        self.last = sql

    def fetchone(self):
        return {"role": "Admin", "status": "active", "full_name": "Admin"}

    def close(self):
        pass


class FakeConn:
    def __init__(self, log, fail_on):
        self.log, self.fail_on, self.commits, self.rollbacks = log, fail_on, 0, 0

    def cursor(self, **kw):
        return FakeCursor(self.log, self.fail_on)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


class MixedReturnTests(unittest.TestCase):
    """A return with several conditions must be saved in one transaction (all or nothing)."""

    request = {"id": 7, "user_id": 3, "equipment_id": 5, "quantity": 4, "status": "Approved",
               "request_date": datetime(2026, 10, 6), "due_date": date(2026, 10, 7),
               "approved_by": 1, "approved_at": datetime(2026, 10, 6), "purpose": None,
               "equipment_name": "Hammer", "days_overdue": 0}

    def run_return(self, parts, fail_on=None, notes="handle broke"):
        from unittest import mock
        self.log, self.conns = [], []

        def fake_connection():
            conn = FakeConn(self.log, fail_on)
            self.conns.append(conn)
            return conn

        with mock.patch.object(borrow_service, "get_connection", fake_connection), \
             mock.patch.object(borrow_service, "get_request_by_id", lambda _id: dict(self.request)), \
             mock.patch.object(borrow_service, "_notify_admins_of_incident", lambda *a: None):
            return borrow_service.process_split_return(7, 1, parts, notes)

    def test_two_good_two_damaged_saved_together(self):
        ok, message = self.run_return({"Good": 2, "Damaged": 2})
        self.assertTrue(ok, message)
        self.assertEqual(sum(c.commits for c in self.conns), 1)  # a single commit for the whole return
        self.assertEqual(sum(c.rollbacks for c in self.conns), 0)
        sql = [entry[0] for entry in self.log]
        # 2 damaged units split off as their own Returned record, equipment marked under repair,
        # then the 2 good units close the original borrowing.
        self.assertTrue(any("quantity = quantity - %s" in q for q in sql))
        self.assertTrue(any(q.startswith("INSERT INTO borrow_requests") for q in self.log_text()))
        self.assertTrue(any("under_repair = LEAST(quantity, under_repair + %s)" in q for q in sql))
        final = [e for e in self.log if "SET status = 'Returned'" in e[0]]
        self.assertEqual(len(final), 1)
        self.assertEqual(final[0][1][1], "Good")        # the closing record is the good units
        self.assertEqual(final[0][1][-1], 2)            # only 2 units were still out at that point
        self.assertIn("2 Damaged", message)
        self.assertIn("2 Good", message)

    def log_text(self):
        return [entry[0] for entry in self.log]

    def test_failure_in_the_middle_saves_nothing(self):
        ok, message = self.run_return({"Good": 2, "Damaged": 2}, fail_on="SET status = 'Returned'")
        self.assertFalse(ok)
        self.assertEqual(sum(c.commits for c in self.conns), 0)
        self.assertEqual(sum(c.rollbacks for c in self.conns), 1)

    def test_too_many_units_is_refused(self):
        ok, message = self.run_return({"Good": 3, "Damaged": 2})
        self.assertFalse(ok)
        self.assertIn("only 4", message)
        self.assertEqual(sum(c.commits for c in self.conns), 0)

    def test_partial_return_leaves_the_rest_borrowed(self):
        ok, message = self.run_return({"Good": 1})
        self.assertTrue(ok, message)
        self.assertIn("3 unit(s) are still borrowed", message)
        self.assertFalse(any("SET status = 'Returned'" in q for q in self.log_text()))


class OverdueCheckTests(unittest.TestCase):
    def test_second_check_is_skipped_while_one_is_running(self):
        from unittest import mock
        calls = []
        with mock.patch.object(borrow_service, "_send_overdue_reminders", lambda: calls.append(1) or (1, 0, None)):
            self.assertEqual(borrow_service.run_overdue_check(), (1, 0, None))
            borrow_service._overdue_lock.acquire()
            try:
                self.assertEqual(borrow_service.run_overdue_check(), (0, 0, None))  # skipped, no duplicate emails
            finally:
                borrow_service._overdue_lock.release()
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
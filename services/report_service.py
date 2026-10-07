"""Report generation for the admin dashboard: build report rows, export them to CSV, and make a printable page."""
import csv
import html
from datetime import date, datetime

from services import borrow_service, equipment_service

REPORT_TYPES = [
    "Equipment Availability Report",
    "Active Borrowings",
    "Overdue Report",
    "Returned Items",
    "Borrowing History Report",
    "Borrowing Report",
    "Equipment Condition Report",
]

REPORT_COLUMNS = {
    "Equipment Availability Report": ["Equipment", "Category", "Total Qty", "Available Qty", "Borrowed",
                                      "Availability Status", "Condition"],
    "Active Borrowings": ["Borrower", "Role", "Equipment", "Qty", "Borrowed On", "Due Date", "Status"],
    "Overdue Report": ["Borrower", "Role", "Equipment", "Qty", "Due Date", "Days Overdue", "Status"],
    "Returned Items": ["Borrower", "Equipment", "Qty Returned", "Borrowed On", "Returned On", "Condition", "Received By"],
    "Borrowing History Report": ["Borrower", "Equipment", "Qty", "Borrow Date", "Due Date", "Return Date",
                                 "Status", "Condition"],
    "Borrowing Report": ["Borrower", "Equipment", "Borrow Date", "Due Date", "Return Date", "Status", "Qty"],
    "Equipment Condition Report": ["Equipment", "Category", "Current Condition", "Returned Condition",
                                   "Borrower", "Return Date", "Return Notes", "Qty"],
}


def _d(value):
    """Plain, sortable date text for reports (YYYY-MM-DD); '-' when empty."""
    if not value:
        return "-"
    return value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)


def _in_range(value, date_from, date_to):
    """True when a date/datetime falls inside the (optional) range."""
    if not date_from and not date_to:
        return True
    if value is None:
        return False
    day = value.date() if hasattr(value, "date") else value
    return (not date_from or day >= date_from) and (not date_to or day <= date_to)


def _returned_in_range(date_from, date_to):
    """Returned borrowings whose RETURN date is inside the range (these reports show the return date)."""
    return [r for r in borrow_service.get_borrow_history(returned_only=True)
            if _in_range(r["returned_at"], date_from, date_to)]


def _inventory(date_from=None, date_to=None):
    rows = []
    for item in equipment_service.get_all_equipment():
        available = borrow_service.get_available_quantity(item["id"])
        rows.append((item["name"], item["category"], item["quantity"], available,
                     item["quantity"] - available, "Available" if available > 0 else "Out of Stock",
                     item["condition_status"]))
    return rows


def _active(date_from=None, date_to=None):
    return [(r["borrower_name"], r["borrower_role"], r["equipment_name"], r["quantity"],
             _d(r["approved_at"] or r["request_date"]), _d(r["due_date"]), r["state"])
            for r in borrow_service.get_active_transactions() if _in_range(r["approved_at"] or r["request_date"], date_from, date_to)]


def _overdue(date_from=None, date_to=None):
    return [(r["borrower_name"], r["borrower_role"], r["equipment_name"], r["quantity"],
             _d(r["due_date"]), r["days_overdue"], r["state"])
            for r in borrow_service.get_overdue_transactions() if _in_range(r["due_date"], date_from, date_to)]


def _returned(date_from=None, date_to=None):
    return [(r["borrower_name"], r["equipment_name"], r["returned_quantity"] or r["quantity"],
             _d(r["approved_at"] or r["request_date"]), _d(r["returned_at"]),
             r["return_condition"] or "-", r["returned_by_name"] or "-")
            for r in _returned_in_range(date_from, date_to)]


def _history(date_from=None, date_to=None):
    return [(r["borrower_name"], r["equipment_name"], r["quantity"], _d(r["approved_at"] or r["request_date"]),
             _d(r["due_date"]), _d(r["returned_at"]), r["state"], r["return_condition"] or "-")
            for r in borrow_service.get_borrow_history(date_from, date_to)]


def _borrowing(date_from=None, date_to=None):
    """Every approved borrowing (still out, overdue or returned) with its dates and status."""
    return [(r["borrower_name"], r["equipment_name"], _d(r["approved_at"] or r["request_date"]),
             _d(r["due_date"]), _d(r["returned_at"]), r["state"], r["quantity"])
            for r in borrow_service.get_borrow_history(date_from, date_to)]


def _condition(date_from=None, date_to=None):
    """
    One row per returned borrowing (what condition it came back in, who returned it, when),
    plus one row for any equipment that has not been returned yet so every item shows its current condition.
    """
    returns = {}
    for r in _returned_in_range(date_from, date_to):
        returns.setdefault(r["equipment_id"], []).append(r)

    rows = []
    for item in equipment_service.get_all_equipment(include_deleted=True):
        records = returns.get(item["id"])
        name = item["name"] + (" (removed)" if item["is_deleted"] else "")
        if not records:
            if not item["is_deleted"]:
                rows.append((name, item["category"], item["condition_status"], "-", "-", "-", "-", "-"))
            continue
        for r in records:
            rows.append((name, item["category"], item["condition_status"],
                         r["return_condition"] or "-", r["borrower_name"],
                         _d(r["returned_at"]), r["return_notes"] or "-", r["returned_quantity"] or r["quantity"]))
    return rows


_BUILDERS = {
    "Equipment Availability Report": _inventory,
    "Active Borrowings": _active,
    "Overdue Report": _overdue,
    "Returned Items": _returned,
    "Borrowing History Report": _history,
    "Borrowing Report": _borrowing,
    "Equipment Condition Report": _condition,
}


def get_report(report_type, date_from=None, date_to=None):
    """
    Return (columns, rows) for a report type; each row is a tuple matching the columns.
    date_from / date_to ('YYYY-MM-DD' or empty) limit borrowing reports by borrow date
    (the Overdue Report by due date, Returned Items and Equipment Condition by return date). The inventory report always shows the current stock.
    """
    if report_type not in _BUILDERS:
        raise ValueError(f"Unknown report type: {report_type}")
    date_from, date_to = borrow_service.parse_date_range(date_from, date_to)
    return REPORT_COLUMNS[report_type], _BUILDERS[report_type](date_from, date_to)


def export_csv(path, columns, rows):
    # utf-8-sig so Excel opens names with accents correctly.
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)


def build_print_html(title, columns, rows, period=""):
    """A standalone HTML page of the report that opens the browser's print dialog when loaded."""
    esc = lambda v: html.escape(str(v))
    head = "".join(f"<th>{esc(c)}</th>" for c in ["No."] + list(columns))
    body = "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in (n, *row)) + "</tr>"
                   for n, row in enumerate(rows, 1))
    if not rows:
        body = f'<tr><td colspan="{len(columns) + 1}" style="text-align:center">No records found.</td></tr>'
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
h1 {{ font-size: 20px; margin: 0; }}
p {{ color: #666; font-size: 12px; margin: 4px 0 16px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
th, td {{ border: 1px solid #bbb; padding: 6px 8px; text-align: left; }}
th {{ background: #eee; }}
</style></head>
<body>
<h1>ICCT Colleges Foundation, Inc. - Equipment Borrowing System</h1>
<h1>{esc(title)}</h1>
<p>Generated {datetime.now().strftime("%B %d, %Y %I:%M %p")} &middot; {len(rows)} records{esc(period)}</p>
<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
<script>window.onload = function () {{ window.print(); }};</script>
</body></html>"""
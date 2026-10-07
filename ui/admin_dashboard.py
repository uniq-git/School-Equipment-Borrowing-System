import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from services import auth
from services import borrow_service
from services import equipment_service
from services import report_service
from database import get_connection
from ui import colors
from ui.helpers import (AMBER, DatePicker, build_main, build_sidebar, build_topbar, button, fill_table, fmt_date, label,
                        make_table, selected_id, setup_table_style, show_page as switch_page, soft_button,
                        table_page, tool_row)

ROLE_OPTIONS = ["Admin", "Student", "Teacher", "Staff"]


def _matches(query, *values):
    """True when the search text appears in any of the values (an empty search matches everything)."""
    query = query.strip().lower()
    return not query or any(query in str(v).lower() for v in values)


# Widths are sized to fit the table area at the minimum window width.
USER_COLS = [("ID", 34), ("Full Name", 150), ("ID Number", 105), ("Email", 190),
             ("Role", 65), ("Verified", 65), ("Status", 60), ("Created", 90)]
EQUIPMENT_COLS = [("ID", 36), ("Name", 140), ("Category", 120), ("Quantity", 72), ("Available", 76),
                  ("Repair", 58), ("Condition", 78), ("Added By", 105), ("Created", 98)]
PENDING_COLS = [("ID", 36), ("Borrower", 140), ("Role", 70), ("Equipment", 160), ("Qty", 50),
                ("Requested", 100), ("Due Date", 100), ("Purpose", 170)]
ACTIVE_COLS = [("ID", 36), ("Borrower", 130), ("Role", 70), ("Equipment", 145), ("Qty", 55),
               ("Borrowed On", 100), ("Due Date", 90), ("Approved By", 125)]
HISTORY_COLS = [("ID", 36), ("Borrower", 140), ("Equipment", 150), ("Borrow Date", 95), ("Due Date", 95),
                ("Return Date", 95), ("Status", 75), ("Condition", 90)]
OVERDUE_COLS = [("ID", 36), ("Borrower", 140), ("Role", 70), ("Equipment", 150), ("Qty", 50),
                ("Due Date", 95), ("Days Overdue", 100), ("Status", 70), ("Reminder", 75)]
OVERDUE_CHECK_MS = 30 * 60 * 1000  # the scheduled overdue check runs every 30 minutes
RETURN_COLS = [("Transaction ID", 105), ("Borrower", 150), ("Equipment", 165), ("Quantity", 70),
               ("Borrow Date", 100), ("Due Date", 100), ("Status", 80)]


def table(parent, cols, tags=None):
    """table_page, but with a narrow fixed ID column (make_table forces a 60px minimum on every column)."""
    page, bar, tree = table_page(parent, cols, tags)
    tree.column(cols[0][0], width=cols[0][1], minwidth=cols[0][1], stretch=False)
    return page, bar, tree


def db(sql, params=(), fetch=False):
    """Run one query: returns the rows when fetch=True, otherwise commits."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
    finally:
        cur.close()
        conn.close()


class AdminDashboard(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        is_admin = user["role"] == "Admin"
        self.titles = {"overview": "Overview", **({"users": "User Management"} if is_admin else {}),
                       "equipment": "Equipment", "pending": "Pending Requests", "active": "Active Transactions",
                       "returns": "Return Transactions", "overdue": "Overdue Monitoring", "history": "Borrowing History", "reports": "Reports"}

        self.title("ICCT Colleges Foundation, Inc. - Admin Dashboard")
        self.geometry("1150x700")
        self.minsize(1120, 700)
        self.configure(fg_color=colors.BG_LIGHT)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        setup_table_style()

        self.nav = build_sidebar(self, self.titles, self.show_page, user, self.logout, self.open_change_password,
                                 menu_title="ADMIN PANEL" if is_admin else "STAFF PANEL")
        main, body = build_main(self)
        self.title_lbl, self.stat_lbls = build_topbar(main, [
            ("pending", "Pending", AMBER), ("active", "Borrowed", colors.SUCCESS_GREEN),
            ("overdue", "Overdue", colors.ACCENT_RED), ("equipment", "Equipment", colors.BUTTON_BLUE)])

        self.pages = {"overview": self._build_overview(body)}
        if is_admin:
            self.pages["users"] = self._build_users(body)
        self.pages["equipment"] = self._build_equipment(body)
        self.pages["pending"] = self._build_pending(body)
        self.pages["active"] = self._build_active(body)
        self.pages["returns"] = self._build_returns(body)
        self.pages["overdue"] = self._build_overdue(body)
        self.pages["history"] = self._build_history(body)
        self.pages["reports"] = self._build_reports(body)
        self.show_page(next(iter(self.pages)))
        self.start_overdue_check()
        if user.get("must_change_password"):
            self.after(600, self.prompt_password_change)

    def prompt_password_change(self):
        """Accounts made by an admin start with a temporary password: ask for a new one right away."""
        messagebox.showinfo("Change Your Password", "Your account was created with a temporary password.\n"
                            "Please set your own password now.")
        self.open_change_password()

    def show_page(self, key):
        switch_page(key, self.pages, self.nav, self.title_lbl, self.titles)
        if key == "overview":
            self.load_overview()

    def _stat(self, key, value):
        self.stat_lbls[key].configure(text=str(value))

    # ---------- Overview (landing page, Admin and Staff) ----------

    def _build_overview(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure((0, 1), weight=1, uniform="overview")
        page.grid_rowconfigure(1, weight=1)

        kpis = ctk.CTkFrame(page, fg_color="transparent")
        kpis.grid(row=0, column=0, columnspan=2, sticky="we")
        self.kpi = {}
        cards = [("pending", "Pending Requests", AMBER, "pending"),
                 ("borrowed", "Borrowed Now", colors.SUCCESS_GREEN, "active"),
                 ("overdue", "Overdue", colors.ACCENT_RED, "overdue"),
                 ("available", "Units Available", colors.BUTTON_BLUE, "equipment")]
        for i, (key, title, color, target) in enumerate(cards):
            kpis.grid_columnconfigure(i, weight=1, uniform="kpi")
            card = ctk.CTkFrame(kpis, fg_color=colors.CARD_WHITE, corner_radius=8)
            card.grid(row=0, column=i, sticky="we", padx=(0 if i == 0 else 8, 0))
            ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=0).pack(fill="x")
            self.kpi[key] = label(card, "0", 30, True, color, anchor="w")
            self.kpi[key].pack(fill="x", padx=16, pady=(10, 0))
            label(card, title + "  \u203a", 12, color=colors.TEXT_GRAY, anchor="w").pack(fill="x", padx=16, pady=(0, 12))
            for w in (card, *card.winfo_children()):  # the whole card jumps to the matching page
                w.bind("<Button-1>", lambda _e, t=target: self.show_page(t))

        self.overview_pending = self._overview_panel(page, 0, "Waiting for approval", "Review all", "pending")
        self.overview_overdue = self._overview_panel(page, 1, "Overdue items", "View all", "overdue")
        return page

    def _overview_panel(self, page, col, title, link_text, target):
        """White card with a heading and a 'view all' button; returns the frame to fill with rows."""
        card = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=8)
        card.grid(row=1, column=col, sticky="nswe", padx=(0 if col == 0 else 8, 0), pady=(12, 0))
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(14, 8))
        label(head, title, 15, True).pack(side="left")
        soft_button(head, link_text, lambda: self.show_page(target), w=90, h=28).pack(side="right")
        ctk.CTkFrame(card, fg_color=colors.BORDER_GRAY, height=1, corner_radius=0).pack(fill="x", padx=16)
        items = ctk.CTkFrame(card, fg_color="transparent")
        items.pack(fill="both", expand=True, padx=16, pady=8)
        return items

    def _fill_panel(self, frame, rows, describe, empty_text, color, limit=6):
        for w in frame.winfo_children():
            w.destroy()
        if not rows:
            label(frame, empty_text, 12, color=colors.TEXT_GRAY).pack(pady=24)
            return
        for r in rows[:limit]:
            who, what, extra = describe(r)
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left")
            label(left, who, 13, True, anchor="w").pack(anchor="w")
            label(left, what, 11, color=colors.TEXT_GRAY, anchor="w").pack(anchor="w")
            label(row, extra, 12, True, color).pack(side="right")
        if len(rows) > limit:
            label(frame, f"+ {len(rows) - limit} more", 11, color=colors.TEXT_GRAY, anchor="w").pack(anchor="w", pady=(4, 0))

    def load_overview(self):
        try:
            summary = borrow_service.get_report_summary()
            pending = borrow_service.get_pending_requests()
            overdue = borrow_service.get_overdue_transactions()
        except Exception:
            return  # keep the old numbers if the database cannot be reached right now
        self.kpi["pending"].configure(text=str(len(pending)))
        self.kpi["borrowed"].configure(text=str(summary["borrowed_transactions"]))
        self.kpi["overdue"].configure(text=str(len(overdue)))
        self.kpi["available"].configure(text=str(summary["available_units"]))
        self._fill_panel(self.overview_pending, pending,
                         lambda r: (r["borrower_name"], f"{r['equipment_name']} x {r['quantity']}",
                                    f"Due {fmt_date(r['due_date'])}"),
                         "No requests are waiting.", AMBER)
        self._fill_panel(self.overview_overdue, overdue,
                         lambda r: (r["borrower_name"], f"{r['equipment_name']} x {r['quantity']}",
                                    f"{r['days_overdue']} day(s) late"),
                         "Nothing is overdue.", colors.ACCENT_RED)

    # ---------- User Management (Admin only) ----------

    def _build_users(self, parent):
        page, bar, self.user_tree = table(parent, USER_COLS, tags={"inactive": colors.ACCENT_RED})
        self.user_search = ctk.StringVar()
        self.user_search.trace_add("write", lambda *_: self.load_users())
        tool_row(bar, search=(self.user_search, "Search name, ID or email..."), pady=(12, 0))
        tool_row(bar, left=[("Add User", self.open_add_user, "blue", 110),
                            ("Activate", lambda: self.update_user("status", "active"), "green"),
                            ("Deactivate", lambda: self.update_user("status", "inactive"), "red"),
                            ("Delete User", self.delete_user, "red")],
                 right=[("Refresh", self.load_users)], pady=(8, 6))
        role_row = tool_row(bar, pady=(0, 12))
        label(role_row, "Set role", color=colors.TEXT_GRAY).pack(side="left", padx=(14, 8))
        self.role_var = ctk.StringVar(value="Student")
        ctk.CTkOptionMenu(role_row, values=ROLE_OPTIONS, variable=self.role_var, width=140, height=36,
                          fg_color=colors.ENTRY_BG, button_color=colors.BUTTON_BLUE,
                          button_hover_color=colors.BUTTON_BLUE_HOVER,
                          text_color=colors.TEXT_DARK).pack(side="left")
        button(role_row, "Apply Role", lambda: self.update_user("role", self.role_var.get())).pack(
            side="left", padx=(8, 12))
        self.load_users()
        return page

    def open_add_user(self):
        from ui.add_user import AddUserDialog
        AddUserDialog(self)

    def load_users(self):
        users = [u for u in db("SELECT * FROM users ORDER BY created_at DESC", fetch=True)
                 if _matches(self.user_search.get(), u["full_name"], u["student_number"], u["email"], u["role"])]
        fill_table(self.user_tree, users,
                   lambda u: (u["full_name"], u["student_number"], u["email"], u["role"],
                              "Yes" if u["email_verified"] else "No", u["status"], fmt_date(u["created_at"])),
                   lambda u: () if u["status"] == "active" else ("inactive",))

    def update_user(self, field, value):
        uid = selected_id(self.user_tree, "a user")
        if not uid:
            return
        own = int(uid) == self.user["id"]
        if own and field == "status" and value != "active":
            return messagebox.showerror("Not Allowed", "You cannot deactivate your own account while logged in.")
        if own and field == "role" and value != self.user["role"]:
            return messagebox.showerror("Not Allowed", "You cannot change your own role while logged in.")
        if field == "role":
            ok, msg = auth.set_user_role(int(uid), value)
        else:
            ok, msg = auth.set_user_status(int(uid), value)
        self.load_users()
        if field == "role":  # the ID number changes with the role, so tell the admin
            (messagebox.showinfo if ok else messagebox.showerror)("Role" if ok else "Not Allowed", msg)

    def delete_user(self):
        uid = selected_id(self.user_tree, "a user")
        if not uid:
            return
        if int(uid) == self.user["id"]:
            return messagebox.showerror("Cannot Delete", "You cannot delete your own account while logged in.")
        name = self.user_tree.item(uid, "values")[1]
        if messagebox.askyesno("Confirm Delete", f"Delete {name}'s account? An account with borrowing "
                               "history is deactivated instead, so the records are kept."):
            ok, msg = auth.delete_user(uid)
            if ok:
                self.load_users()
                messagebox.showinfo("Account Removed", msg)
            else:
                messagebox.showerror("Delete Failed", msg)

    # ---------- Equipment (Admin and Staff) ----------

    def _build_equipment(self, parent):
        page, bar, self.equipment_tree = table(parent, EQUIPMENT_COLS)
        self.equipment_search = ctk.StringVar()
        self.equipment_search.trace_add("write", lambda *_: self.load_equipment())
        tool_row(bar, search=(self.equipment_search, "Search name, category or condition..."), pady=(8, 0))
        left = [("Register Equipment", self.open_add_equipment, "blue", 150),
                ("Edit Selected", self.open_edit_equipment, "blue", 110),
                ("Delete Selected", self.delete_equipment, "red", 120),
                ("Categories", self.open_categories, "blue", 100)]
        tool_row(bar, left=left, right=[("Refresh", self.load_equipment)])
        self.load_equipment()
        return page

    def open_add_equipment(self):
        from ui.add_equipment import AddEquipmentDialog
        AddEquipmentDialog(self, self.user)

    def open_edit_equipment(self):
        item_id = selected_id(self.equipment_tree, "an equipment item")
        if not item_id:
            return
        item = next((i for i in equipment_service.get_all_equipment() if i["id"] == int(item_id)), None)
        if not item:
            return messagebox.showerror("Not Found", "This equipment item no longer exists.")
        from ui.add_equipment import EditEquipmentDialog
        EditEquipmentDialog(self, item)

    def open_categories(self):
        from ui.add_equipment import ManageCategoriesDialog
        ManageCategoriesDialog(self)

    def load_equipment(self):
        all_rows = equipment_service.get_all_equipment()
        rows = [i for i in all_rows if _matches(self.equipment_search.get(), i["name"], i["category"],
                                                i["condition_status"])]
        fill_table(self.equipment_tree, rows,
                   lambda i: (i["name"], i["category"], i["quantity"], borrow_service.get_available_quantity(i["id"]),
                              i.get("under_repair") or 0, i["condition_status"], i["added_by_name"] or "-",
                              fmt_date(i["created_at"])))
        self._stat("equipment", len(all_rows))

    def delete_equipment(self):
        item_id = selected_id(self.equipment_tree, "an equipment item")
        if item_id and messagebox.askyesno("Confirm Delete", "Remove this equipment item? Its borrowing "
                                           "history (if any) is kept for reports."):
            ok, msg = equipment_service.delete_equipment(item_id)
            if ok:
                self.load_equipment()
            else:
                messagebox.showerror("Cannot Delete", msg)

    # ---------- Borrowing (Admin and Staff) ----------

    def _build_pending(self, parent):
        page, bar, self.pending_tree = table(parent, PENDING_COLS)
        tool_row(bar, left=[("Approve", self.approve_request, "green"), ("Deny", self.deny_request, "red")],
                 right=[("Refresh", self.load_pending)])
        self.load_pending()
        return page

    def load_pending(self):
        rows = borrow_service.get_pending_requests()
        fill_table(self.pending_tree, rows,
                   lambda r: (r["borrower_name"], r["borrower_role"], r["equipment_name"], r["quantity"],
                              fmt_date(r["request_date"]), fmt_date(r["due_date"]), r.get("purpose") or "-"))
        self._stat("pending", len(rows))

    def _pending_request(self):
        rid = selected_id(self.pending_tree, "a pending request")
        if not rid:
            return None
        req = borrow_service.get_request_by_id(int(rid))
        if not req or req["status"] != "Pending":
            messagebox.showinfo("Not Available", "This request is no longer pending.")
            self.load_pending()
            return None
        return req

    def approve_request(self):
        req = self._pending_request()
        if req:
            from ui.borrow import ApproveRequestDialog
            ApproveRequestDialog(self, self.user, req, on_success=lambda: (
                self.load_pending(), self.load_active(), self.load_returns(), self.load_equipment()))

    def deny_request(self):
        req = self._pending_request()
        if req:
            from ui.borrow import DenyRequestDialog
            DenyRequestDialog(self, self.user, req, on_success=self.load_pending)

    def _build_active(self, parent):
        page, bar, self.active_tree = table(parent, ACTIVE_COLS)
        tool_row(bar, right=[("Refresh", self.load_active)])
        self.load_active()
        return page

    def load_active(self):
        rows = borrow_service.get_active_transactions()
        fill_table(self.active_tree, rows,
                   lambda r: (r["borrower_name"], r["borrower_role"], r["equipment_name"], r["quantity"],
                              fmt_date(r["request_date"]), fmt_date(r["due_date"]), r["approved_by_name"] or "-"))
        self._stat("active", len(rows))

    # ---------- Return Transactions (Admin and Staff) ----------

    def _build_returns(self, parent):
        page, bar, self.returns_tree = table(parent, RETURN_COLS, tags={"overdue": colors.ACCENT_RED})
        tool_row(bar, left=[("Return", self.return_transaction, "green")],
                 right=[("Refresh", self.load_returns)])
        self.load_returns()
        return page

    def load_returns(self):
        """Active (Approved) borrowings that can still be returned. Returned ones leave this list."""
        rows = borrow_service.get_active_transactions()
        fill_table(self.returns_tree, rows,
                   lambda r: (r["borrower_name"], r["equipment_name"], r["quantity"],
                              fmt_date(r["approved_at"] or r["request_date"]), fmt_date(r["due_date"]), r["state"]),
                   lambda r: ("overdue",) if r["state"] == "Overdue" else (), show_id=True)

    def return_transaction(self):
        tid = selected_id(self.returns_tree, "a transaction")
        if not tid:
            return
        txn = borrow_service.get_request_by_id(int(tid))
        if not txn or txn["status"] != "Approved":
            messagebox.showinfo("Not Available", "This transaction is no longer active.")
            self.load_returns()
            self.load_active()
            return
        from ui.borrow import ReturnDialog
        ReturnDialog(self, self.user, txn, on_success=lambda: (
            self.load_returns(), self.load_active(), self.load_equipment(), self.load_overdue(), self.load_history()))

    # ---------- Reports (Admin and Staff) ----------

    def _build_reports(self, parent):
        self.report_page = page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=4)
        bar.grid(row=0, column=0, sticky="we", pady=(0, 8))

        row = tool_row(bar, right=[("Print", self.print_report), ("Export", self.export_report)])
        label(row, "Report Type:", color=colors.TEXT_GRAY).pack(side="left", padx=(12, 6))
        self.report_type_var = ctk.StringVar(value=report_service.REPORT_TYPES[0])
        ctk.CTkOptionMenu(row, values=report_service.REPORT_TYPES, variable=self.report_type_var, width=230,
                          height=32, corner_radius=3, fg_color=colors.ENTRY_BG, button_color=colors.BUTTON_BLUE,
                          button_hover_color=colors.BUTTON_BLUE_HOVER,
                          text_color=colors.TEXT_DARK).pack(side="left")
        button(row, "Generate Report", self.generate_report, w=140, h=32, fg=colors.SUCCESS_GREEN,
               hover="#166838").pack(side="left", padx=10)

        dates = tool_row(bar, pady=(0, 8))
        label(dates, "Date from:", color=colors.TEXT_GRAY).pack(side="left", padx=(12, 6))
        self.report_from = DatePicker(dates, width=150, height=32)
        self.report_from.pack(side="left")
        label(dates, "to:", color=colors.TEXT_GRAY).pack(side="left", padx=(10, 6))
        self.report_to = DatePicker(dates, width=150, height=32)
        self.report_to.pack(side="left")
        button(dates, "Clear Dates", lambda: (self.report_from.clear(), self.report_to.clear()), w=100, h=32,
               fg=colors.ENTRY_BG, hover=colors.BORDER_GRAY, text_color=colors.TEXT_DARK).pack(side="left", padx=10)

        self.report_tree = None
        self.report = None  # (title, columns, rows) once a report has been generated
        self._show_report(report_service.REPORT_TYPES[0], [])
        return page

    def _show_report(self, report_type, rows):
        """Rebuild the table with the columns of this report type and fill it with rows."""
        if self.report_tree is not None:
            self.report_tree.master.destroy()
        columns = report_service.REPORT_COLUMNS[report_type]
        self.report_tree = make_table(self.report_page, [("No.", 50)] + [(c, 110) for c in columns])
        self.report_tree.column("No.", width=50, minwidth=50, stretch=False)
        fill_table(self.report_tree, [{"id": n} for n in range(len(rows))], lambda r: rows[r["id"]])

    def generate_report(self):
        report_type = self.report_type_var.get()
        try:
            columns, rows = report_service.get_report(report_type, self.report_from.get(), self.report_to.get())
        except Exception as exc:
            return messagebox.showerror("Report Failed", f"Could not generate the report: {exc}")
        period = ""
        if self.report_from.get() or self.report_to.get():
            period = f" · {self.report_from.get() or 'start'} to {self.report_to.get() or 'today'}"
        self.report = (report_type, columns, rows, period)
        self._show_report(report_type, rows)

    def _current_report(self, action):
        if not self.report:
            messagebox.showinfo("No Report", f"Please generate a report first before you {action}.")
        return self.report

    def export_report(self):
        report = self._current_report("export")
        if not report:
            return
        title, columns, rows, _period = report
        from datetime import date
        path = filedialog.asksaveasfilename(
            title="Export Report", defaultextension=".csv", filetypes=[("CSV file", "*.csv")],
            initialfile=f"{title.replace(' ', '_')}_{date.today().isoformat()}.csv")
        if not path:
            return
        try:
            report_service.export_csv(path, columns, rows)
        except OSError as exc:
            return messagebox.showerror("Export Failed", f"Could not save the file: {exc}")
        messagebox.showinfo("Exported", f"The report was saved to:\n{path}")

    def print_report(self):
        report = self._current_report("print")
        if not report:
            return
        import pathlib
        import tempfile
        import webbrowser
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(report_service.build_print_html(*report))
        webbrowser.open(pathlib.Path(f.name).as_uri())  # the page opens the print dialog by itself

    # ---------- Borrowing History (Admin and Staff) ----------

    def _build_history(self, parent):
        page, bar, self.history_tree = table(parent, HISTORY_COLS)
        self.history_search = ctk.StringVar()
        self.history_search.trace_add("write", lambda *_: self.load_history())
        tool_row(bar, right=[("Refresh", self.load_history)],
                 search=(self.history_search, "Search borrower, equipment or condition..."))
        self.load_history()
        return page

    def load_history(self):
        """Full borrowing history: every completed (returned) transaction."""
        rows = [r for r in borrow_service.get_borrow_history(returned_only=True)
                if _matches(self.history_search.get(), r["borrower_name"], r["equipment_name"],
                            r["return_condition"] or "")]
        fill_table(self.history_tree, rows,
                   lambda r: (r["borrower_name"], r["equipment_name"],
                              fmt_date(r["approved_at"] or r["request_date"]), fmt_date(r["due_date"]),
                              fmt_date(r["returned_at"]), r["status"], r["return_condition"] or "-"),
                   show_id=True)

    # ---------- Overdue Monitoring (Admin and Staff) ----------

    def _build_overdue(self, parent):
        page, bar, self.overdue_tree = table(parent, OVERDUE_COLS, tags={"overdue": colors.ACCENT_RED})
        tool_row(bar, right=[("Refresh", self.load_overdue)])
        self.load_overdue()
        return page

    def load_overdue(self):
        """Active borrowings that are past their due date (the admin dashboard Overdue list)."""
        rows = borrow_service.get_overdue_transactions()
        fill_table(self.overdue_tree, rows,
                   lambda r: (r["borrower_name"], r["borrower_role"], r["equipment_name"], r["quantity"],
                              fmt_date(r["due_date"]), r["days_overdue"], "Overdue",
                              "Sent" if r.get("overdue_reminder_sent_at") else "Pending"),
                   lambda r: ("overdue",), show_id=True)
        self._stat("overdue", len(rows))

    def start_overdue_check(self):
        """Scheduled check: run now, then again every OVERDUE_CHECK_MS, without freezing the window."""
        threading.Thread(target=self._overdue_worker, daemon=True).start()
        self.after(OVERDUE_CHECK_MS, self.start_overdue_check)

    def _overdue_worker(self):
        try:
            borrow_service.run_overdue_check()
        except Exception as exc:  # e.g. database not reachable; try again at the next check
            print(f"Overdue check failed: {exc}")
        try:
            self.after(0, self.load_overdue)
        except Exception:
            pass  # the window was closed

    # ---------- shared ----------

    def open_change_password(self):
        from ui.change_password import ChangePasswordDialog
        ChangePasswordDialog(self, self.user)

    def logout(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()
import customtkinter as ctk
from tkinter import messagebox

import auth
import borrow_service
import equipment_service
from database import get_connection
from ui import colors
from ui.helpers import (AMBER, build_main, build_sidebar, build_topbar, button, fill_table, fmt_date, label,
                        selected_id, setup_table_style, show_page as switch_page, table_page, tool_row)

ROLE_OPTIONS = ["Admin", "Student", "Teacher", "Staff"]

# Widths are sized to fit the table area at the minimum window width.
USER_COLS = [("ID", 36), ("Full Name", 145), ("ID Number", 105), ("Email", 185),
             ("Role", 62), ("Verified", 72), ("Status", 62), ("Created", 93)]
EQUIPMENT_COLS = [("ID", 36), ("Name", 150), ("Category", 130), ("Quantity", 72), ("Available", 76),
                  ("Condition", 78), ("Added By", 120), ("Created", 98)]
PENDING_COLS = [("ID", 36), ("Borrower", 160), ("Role", 80), ("Equipment", 190), ("Qty", 60),
                ("Requested", 110), ("Due Date", 110)]
ACTIVE_COLS = [("ID", 36), ("Borrower", 130), ("Role", 70), ("Equipment", 145), ("Qty", 55),
               ("Borrowed On", 100), ("Due Date", 90), ("Approved By", 125)]


def table(parent, cols, tags=None):
    """table_page, but with a narrow fixed ID column (make_table forces a 60px minimum on every column)."""
    page, bar, tree = table_page(parent, cols, tags)
    tree.column("ID", width=cols[0][1], minwidth=cols[0][1], stretch=False)
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
        self.titles = {**({"users": "User Management"} if is_admin else {}),
                       "equipment": "Equipment", "pending": "Pending Requests", "active": "Active Transactions"}

        self.title("ICCT Colleges Foundation, Inc. - Equipment Borrowing System")
        self.geometry("1150x700")
        self.minsize(1120, 620)
        self.configure(fg_color=colors.BG_LIGHT)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        setup_table_style()

        self.nav = build_sidebar(self, self.titles, self.show_page, user, self.logout, self.open_change_password)
        main, body = build_main(self)
        self.title_lbl, self.stat_lbls = build_topbar(main, [
            ("pending", "Pending", AMBER), ("active", "Borrowed", colors.SUCCESS_GREEN),
            ("equipment", "Equipment", colors.BUTTON_BLUE)])

        self.pages = {}
        if is_admin:
            self.pages["users"] = self._build_users(body)
        self.pages["equipment"] = self._build_equipment(body)
        self.pages["pending"] = self._build_pending(body)
        self.pages["active"] = self._build_active(body)
        self.show_page(next(iter(self.pages)))

    def show_page(self, key):
        switch_page(key, self.pages, self.nav, self.title_lbl, self.titles)

    def _stat(self, key, value):
        self.stat_lbls[key].configure(text=str(value))

    # ---------- User Management (Admin only) ----------

    def _build_users(self, parent):
        page, bar, self.user_tree = table(parent, USER_COLS, tags={"inactive": colors.ACCENT_RED})
        tool_row(bar, left=[("Add User", self.open_add_user, "blue", 110),
                            ("Activate", lambda: self.update_user("status", "active"), "green"),
                            ("Deactivate", lambda: self.update_user("status", "inactive"), "red"),
                            ("Delete User", self.delete_user, "red")],
                 right=[("Refresh", self.load_users)], pady=(12, 6))
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
        fill_table(self.user_tree, db("SELECT * FROM users ORDER BY created_at DESC", fetch=True),
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
        db(f"UPDATE users SET {field} = %s WHERE id = %s", (value, uid))  # field is hard-coded by the callers
        self.load_users()

    def delete_user(self):
        uid = selected_id(self.user_tree, "a user")
        if not uid:
            return
        if int(uid) == self.user["id"]:
            return messagebox.showerror("Cannot Delete", "You cannot delete your own account while logged in.")
        name = self.user_tree.item(uid, "values")[1]
        if messagebox.askyesno("Confirm Delete", f"Permanently delete {name}'s account? This cannot be undone."):
            ok, msg = auth.delete_user(uid)
            self.load_users() if ok else messagebox.showerror("Delete Failed", msg)

    # ---------- Equipment (Admin and Staff) ----------

    def _build_equipment(self, parent):
        page, bar, self.equipment_tree = table(parent, EQUIPMENT_COLS)
        left = [("Register Equipment", self.open_add_equipment, "blue", 150),
                ("Delete Selected", self.delete_equipment, "red", 130)]
        if self.user["role"] == "Staff":  # Staff can borrow; Admin only manages the catalog
            left.append(("Request to Borrow", self.request_equipment, "blue", 150))
        tool_row(bar, left=left, right=[("Refresh", self.load_equipment)])
        self.load_equipment()
        return page

    def open_add_equipment(self):
        from ui.add_equipment import AddEquipmentDialog
        AddEquipmentDialog(self, self.user)

    def load_equipment(self):
        rows = equipment_service.get_all_equipment()
        fill_table(self.equipment_tree, rows,
                   lambda i: (i["name"], i["category"], i["quantity"], borrow_service.get_available_quantity(i["id"]),
                              i["condition_status"], i["added_by_name"] or "-", fmt_date(i["created_at"])))
        self._stat("equipment", len(rows))

    def request_equipment(self):
        item_id = selected_id(self.equipment_tree, "an equipment item")
        if not item_id:
            return
        item = next((i for i in equipment_service.get_all_equipment() if i["id"] == int(item_id)), None)
        if not item:
            return messagebox.showerror("Not Found", "This equipment item no longer exists.")
        available = borrow_service.get_available_quantity(item["id"])
        if available <= 0:
            return messagebox.showinfo("Unavailable", "There are no available units of this equipment right now.")
        from ui.borrow import RequestEquipmentDialog
        RequestEquipmentDialog(self, self.user, item, available,
                               on_success=lambda: (self.load_equipment(), self.load_pending()))

    def delete_equipment(self):
        item_id = selected_id(self.equipment_tree, "an equipment item")
        if item_id and messagebox.askyesno("Confirm Delete", "Remove this equipment item? This cannot be undone."):
            equipment_service.delete_equipment(item_id)
            self.load_equipment()

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
                              fmt_date(r["request_date"]), fmt_date(r["due_date"])))
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
                self.load_pending(), self.load_active(), self.load_equipment()))

    def deny_request(self):
        req = self._pending_request()
        if req and messagebox.askyesno(
                "Confirm Deny", f"Deny the request for '{req['equipment_name']}' from {req['borrower_name']}?"):
            ok, msg = borrow_service.deny_request(req["id"], self.user["id"])
            self.load_pending() if ok else messagebox.showerror("Deny Failed", msg)

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

    # ---------- shared ----------

    def open_change_password(self):
        from ui.change_password import ChangePasswordDialog
        ChangePasswordDialog(self, self.user)

    def logout(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()
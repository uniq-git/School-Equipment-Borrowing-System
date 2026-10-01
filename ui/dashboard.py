"""Admin / Staff dashboard (navy sidebar + light content area, same look as the student dashboard)."""
import customtkinter as ctk
from tkinter import messagebox

from ui import colors
from ui.helpers import (AMBER, build_main, build_sidebar, build_topbar, fill_table, fmt_date, label,
                        selected_id, setup_table_style, show_page, table_page, tool_row)
from database import get_connection
import borrow_service
import equipment_service

ROLES = ["Admin", "Student", "Teacher", "Staff"]
TITLES = {"users": "User Management", "equipment": "Equipment", "pending": "Pending Requests",
          "active": "Active Transactions"}
# (heading, minimum width); columns stretch to fill the card.
USER_COLS = (("#", 36), ("Full Name", 140), ("ID Number", 110), ("Email", 180), ("Role", 70),
             ("Verified", 66), ("Status", 70), ("Created", 100))
EQUIP_COLS = (("#", 36), ("Name", 170), ("Category", 140), ("Qty", 56), ("Available", 76),
              ("Condition", 80), ("Added By", 150), ("Created", 100))
PENDING_COLS = (("#", 36), ("Borrower", 150), ("Role", 70), ("Equipment", 170), ("Qty", 50),
                ("Requested", 110), ("Proposed Due", 110))
ACTIVE_COLS = (("#", 36), ("Borrower", 140), ("Role", 70), ("Equipment", 150), ("Qty", 50),
               ("Borrowed On", 110), ("Due Date", 100), ("Approved By", 120))


def db(sql, params=(), fetch=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params)
    rows = cursor.fetchall() if fetch else conn.commit()
    cursor.close()
    conn.close()
    return rows


def search_var(on_change):
    var = ctk.StringVar()
    var.trace_add("write", lambda *_: on_change())
    return var


class AdminDashboard(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user, self._users, self._equipment = user, [], []
        self.title("ICCT Colleges Foundation, Inc. - Equipment Borrowing System")
        self.geometry("1280x720")
        self.minsize(1100, 640)
        self.configure(fg_color=colors.BG_LIGHT)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        setup_table_style()

        builders = {"users": self._users_page, "equipment": self._equipment_page,
                    "pending": self._pending_page, "active": self._active_page}
        keys = [k for k in builders if k != "users" or user["role"] == "Admin"]
        self._nav = build_sidebar(self, {k: TITLES[k] for k in keys}, self.show_page, user, self.logout)
        main, body = build_main(self)
        self.title_lbl, self.stats = build_topbar(main, (
            ("pending", "Pending", AMBER), ("active", "Active", colors.SUCCESS_GREEN),
            ("equipment", "Equipment", colors.BUTTON_BLUE)))
        self._pages = {k: builders[k](body) for k in keys}
        self.show_page(keys[0])

    def show_page(self, key):
        show_page(key, self._pages, self._nav, self.title_lbl, TITLES)

    # ---------- User Management (Admin only) ----------

    def _users_page(self, parent):
        page, bar, self.tree = table_page(parent, USER_COLS, {"inactive": colors.TEXT_GRAY})
        self.user_search = search_var(self.render_users)
        tool_row(bar, [("Add User", self.open_add_user)], [("Refresh", self.load_users)],
                 (self.user_search, "Search users..."))
        row = tool_row(bar, [("Activate", lambda: self.update_status("active"), "green"),
                             ("Deactivate", lambda: self.update_status("inactive"), "red"),
                             ("Delete", self.delete_user, "red")],
                       [("Apply Role", self.update_role)], pady=(0, 12))
        self.role_var = ctk.StringVar(value="Student")
        ctk.CTkOptionMenu(row, values=ROLES, variable=self.role_var, width=120, height=36,
                          fg_color=colors.ENTRY_BG, button_color=colors.BUTTON_BLUE,
                          button_hover_color=colors.BUTTON_BLUE_HOVER,
                          text_color=colors.TEXT_DARK).pack(side="right", padx=(0, 20))
        label(row, "Set role", color=colors.TEXT_GRAY).pack(side="right", padx=(0, 8))
        self.load_users()
        return page

    def open_add_user(self):
        from ui.add_user import AddUserDialog
        AddUserDialog(self)

    def load_users(self):
        self._users = db("SELECT * FROM users ORDER BY created_at DESC", fetch=True)
        self.render_users()

    def render_users(self):
        q = self.user_search.get().strip().lower()
        rows = [u for u in self._users
                if q in " ".join(str(u[k] or "") for k in ("full_name", "student_number", "email", "role")).lower()]
        fill_table(self.tree, rows, lambda u: (
            u["full_name"], u["student_number"], u["email"], u["role"], "Yes" if u["email_verified"] else "No",
            u["status"].title(), fmt_date(u["created_at"])),
            lambda u: ("inactive",) if u["status"] == "inactive" else ())

    def _selected_user(self, own_account_error=None, blocked=False):
        """Selected user id; shows own_account_error and returns None if it's the logged-in admin and blocked."""
        user_id = selected_id(self.tree, "a user")
        if user_id and blocked and int(user_id) == self.user["id"]:
            messagebox.showerror("Not Allowed", own_account_error)
            return None
        return user_id

    def update_status(self, status):
        user_id = self._selected_user("You cannot deactivate your own account while logged in.", status != "active")
        if user_id:
            db("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
            self.load_users()

    def update_role(self):
        role = self.role_var.get()
        user_id = self._selected_user("You cannot change your own role while logged in.", role != self.user["role"])
        if user_id:
            db("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
            self.load_users()

    def delete_user(self):
        user_id = self._selected_user("You cannot delete your own account while logged in.", True)
        if not user_id:
            return
        name = self.tree.item(user_id, "values")[1]
        if messagebox.askyesno("Confirm Delete", f"Permanently delete {name}'s account? This cannot be undone."):
            import auth
            ok, message = auth.delete_user(user_id)
            self.load_users() if ok else messagebox.showerror("Delete Failed", message)

    # ---------- Equipment (Admin and Staff) ----------

    def _equipment_page(self, parent):
        page, bar, self.equipment_tree = table_page(parent, EQUIP_COLS, {"out": colors.ACCENT_RED})
        self.equip_search = search_var(self.render_equipment)
        buttons = [("Register Equipment", self.open_add_equipment, "blue", 150),
                   ("Delete Selected", self.delete_equipment, "red", 130)]
        if self.user["role"] == "Staff":  # Staff can borrow too; Admin only manages the catalog
            buttons.append(("Request to Borrow", self.request_equipment, "blue", 150))
        tool_row(bar, buttons, [("Refresh", self.load_equipment)], (self.equip_search, "Search equipment..."))
        self.load_equipment()
        return page

    def open_add_equipment(self):
        from ui.add_equipment import AddEquipmentDialog
        AddEquipmentDialog(self, self.user)

    def load_equipment(self):
        self._equipment = [{**i, "available": borrow_service.get_available_quantity(i["id"])}
                           for i in equipment_service.get_all_equipment()]
        self.stats["equipment"].configure(text=str(len(self._equipment)))
        self.render_equipment()

    def render_equipment(self):
        q = self.equip_search.get().strip().lower()
        rows = [i for i in self._equipment if q in f"{i['name']} {i['category']}".lower()]
        fill_table(self.equipment_tree, rows, lambda i: (
            i["name"], i["category"], i["quantity"], i["available"], i["condition_status"],
            i["added_by_name"] or "-", fmt_date(i["created_at"])),
            lambda i: ("out",) if i["available"] <= 0 else ())

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
                               on_success=lambda: (self.load_equipment(), self.load_pending_requests()))

    def delete_equipment(self):
        item_id = selected_id(self.equipment_tree, "an equipment item")
        if item_id and messagebox.askyesno("Confirm Delete", "Remove this equipment item? This cannot be undone."):
            equipment_service.delete_equipment(item_id)
            self.load_equipment()

    # ---------- Pending Requests (Admin and Staff) ----------

    def _pending_page(self, parent):
        page, bar, self.pending_tree = table_page(parent, PENDING_COLS)
        tool_row(bar, [("Approve", self.approve_request, "green"), ("Deny", self.deny_request, "red")],
                 [("Refresh", self.load_pending_requests)])
        self.load_pending_requests()
        return page

    def load_pending_requests(self):
        rows = borrow_service.get_pending_requests()
        fill_table(self.pending_tree, rows, lambda r: (
            r["borrower_name"], r["borrower_role"], r["equipment_name"], r["quantity"],
            fmt_date(r["request_date"]), fmt_date(r["due_date"])))
        self.stats["pending"].configure(text=str(len(rows)))

    def _selected_request(self):
        request_id = selected_id(self.pending_tree, "a pending request")
        if not request_id:
            return None
        request = borrow_service.get_request_by_id(int(request_id))
        if not request or request["status"] != "Pending":
            messagebox.showinfo("Not Available", "This request is no longer pending.")
            self.load_pending_requests()
            return None
        return request

    def approve_request(self):
        request = self._selected_request()
        if request:
            from ui.borrow import ApproveRequestDialog
            ApproveRequestDialog(self, self.user, request, on_success=lambda: (
                self.load_pending_requests(), self.load_active_transactions(), self.load_equipment()))

    def deny_request(self):
        request = self._selected_request()
        if request and messagebox.askyesno(
                "Confirm Deny", f"Deny the request for '{request['equipment_name']}' from {request['borrower_name']}?"):
            ok, message = borrow_service.deny_request(request["id"], self.user["id"])
            self.load_pending_requests() if ok else messagebox.showerror("Deny Failed", message)

    # ---------- Active Transactions (Admin and Staff) ----------

    def _active_page(self, parent):
        page, bar, self.active_tree = table_page(parent, ACTIVE_COLS)
        tool_row(bar, [("Refresh", self.load_active_transactions)])
        self.load_active_transactions()
        return page

    def load_active_transactions(self):
        rows = borrow_service.get_active_transactions()
        fill_table(self.active_tree, rows, lambda r: (
            r["borrower_name"], r["borrower_role"], r["equipment_name"], r["quantity"],
            fmt_date(r["request_date"]), fmt_date(r["due_date"]), r["approved_by_name"] or "-"))
        self.stats["active"].configure(text=str(len(rows)))

    # ---------- shared ----------

    def logout(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()
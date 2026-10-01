import customtkinter as ctk
from tkinter import ttk, messagebox

import auth
import borrow_service
import equipment_service
from database import get_connection
from ui import colors

ROLE_OPTIONS = ["Admin", "Student", "Teacher", "Staff"]
GREEN, GREEN_H, RED, RED_H = colors.SUCCESS_GREEN, "#166838", colors.ACCENT_RED, "#b52a48"
BLUE, BLUE_H = colors.BUTTON_BLUE, colors.BUTTON_BLUE_HOVER

# Treeview layouts: (column, width) pairs
USER_COLS = (("id", 40), ("full_name", 160), ("student_number", 120), ("email", 200),
             ("role", 80), ("email_verified", 100), ("status", 80), ("created_at", 140))
EQUIP_COLS = (("id", 40), ("name", 200), ("category", 140), ("quantity", 70), ("available", 80),
              ("condition", 100), ("added_by", 160), ("created_at", 140))
PENDING_COLS = (("id", 40), ("borrower", 160), ("role", 80), ("equipment", 200),
                ("quantity", 70), ("request_date", 140), ("proposed_due_date", 120))
ACTIVE_COLS = (("id", 40), ("borrower", 160), ("role", 80), ("equipment", 200), ("quantity", 70),
               ("borrowed_on", 140), ("due_date", 110), ("approved_by", 160))


def db(sql, params=(), fetch=False):
    """Run one query; return rows if fetch=True, else commit."""
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


def toolbar(parent, buttons, pady=(4, 4)):
    """buttons: (text, command, width, fg, hover) tuples; fg/hover optional."""
    bar = ctk.CTkFrame(parent, fg_color=colors.BG_LIGHT)
    bar.pack(fill="x", pady=pady)
    for b in buttons:
        text, cmd, w, fg, hover = b + (100, None, None)[len(b) - 2:]  # fill in defaults
        kw = {"fg_color": fg, "hover_color": hover} if fg else {}
        ctk.CTkButton(bar, text=text, width=w, command=cmd, **kw).pack(side="left", padx=(0, 6))
    return bar


def table(parent, cols, height=16):
    tree = ttk.Treeview(parent, columns=[c for c, _ in cols], show="headings", height=height)
    for col, width in cols:
        tree.heading(col, text=col.replace("_", " ").title())
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, pady=10)
    return tree


def fill(tree, rows):
    """rows: (iid, values...) tuples; the first value shown is a 1-based row number."""
    tree.delete(*tree.get_children())
    for n, (iid, *values) in enumerate(rows, start=1):
        tree.insert("", "end", iid=str(iid), values=(n, *values))


def selected(tree, what):
    sel = tree.selection()
    if not sel:
        messagebox.showinfo("No selection", f"Please select {what} first.")
    return sel[0] if sel else None


class AdminDashboard(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.title("ICCT Equipment Borrowing System")
        self.geometry("1060x620")
        self.configure(fg_color=colors.BG_LIGHT)

        header = ctk.CTkFrame(self, fg_color=colors.NAVY_DARK, height=70, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="Admin Dashboard", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="white").pack(side="left", padx=20, pady=15)
        ctk.CTkLabel(header, text=f"Signed in as {user['full_name']} ({user['role']})",
                     font=ctk.CTkFont(size=12), text_color="#c7cede").pack(side="left", padx=10)
        ctk.CTkButton(header, text="Log Out", width=100, fg_color=RED, hover_color=RED_H,
                      command=self.logout).pack(side="right", padx=20, pady=15)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        tabs = self._tabs(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=(14, 20))
        if user["role"] == "Admin":
            self._build_users(self._add_tab(tabs, "User Management"))
        self._build_equipment(self._add_tab(tabs, "Equipment"))
        sub = self._tabs(self._add_tab(tabs, "Borrowing"))
        sub.pack(fill="both", expand=True)
        self._build_pending(self._add_tab(sub, "Pending Requests"))
        self._build_active(self._add_tab(sub, "Active Transactions"))

    @staticmethod
    def _tabs(parent):
        return ctk.CTkTabview(parent, fg_color=colors.BG_LIGHT, segmented_button_selected_color=BLUE)

    @staticmethod
    def _add_tab(tabview, name):
        tabview.add(name)
        return tabview.tab(name)

    # ---------- User Management (Admin only) ----------

    def _build_users(self, tab):
        bar = toolbar(tab, [
            ("Add User", self.open_add_user, 100, BLUE, BLUE_H),
            ("Refresh", self.load_users),
            ("Activate", lambda: self.update_user("status", "active"), 100, GREEN, GREEN_H),
            ("Deactivate", lambda: self.update_user("status", "inactive"), 100, RED, RED_H),
            ("Delete User", self.delete_user, 100, RED, RED_H),
        ])
        ctk.CTkLabel(bar, text="Set role:", text_color=colors.TEXT_DARK).pack(side="left", padx=(14, 6))
        self.role_var = ctk.StringVar(value="Student")
        ctk.CTkOptionMenu(bar, values=ROLE_OPTIONS, variable=self.role_var, width=110).pack(side="left")
        ctk.CTkButton(bar, text="Apply Role", width=100,
                      command=lambda: self.update_user("role", self.role_var.get())).pack(side="left", padx=6)
        self.tree = table(tab, USER_COLS)
        self.load_users()

    def open_add_user(self):
        from ui.add_user import AddUserDialog
        AddUserDialog(self)

    def load_users(self):
        fill(self.tree, [(u["id"], u["full_name"], u["student_number"], u["email"], u["role"],
                          "Yes" if u["email_verified"] else "No", u["status"], u["created_at"])
                         for u in db("SELECT * FROM users ORDER BY created_at DESC", fetch=True)])

    def update_user(self, field, value):
        uid = selected(self.tree, "a user")
        if not uid:
            return
        own = int(uid) == self.user["id"]
        if own and field == "status" and value != "active":
            return messagebox.showerror("Not Allowed", "You cannot deactivate your own account while logged in.")
        if own and field == "role" and value != self.user["role"]:
            return messagebox.showerror("Not Allowed", "You cannot change your own role while logged in.")
        db(f"UPDATE users SET {field} = %s WHERE id = %s", (value, uid))  # field is hard-coded above
        self.load_users()

    def delete_user(self):
        uid = selected(self.tree, "a user")
        if not uid:
            return
        if int(uid) == self.user["id"]:
            return messagebox.showerror("Cannot Delete", "You cannot delete your own account while logged in.")
        name = self.tree.item(uid, "values")[1]
        if messagebox.askyesno("Confirm Delete", f"Permanently delete {name}'s account? This cannot be undone."):
            ok, msg = auth.delete_user(uid)
            self.load_users() if ok else messagebox.showerror("Delete Failed", msg)

    # ---------- Equipment (Admin and Staff) ----------

    def _build_equipment(self, tab):
        buttons = [("Register Equipment", self.open_add_equipment, 150, BLUE, BLUE_H),
                   ("Refresh", self.load_equipment),
                   ("Delete Selected", self.delete_equipment, 130, RED, RED_H)]
        if self.user["role"] == "Staff":  # Staff can borrow; Admin only manages
            buttons.append(("Request to Borrow", self.request_equipment, 150, BLUE, BLUE_H))
        toolbar(tab, buttons)
        self.equipment_tree = table(tab, EQUIP_COLS)
        self.load_equipment()

    def open_add_equipment(self):
        from ui.add_equipment import AddEquipmentDialog
        AddEquipmentDialog(self, self.user)

    def load_equipment(self):
        fill(self.equipment_tree,
             [(i["id"], i["name"], i["category"], i["quantity"], borrow_service.get_available_quantity(i["id"]),
               i["condition_status"], i["added_by_name"] or "-", i["created_at"])
              for i in equipment_service.get_all_equipment()])

    def request_equipment(self):
        item_id = selected(self.equipment_tree, "an equipment item")
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
        item_id = selected(self.equipment_tree, "an equipment item")
        if item_id and messagebox.askyesno("Confirm Delete", "Remove this equipment item? This cannot be undone."):
            equipment_service.delete_equipment(item_id)
            self.load_equipment()

    # ---------- Borrowing (Admin and Staff) ----------

    def _build_pending(self, tab):
        toolbar(tab, [("Refresh", self.load_pending),
                      ("Approve", self.approve_request, 100, GREEN, GREEN_H),
                      ("Deny", self.deny_request, 100, RED, RED_H)], pady=(8, 4))
        self.pending_tree = table(tab, PENDING_COLS, 14)
        self.load_pending()

    def load_pending(self):
        fill(self.pending_tree, [(r["id"], r["borrower_name"], r["borrower_role"], r["equipment_name"],
                                  r["quantity"], r["request_date"], r["due_date"] or "-")
                                 for r in borrow_service.get_pending_requests()])

    def _pending_request(self):
        rid = selected(self.pending_tree, "a pending request")
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

    def _build_active(self, tab):
        toolbar(tab, [("Refresh", self.load_active)], pady=(8, 4))
        self.active_tree = table(tab, ACTIVE_COLS, 14)
        self.load_active()

    def load_active(self):
        fill(self.active_tree, [(r["id"], r["borrower_name"], r["borrower_role"], r["equipment_name"],
                                 r["quantity"], r["request_date"], r["due_date"] or "-",
                                 r["approved_by_name"] or "-")
                                for r in borrow_service.get_active_transactions()])

    # ---------- shared ----------

    def logout(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()
import customtkinter as ctk
from tkinter import ttk, messagebox

from ui import colors
from ui.helpers import button, goto_login, label
from database import get_connection
import borrow_service
import equipment_service
import auth

ROLE_OPTIONS = ["Admin", "Student", "Teacher", "Staff"]

BLUE = (colors.BUTTON_BLUE, colors.BUTTON_BLUE_HOVER)
GREEN = (colors.SUCCESS_GREEN, "#166838")
RED = (colors.ACCENT_RED, "#b52a48")

def execute(sql, params):
    """Run one UPDATE/DELETE and save it."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    cursor.close()
    conn.close()
 
 
def toolbar(tab, *buttons):
    """Row of buttons above a table. Each button is (text, command) or (text, command, style)."""
    bar = ctk.CTkFrame(tab, fg_color=colors.BG_LIGHT)
    bar.pack(fill="x", pady=(8, 4))
    for text, command, *style in buttons:
        tool(bar, text, command, *style)
    return bar
 
 
def tool(bar, text, command, style=BLUE):
    button(bar, text, command, w=max(100, len(text) * 9), h=28, fg=style[0], hover=style[1]).pack(side="left", padx=(0, 6))
 
 
def make_tree(tab, columns, widths):
    """Create a table with the given column names and widths."""
    tree = ttk.Treeview(tab, columns=columns, show="headings", height=16)
    for col, width in zip(columns, widths):
        tree.heading(col, text=col.replace("_", " ").title())
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, pady=10)
    return tree
 
 
def fill_tree(tree, rows):
    """Replace the table content. rows = iterable of (row id, tuple of cell values)."""
    tree.delete(*tree.get_children())
    for iid, values in rows:
        tree.insert("", "end", iid=str(iid), values=values)
 
 
def selected(tree, what):
    """Return the selected row id, or show a hint and return None."""
    rows = tree.selection()
    if not rows:
        messagebox.showinfo("No selection", f"Please select {what} first.")
    return rows[0] if rows else None
 
 
class AdminDashboard(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.title("ICCT Equipment Borrowing System")
        self.geometry("1060x620")
        self.configure(fg_color=colors.BG_LIGHT)
 
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
 
        header = ctk.CTkFrame(self, fg_color=colors.NAVY_DARK, height=70, corner_radius=0)
        header.pack(fill="x")
        label(header, "Admin Dashboard", 20, True, "white").pack(side="left", padx=20, pady=15)
        button(header, "Log Out", lambda: goto_login(self), h=28, fg=RED[0], hover=RED[1]).pack(side="right", padx=20, pady=15)
 
        self.tabview = self._tabs(self)
        if user["role"] == "Admin":  # only Admin manages users
            self.tabview.add("User Management")
            self._build_user_management_tab(self.tabview.tab("User Management"))
        self.tabview.add("Equipment")
        self._build_equipment_tab(self.tabview.tab("Equipment"))
        self.tabview.add("Borrowing")
        self._build_borrowing_tab(self.tabview.tab("Borrowing"))
 
    @staticmethod
    def _tabs(parent):
        tabs = ctk.CTkTabview(parent, fg_color=colors.BG_LIGHT, segmented_button_selected_color=colors.BUTTON_BLUE)
        tabs.pack(fill="both", expand=True, padx=20, pady=(14, 20))
        return tabs
 
    # ---------- User Management (Admin only) ----------
 
    def _build_user_management_tab(self, tab):
        bar = toolbar(
            tab,
            ("Add User", self.open_add_user),
            ("Refresh", self.load_users),
            ("Activate", lambda: self.update_status("active"), GREEN),
            ("Deactivate", lambda: self.update_status("inactive"), RED),
            ("Delete User", self.delete_selected_user, RED),
        )
        label(bar, "Set role:").pack(side="left", padx=(14, 6))
        self.role_var = ctk.StringVar(value="Student")
        ctk.CTkOptionMenu(bar, values=ROLE_OPTIONS, variable=self.role_var, width=110).pack(side="left", padx=(0, 6))
        tool(bar, "Apply Role", self.update_role)
 
        self.tree = make_tree(
            tab, ("id", "full_name", "student_number", "email", "role", "email_verified", "status", "created_at"),
            (40, 160, 120, 200, 80, 100, 80, 140))
        self.load_users()
 
    def open_add_user(self):
        from ui.add_user import AddUserDialog
        AddUserDialog(self)
 
    def load_users(self):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        fill_tree(self.tree, ((u["id"], (
            n, u["full_name"], u["student_number"], u["email"], u["role"],
            "Yes" if u["email_verified"] else "No", u["status"], u["created_at"])) for n, u in enumerate(users, 1)))
 
    def update_status(self, status):
        user_id = selected(self.tree, "a user")
        if not user_id:
            return
        if int(user_id) == self.user["id"] and status != "active":
            return messagebox.showerror("Not Allowed", "You cannot deactivate your own account while logged in.")
        execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
        self.load_users()
 
    def update_role(self):
        user_id = selected(self.tree, "a user")
        if not user_id:
            return
        if int(user_id) == self.user["id"] and self.role_var.get() != self.user["role"]:
            return messagebox.showerror("Not Allowed", "You cannot change your own role while logged in.")
        execute("UPDATE users SET role = %s WHERE id = %s", (self.role_var.get(), user_id))
        self.load_users()
 
    def delete_selected_user(self):
        user_id = selected(self.tree, "a user")
        if not user_id:
            return
        if int(user_id) == self.user["id"]:
            return messagebox.showerror("Cannot Delete", "You cannot delete your own account while logged in.")
 
        full_name = self.tree.item(user_id, "values")[1]
        if not messagebox.askyesno("Confirm Delete", f"Permanently delete {full_name}'s account? This cannot be undone."):
            return
        ok, message = auth.delete_user(user_id)
        if ok:
            self.load_users()
        else:
            messagebox.showerror("Delete Failed", message)
 
    # ---------- Equipment (Admin and Staff) ----------
 
    def _build_equipment_tab(self, tab):
        buttons = [
            ("Register Equipment", self.open_add_equipment),
            ("Refresh", self.load_equipment),
            ("Delete Selected", self.delete_selected_equipment, RED),
        ]
        # Staff can borrow through this screen; Admin only manages the catalog and approvals.
        if self.user["role"] == "Staff":
            buttons.append(("Request to Borrow", self.open_request_equipment))
        toolbar(tab, *buttons)
 
        self.equipment_tree = make_tree(
            tab, ("id", "name", "category", "quantity", "available", "condition", "added_by", "created_at"),
            (40, 200, 140, 70, 80, 100, 160, 140))
        self.load_equipment()
 
    def open_add_equipment(self):
        from ui.add_equipment import AddEquipmentDialog
        AddEquipmentDialog(self, self.user)
 
    def load_equipment(self):
        fill_tree(self.equipment_tree, ((i["id"], (
            n, i["name"], i["category"], i["quantity"], borrow_service.get_available_quantity(i["id"]),
            i["condition_status"], i["added_by_name"] or "-", i["created_at"]))
            for n, i in enumerate(equipment_service.get_all_equipment(), 1)))
 
    def open_request_equipment(self):
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
                               on_success=lambda: (self.load_equipment(), self.load_pending_requests()))
 
    def delete_selected_equipment(self):
        item_id = selected(self.equipment_tree, "an equipment item")
        if item_id and messagebox.askyesno("Confirm Delete", "Remove this equipment item? This cannot be undone."):
            equipment_service.delete_equipment(item_id)
            self.load_equipment()
 
    # ---------- Borrowing (Admin and Staff) ----------
 
    def _build_borrowing_tab(self, tab):
        sub = self._tabs(tab)
        sub.pack_configure(padx=0, pady=0)
 
        sub.add("Pending Requests")
        pending = sub.tab("Pending Requests")
        toolbar(pending, ("Refresh", self.load_pending_requests), ("Approve", self.open_approve_dialog, GREEN),
                ("Deny", self.deny_selected_request, RED))
        self.pending_tree = make_tree(
            pending, ("id", "borrower", "role", "equipment", "quantity", "request_date", "proposed_due_date"),
            (40, 160, 80, 200, 70, 140, 120))
        self.load_pending_requests()
 
        sub.add("Active Transactions")
        active = sub.tab("Active Transactions")
        toolbar(active, ("Refresh", self.load_active_transactions))
        self.active_tree = make_tree(
            active, ("id", "borrower", "role", "equipment", "quantity", "borrowed_on", "due_date", "approved_by"),
            (40, 160, 80, 200, 70, 140, 110, 160))
        self.load_active_transactions()
 
    def load_pending_requests(self):
        fill_tree(self.pending_tree, ((r["id"], (
            n, r["borrower_name"], r["borrower_role"], r["equipment_name"], r["quantity"],
            r["request_date"], r["due_date"] or "-")) for n, r in enumerate(borrow_service.get_pending_requests(), 1)))
 
    def load_active_transactions(self):
        fill_tree(self.active_tree, ((r["id"], (
            n, r["borrower_name"], r["borrower_role"], r["equipment_name"], r["quantity"],
            r["request_date"], r["due_date"] or "-", r["approved_by_name"] or "-"))
            for n, r in enumerate(borrow_service.get_active_transactions(), 1)))
 
    def _selected_pending_request(self):
        request_id = selected(self.pending_tree, "a pending request")
        if not request_id:
            return None
        request = borrow_service.get_request_by_id(int(request_id))
        if not request or request["status"] != "Pending":
            messagebox.showinfo("Not Available", "This request is no longer pending.")
            self.load_pending_requests()
            return None
        return request
 
    def open_approve_dialog(self):
        request = self._selected_pending_request()
        if request:
            from ui.borrow import ApproveRequestDialog
            ApproveRequestDialog(self, self.user, request, on_success=lambda: (
                self.load_pending_requests(), self.load_active_transactions(), self.load_equipment()))
 
    def deny_selected_request(self):
        request = self._selected_pending_request()
        if not request or not messagebox.askyesno(
                "Confirm Deny", f"Deny the request for '{request['equipment_name']}' from {request['borrower_name']}?"):
            return
        ok, message = borrow_service.deny_request(request["id"], self.user["id"])
        if ok:
            self.load_pending_requests()
        else:
            messagebox.showerror("Deny Failed", message)
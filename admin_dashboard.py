import customtkinter as ctk
from tkinter import ttk, messagebox

from ui import colors
from database import get_connection
import borrow_service

ROLE_OPTIONS = ["Admin", "Student", "Teacher", "Staff"]


class AdminDashboard(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.title("ICCT Equipment Borrowing System")
        self.geometry("1060x620")
        self.configure(fg_color=colors.BG_LIGHT)

        header = ctk.CTkFrame(self, fg_color=colors.NAVY_DARK, height=70, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(
            header, text="Admin Dashboard", font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=15)
        ctk.CTkLabel(
            header, text=f"Signed in as {user['full_name']} ({user['role']})",
            font=ctk.CTkFont(size=12), text_color="#c7cede",
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            header, text="Log Out", width=100, fg_color=colors.ACCENT_RED,
            hover_color="#b52a48", command=self.logout,
        ).pack(side="right", padx=20, pady=15)

        self.tabview = ctk.CTkTabview(self, fg_color=colors.BG_LIGHT, segmented_button_selected_color=colors.BUTTON_BLUE)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(14, 20))

        if user["role"] == "Admin":
            self.tabview.add("User Management")
            self._build_user_management_tab(self.tabview.tab("User Management"))

        self.tabview.add("Equipment")
        self._build_equipment_tab(self.tabview.tab("Equipment"))

        self.tabview.add("Borrowing")
        self._build_borrowing_tab(self.tabview.tab("Borrowing"))

    # ---------- User Management tab (Admin only) ----------

    def _build_user_management_tab(self, tab):
        toolbar = ctk.CTkFrame(tab, fg_color=colors.BG_LIGHT)
        toolbar.pack(fill="x", pady=(4, 4))
        ctk.CTkButton(
            toolbar, text="Add User", width=100, fg_color=colors.BUTTON_BLUE,
            hover_color=colors.BUTTON_BLUE_HOVER, command=self.open_add_user,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="Refresh", width=100, command=self.load_users).pack(side="left")
        ctk.CTkButton(
            toolbar, text="Activate", width=100, fg_color=colors.SUCCESS_GREEN,
            hover_color="#166838", command=lambda: self.update_status("active"),
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            toolbar, text="Deactivate", width=100, fg_color=colors.ACCENT_RED,
            hover_color="#b52a48", command=lambda: self.update_status("inactive"),
        ).pack(side="left")
        ctk.CTkButton(
            toolbar, text="Delete User", width=100, fg_color=colors.ACCENT_RED,
            hover_color="#b52a48", command=self.delete_selected_user,
        ).pack(side="left", padx=6)

        ctk.CTkLabel(toolbar, text="Set role:", text_color=colors.TEXT_DARK).pack(side="left", padx=(20, 6))
        self.role_var = ctk.StringVar(value="Student")
        ctk.CTkOptionMenu(toolbar, values=ROLE_OPTIONS, variable=self.role_var, width=110).pack(side="left")
        ctk.CTkButton(toolbar, text="Apply Role", width=100, command=self.update_role).pack(side="left", padx=6)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        columns = ("id", "full_name", "student_number", "email", "role", "email_verified", "status", "created_at")
        self.tree = ttk.Treeview(tab, columns=columns, show="headings", height=16)
        widths = (40, 160, 120, 200, 80, 100, 80, 140)
        for col, width in zip(columns, widths):
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=10)

        self.load_users()

    def open_add_user(self):
        from ui.add_user import AddUserDialog
        AddUserDialog(self)

    def load_users(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        for row_num, u in enumerate(cursor.fetchall(), start=1):
            self.tree.insert(
                "", "end", iid=str(u["id"]),
                values=(
                    row_num, u["full_name"], u["student_number"], u["email"], u["role"],
                    "Yes" if u["email_verified"] else "No", u["status"], u["created_at"],
                ),
            )
        cursor.close()
        conn.close()

    def _get_selected_user_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Please select a user first.")
            return None
        return selected[0]

    def update_status(self, new_status):
        user_id = self._get_selected_user_id()
        if not user_id:
            return

        if int(user_id) == self.user["id"] and new_status != "active":
            messagebox.showerror(
                "Not Allowed", "You cannot deactivate your own account while logged in."
            )
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        self.load_users()

    def update_role(self):
        user_id = self._get_selected_user_id()
        if not user_id:
            return

        if int(user_id) == self.user["id"] and self.role_var.get() != self.user["role"]:
            messagebox.showerror(
                "Not Allowed", "You cannot change your own role while logged in."
            )
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = %s WHERE id = %s", (self.role_var.get(), user_id))
        conn.commit()
        cursor.close()
        conn.close()
        self.load_users()

    def delete_selected_user(self):
        user_id = self._get_selected_user_id()
        if not user_id:
            return

        if int(user_id) == self.user["id"]:
            messagebox.showerror(
                "Cannot Delete", "You cannot delete your own account while logged in."
            )
            return

        selected_values = self.tree.item(user_id, "values")
        full_name = selected_values[1] if selected_values else "this user"

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Permanently delete {full_name}'s account? This cannot be undone.",
        ):
            return

        import auth
        success, message = auth.delete_user(user_id)
        if success:
            self.load_users()
        else:
            messagebox.showerror("Delete Failed", message)

    # ---------- Equipment tab (Admin and Staff) ----------

    def _build_equipment_tab(self, tab):
        toolbar = ctk.CTkFrame(tab, fg_color=colors.BG_LIGHT)
        toolbar.pack(fill="x", pady=(4, 4))
        ctk.CTkButton(
            toolbar, text="Register Equipment", width=150, fg_color=colors.BUTTON_BLUE,
            hover_color=colors.BUTTON_BLUE_HOVER, command=self.open_add_equipment,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="Refresh", width=100, command=self.load_equipment).pack(side="left")
        ctk.CTkButton(
            toolbar, text="Delete Selected", width=130, fg_color=colors.ACCENT_RED,
            hover_color="#b52a48", command=self.delete_selected_equipment,
        ).pack(side="left", padx=6)

        # Staff can request to borrow equipment themselves; Admin manages
        # the catalog and approvals but doesn't borrow through this screen.
        if self.user["role"] == "Staff":
            ctk.CTkButton(
                toolbar, text="Request to Borrow", width=150, fg_color=colors.BUTTON_BLUE,
                hover_color=colors.BUTTON_BLUE_HOVER, command=self.open_request_equipment,
            ).pack(side="left", padx=6)

        columns = ("id", "name", "category", "quantity", "available", "condition", "added_by", "created_at")
        self.equipment_tree = ttk.Treeview(tab, columns=columns, show="headings", height=16)
        widths = (40, 200, 140, 70, 80, 100, 160, 140)
        for col, width in zip(columns, widths):
            self.equipment_tree.heading(col, text=col.replace("_", " ").title())
            self.equipment_tree.column(col, width=width, anchor="center")
        self.equipment_tree.pack(fill="both", expand=True, pady=10)

        self.load_equipment()

    def open_add_equipment(self):
        from ui.add_equipment import AddEquipmentDialog
        AddEquipmentDialog(self, self.user)

    def load_equipment(self):
        import equipment_service

        for row in self.equipment_tree.get_children():
            self.equipment_tree.delete(row)

        for row_num, item in enumerate(equipment_service.get_all_equipment(), start=1):
            available = borrow_service.get_available_quantity(item["id"])
            self.equipment_tree.insert(
                "", "end", iid=str(item["id"]),
                values=(
                    row_num, item["name"], item["category"], item["quantity"], available,
                    item["condition_status"], item["added_by_name"] or "-", item["created_at"],
                ),
            )

    def open_request_equipment(self):
        import equipment_service

        selected = self.equipment_tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Please select an equipment item first.")
            return

        item_id = int(selected[0])
        item = next((i for i in equipment_service.get_all_equipment() if i["id"] == item_id), None)
        if not item:
            messagebox.showerror("Not Found", "This equipment item no longer exists.")
            return

        available = borrow_service.get_available_quantity(item_id)
        if available <= 0:
            messagebox.showinfo("Unavailable", "There are no available units of this equipment right now.")
            return

        from ui.borrow import RequestEquipmentDialog
        RequestEquipmentDialog(
            self, self.user, item, available,
            on_success=lambda: (self.load_equipment(), self.load_pending_requests()),
        )

    def delete_selected_equipment(self):
        import equipment_service

        selected = self.equipment_tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Please select an equipment item first.")
            return
        if not messagebox.askyesno("Confirm Delete", "Remove this equipment item? This cannot be undone."):
            return
        equipment_service.delete_equipment(selected[0])
        self.load_equipment()

    # ---------- Borrowing tab (Admin and Staff) ----------

    def _build_borrowing_tab(self, tab):
        sub_tabview = ctk.CTkTabview(
            tab, fg_color=colors.BG_LIGHT, segmented_button_selected_color=colors.BUTTON_BLUE
        )
        sub_tabview.pack(fill="both", expand=True)

        sub_tabview.add("Pending Requests")
        self._build_pending_requests_tab(sub_tabview.tab("Pending Requests"))

        sub_tabview.add("Active Transactions")
        self._build_active_transactions_tab(sub_tabview.tab("Active Transactions"))

    def _build_pending_requests_tab(self, tab):
        toolbar = ctk.CTkFrame(tab, fg_color=colors.BG_LIGHT)
        toolbar.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(toolbar, text="Refresh", width=100, command=self.load_pending_requests).pack(side="left")
        ctk.CTkButton(
            toolbar, text="Approve", width=100, fg_color=colors.SUCCESS_GREEN,
            hover_color="#166838", command=self.open_approve_dialog,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            toolbar, text="Deny", width=100, fg_color=colors.ACCENT_RED,
            hover_color="#b52a48", command=self.deny_selected_request,
        ).pack(side="left")

        columns = ("id", "borrower", "role", "equipment", "quantity", "request_date", "proposed_due_date")
        self.pending_tree = ttk.Treeview(tab, columns=columns, show="headings", height=14)
        widths = (40, 160, 80, 200, 70, 140, 120)
        for col, width in zip(columns, widths):
            self.pending_tree.heading(col, text=col.replace("_", " ").title())
            self.pending_tree.column(col, width=width, anchor="center")
        self.pending_tree.pack(fill="both", expand=True, pady=10)

        self.load_pending_requests()

    def load_pending_requests(self):
        for row in self.pending_tree.get_children():
            self.pending_tree.delete(row)

        for row_num, r in enumerate(borrow_service.get_pending_requests(), start=1):
            self.pending_tree.insert(
                "", "end", iid=str(r["id"]),
                values=(
                    row_num, r["borrower_name"], r["borrower_role"], r["equipment_name"],
                    r["quantity"], r["request_date"], r["due_date"] or "-",
                ),
            )

    def _get_selected_pending_request(self):
        selected = self.pending_tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Please select a pending request first.")
            return None

        request_id = int(selected[0])
        request = borrow_service.get_request_by_id(request_id)

        if not request or request["status"] != "Pending":
            messagebox.showinfo("Not Available", "This request is no longer pending.")
            self.load_pending_requests()
            return None

        return request

    def open_approve_dialog(self):
        request = self._get_selected_pending_request()
        if not request:
            return

        from ui.borrow import ApproveRequestDialog
        ApproveRequestDialog(
            self, self.user, request,
            on_success=lambda: (
                self.load_pending_requests(),
                self.load_active_transactions(),
                self.load_equipment(),
            ),
        )

    def deny_selected_request(self):
        request = self._get_selected_pending_request()
        if not request:
            return

        if not messagebox.askyesno(
            "Confirm Deny",
            f"Deny the request for '{request['equipment_name']}' from {request['borrower_name']}?",
        ):
            return

        success, message = borrow_service.deny_request(request["id"], self.user["id"])
        if success:
            self.load_pending_requests()
        else:
            messagebox.showerror("Deny Failed", message)

    def _build_active_transactions_tab(self, tab):
        toolbar = ctk.CTkFrame(tab, fg_color=colors.BG_LIGHT)
        toolbar.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(toolbar, text="Refresh", width=100, command=self.load_active_transactions).pack(side="left")

        columns = ("id", "borrower", "role", "equipment", "quantity", "borrowed_on", "due_date", "approved_by")
        self.active_tree = ttk.Treeview(tab, columns=columns, show="headings", height=14)
        widths = (40, 160, 80, 200, 70, 140, 110, 160)
        for col, width in zip(columns, widths):
            self.active_tree.heading(col, text=col.replace("_", " ").title())
            self.active_tree.column(col, width=width, anchor="center")
        self.active_tree.pack(fill="both", expand=True, pady=10)

        self.load_active_transactions()

    def load_active_transactions(self):
        for row in self.active_tree.get_children():
            self.active_tree.delete(row)

        for row_num, r in enumerate(borrow_service.get_active_transactions(), start=1):
            self.active_tree.insert(
                "", "end", iid=str(r["id"]),
                values=(
                    row_num, r["borrower_name"], r["borrower_role"], r["equipment_name"],
                    r["quantity"], r["request_date"], r["due_date"] or "-", r["approved_by_name"] or "-",
                ),
            )

    # ---------- shared ----------

    def logout(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()
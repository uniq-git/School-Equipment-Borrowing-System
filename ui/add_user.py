"""
Admin-only dialog for creating Teacher, Staff, or Admin accounts directly.
Students self-register through the normal Register screen instead.

The role prefix (CA/FA/SF/AD) is applied automatically based on the
selected role, so it's impossible to create a mismatched ID number.
"""
import customtkinter as ctk

from ui import colors
from ui.helpers import FormDialog, entry, label
import auth

ROLE_OPTIONS = ["Teacher", "Staff", "Admin", "Student"]


class AddUserDialog(FormDialog):
    def __init__(self, parent):
        super().__init__(parent, "Add User", "380x740")
        f = self.f
 
        self.full_name_entry = f.entry("Full Name", "Enter your full name")
        self.role_var = ctk.StringVar(value=ROLE_OPTIONS[0])
        f.menu("Role", ROLE_OPTIONS, self.role_var, command=self._update_prefix)
 
        f.title("ID Number")  # prefix box + 9-digit box side by side
        id_row = f.place(ctk.CTkFrame(self, fg_color="transparent"))
        self.prefix_label = label(id_row, auth.ROLE_ID_PREFIXES[self.role_var.get()], 13, True, "black",
                                  fg_color=colors.CARD_WHITE, width=44, height=34, corner_radius=6)
        self.prefix_label.pack(side="left")
        self.digits_entry = entry(id_row, "9 digits, e.g. 202401234", w=244)
        self.digits_entry.pack(side="left", padx=(6, 0))
 
        self.email_entry = f.entry("Email Address", "Enter your email address")
        self.password_entry = f.password("Temporary Password", "At least 8 characters")
        self.confirm_entry = f.password("Confirm Password", "Re-enter password")
        self.footer("Create User", self.handle_submit, status_pady=(10, 0))
 
    def _update_prefix(self, role):
        self.prefix_label.configure(text=auth.ROLE_ID_PREFIXES[role])
 
    def handle_submit(self):
        password = self.password_entry.get()
        if password != self.confirm_entry.get():
            return self.show("Passwords do not match.")
 
        ok, message = auth.create_user(
            self.full_name_entry.get(), self.role_var.get(), self.digits_entry.get(),
            self.email_entry.get(), password)
        self.result(ok, message, getattr(self.parent, "load_users", None), 1500)
 
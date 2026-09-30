"""
Admin-only dialog for creating Teacher, Staff, or Admin accounts directly.
Students self-register through the normal Register screen instead.

The role prefix (CA/FA/SF/AD) is applied automatically based on the
selected role, so it's impossible to create a mismatched ID number.
"""
import customtkinter as ctk

from ui import colors
import auth

ROLE_OPTIONS = ["Teacher", "Staff", "Admin", "Student"]


class AddUserDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("Add User")
        self.geometry("380x740")
        self.resizable(False, False)
        self.configure(fg_color=colors.CARD_WHITE)

        self.transient(parent)
        self.grab_set()

        pad_x = 30

        ctk.CTkLabel(
            self, text="Add User", font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors.TEXT_DARK,
        ).pack(anchor="w", padx=pad_x, pady=(20, 4))
        self.full_name_entry = self._labeled_entry("Full Name", "Enter your full name", pad_x)

        ctk.CTkLabel(
            self, text="Role", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(14, 4))
        self.role_var = ctk.StringVar(value=ROLE_OPTIONS[0])
        ctk.CTkOptionMenu(
            self, values=ROLE_OPTIONS, variable=self.role_var, width=300,
            command=self._update_prefix,
        ).pack(anchor="w", padx=pad_x)

        ctk.CTkLabel(
            self, text="ID Number", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(14, 4))
        id_row = ctk.CTkFrame(self, fg_color="transparent")
        id_row.pack(anchor="w", padx=pad_x)
        self.prefix_label = ctk.CTkLabel(
            id_row, text=auth.ROLE_ID_PREFIXES[self.role_var.get()],
            font=ctk.CTkFont(size=13, weight="bold"), text_color="black",
            fg_color=colors.CARD_WHITE, width=44, height=34, corner_radius=6,
        )
        self.prefix_label.pack(side="left")
        self.digits_entry = ctk.CTkEntry(
            id_row, placeholder_text="9 digits, e.g. 202401234", width=244, height=34,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        self.digits_entry.pack(side="left", padx=(6, 0))
        self.email_entry = self._labeled_entry("Email Addres", "Enter your email address",pad_x)
        self.password_entry, _ = self._labeled_password("Temporary Password", "At least 8 characters", pad_x)
        self.confirm_entry, _ = self._labeled_password("Confirm Password", "Re-enter password", pad_x)

        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color=colors.ACCENT_RED,
            wraplength=300, justify="left",
        )
        self.status_label.pack(anchor="w", padx=pad_x, pady=(10, 0))

        ctk.CTkButton(
            self, text="Create User", height=40, width=300, fg_color=colors.BUTTON_BLUE,
            hover_color=colors.BUTTON_BLUE_HOVER, font=ctk.CTkFont(size=13, weight="bold"),
            command=self.handle_submit,
        ).pack(anchor="w", padx=pad_x, pady=(16, 6))

        ctk.CTkButton(
            self, text="Cancel", height=32, width=300, fg_color="transparent",
            hover_color=colors.BG_LIGHT, text_color=colors.TEXT_GRAY, command=self.destroy,
        ).pack(anchor="w", padx=pad_x)

    def _labeled_entry(self, label, placeholder, pad_x):
        ctk.CTkLabel(
            self, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(14, 4))
        entry = ctk.CTkEntry(
            self, placeholder_text=placeholder, height=34, width=300,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        entry.pack(anchor="w", padx=pad_x)
        return entry

    def _labeled_password(self, label, placeholder, pad_x):
        ctk.CTkLabel(
            self, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(14, 4))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=pad_x)
        entry = ctk.CTkEntry(
            row, placeholder_text=placeholder, show="*", height=34, width=245,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        entry.pack(side="left")
        btn = ctk.CTkButton(
            row, text="Show", width=48, height=34, fg_color=colors.ENTRY_BG,
            hover_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
            command=lambda: self._toggle(entry, btn),
        )
        btn.pack(side="left", padx=(6, 0))
        return entry, btn

    def _toggle(self, entry, btn):
        if entry.cget("show") == "*":
            entry.configure(show="")
            btn.configure(text="Hide")
        else:
            entry.configure(show="*")
            btn.configure(text="Show")

    def _update_prefix(self, role):
        self.prefix_label.configure(text=auth.ROLE_ID_PREFIXES[role])

    def handle_submit(self):
        full_name = self.full_name_entry.get()
        role = self.role_var.get()
        digits = self.digits_entry.get()
        email = self.email_entry.get()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        if password != confirm:
            self.status_label.configure(text="Passwords do not match.", text_color=colors.ACCENT_RED)
            return

        success, message = auth.create_user(full_name, role, digits, email, password)
        if success:
            self.status_label.configure(text=message, text_color=colors.SUCCESS_GREEN)
            if hasattr(self.parent, "load_users"):
                self.parent.load_users()
            self.after(1500, self.destroy)
        else:
            self.status_label.configure(text=message, text_color=colors.ACCENT_RED)
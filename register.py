"""
Registration screen: Full Name, Student Number, Email, Password, Confirm Password,
Send Verification Code / Verification Code / Verify Email, then Register.
"""
import threading
import customtkinter as ctk

from ui import colors
from ui.left_panel import build_left_panel
import auth
import email_service


class RegisterWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ICCT Colleges Foundation, Inc. - Register")
        self.geometry("973x680")
        self.resizable(False, False)
        self.configure(fg_color=colors.BG_LIGHT)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        build_left_panel(self, height=680).grid(row=0, column=0, sticky="nswe")

        right = ctk.CTkFrame(self, fg_color=colors.BG_LIGHT, corner_radius=0)
        right.grid(row=0, column=1, sticky="nswe")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        card = ctk.CTkScrollableFrame(
            right, fg_color=colors.CARD_WHITE, corner_radius=12, width=380, height=620,
            scrollbar_button_color=colors.BORDER_GRAY, scrollbar_fg_color=colors.CARD_WHITE,
        )
        card.grid(row=0, column=0, pady=18)

        pad_x = 30

        ctk.CTkLabel(
            card, text="Create an Account", font=ctk.CTkFont(size=24, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(18, 2))
        ctk.CTkLabel(
            card, text="Register to start borrowing equipment",
            font=ctk.CTkFont(size=12), text_color=colors.TEXT_GRAY,
        ).pack(anchor="w", padx=pad_x)

        self.full_name_entry = self._labeled_entry(card, "Full Name","Enter your full name", pad_x)
        self.student_number_entry = self._labeled_entry(card, "Student Number", "e.g. CA202401234", pad_x)
        self.email_entry = self._labeled_entry(card, "Email Address", "Emter your email address", pad_x)

        ctk.CTkButton(
            card, text="Send Verification Code", height=34, width=300, fg_color=colors.ENTRY_BG,
            hover_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
            font=ctk.CTkFont(size=12, weight="bold"), command=self.handle_send_code,
        ).pack(anchor="w", padx=pad_x, pady=(8, 0))

        ctk.CTkLabel(
            card, text="Verification Code", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(16, 4))
        code_row = ctk.CTkFrame(card, fg_color="transparent")
        code_row.pack(anchor="w", padx=pad_x)
        self.code_var = ctk.StringVar()
        self.code_var.trace_add("write", self._on_code_changed)
        self._last_auto_checked_code = None
        self.code_entry = ctk.CTkEntry(
            code_row, textvariable=self.code_var, placeholder_text="6-digit code", width=210, height=36,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        self.code_entry.pack(side="left")
        ctk.CTkButton(
            code_row, text="Verify Email", width=84, height=36, fg_color=colors.BUTTON_BLUE,
            hover_color=colors.BUTTON_BLUE_HOVER, command=self.handle_verify_code,
        ).pack(side="left", padx=(6, 0))

        self.verify_status_label = ctk.CTkLabel(
            card, text="Email not verified yet.", text_color=colors.TEXT_GRAY, font=ctk.CTkFont(size=11),
            wraplength=300, justify="left",
        )
        self.verify_status_label.pack(anchor="w", padx=pad_x, pady=(4, 0))

        self.password_entry, _ = self._labeled_password(card, "Password", "Create a password", pad_x)
        self.confirm_entry, _ = self._labeled_password(card, "Confirm Password", "Re-enter password", pad_x)

        self.error_label = ctk.CTkLabel(
            card, text="", text_color=colors.ACCENT_RED, font=ctk.CTkFont(size=12),
            wraplength=300, justify="left",
        )
        self.error_label.pack(anchor="w", padx=pad_x, pady=(10, 0))

        ctk.CTkButton(
            card, text="Register", height=42, width=300, fg_color=colors.BUTTON_BLUE,
            hover_color=colors.BUTTON_BLUE_HOVER, font=ctk.CTkFont(size=14, weight="bold"),
            command=self.handle_register,
        ).pack(anchor="w", padx=pad_x, pady=(18, 10))

        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(anchor="w", padx=pad_x, pady=(0, 22))
        ctk.CTkLabel(
            bottom, text="Already have an account?", text_color=colors.TEXT_GRAY, font=ctk.CTkFont(size=12)
        ).pack(side="left")
        ctk.CTkButton(
            bottom, text="Log in here", fg_color="transparent", hover=False,
            text_color=colors.LINK_BLUE, font=ctk.CTkFont(size=12, weight="bold"),
            width=20, command=self.open_login,
        ).pack(side="left", padx=(4, 0))

    # ---------- small helpers to build repeated widgets ----------

    def _labeled_entry(self, parent, label, placeholder, pad_x):
        ctk.CTkLabel(
            parent, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(16, 4))
        entry = ctk.CTkEntry(
            parent, placeholder_text=placeholder, height=36, width=300,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        entry.pack(anchor="w", padx=pad_x)
        return entry

    def _labeled_password(self, parent, label, placeholder, pad_x):
        ctk.CTkLabel(
            parent, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(16, 4))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(anchor="w", padx=pad_x)
        entry = ctk.CTkEntry(
            row, placeholder_text=placeholder, show="*", height=36, width=245,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        entry.pack(side="left")
        btn = ctk.CTkButton(
            row, text="Show", width=48, height=36, fg_color=colors.ENTRY_BG,
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

    # ---------- actions ----------

    def handle_send_code(self):
        email = self.email_entry.get().strip().lower()

        if not auth.is_valid_email(email):
            self.error_label.configure(text="Please enter a valid email address first.")
            return
        if auth.email_exists(email):
            self.error_label.configure(text="This email is already registered.")
            return

        self.error_label.configure(text="")
        self.verify_status_label.configure(text="Sending code...", text_color=colors.TEXT_GRAY)

        def worker():
            try:
                email_service.send_and_store_code(email)
                self.verify_status_label.configure(
                    text=f"Code sent to {email}. Check your inbox.", text_color=colors.TEXT_GRAY
                )
            except Exception as exc:
                self.verify_status_label.configure(
                    text=f"Failed to send email: {exc}", text_color=colors.ACCENT_RED
                )

        threading.Thread(target=worker, daemon=True).start()

    def _on_code_changed(self, *_args):
        """Auto-verify the moment a 6-digit code has been fully typed/pasted in."""
        code = self.code_var.get().strip()
        if len(code) == 6 and code.isdigit() and code != self._last_auto_checked_code:
            self._last_auto_checked_code = code
            self.handle_verify_code()

    def handle_verify_code(self):
        email = self.email_entry.get().strip().lower()
        code = self.code_entry.get().strip()

        if not code:
            self.error_label.configure(text="Please enter the verification code.")
            return

        ok, message = email_service.verify_code(email, code)
        self.error_label.configure(text="" if ok else message)
        self.verify_status_label.configure(
            text=message, text_color=colors.SUCCESS_GREEN if ok else colors.ACCENT_RED
        )

    def handle_register(self):
        full_name = self.full_name_entry.get()
        student_number = self.student_number_entry.get()
        email = self.email_entry.get()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        if password != confirm:
            self.error_label.configure(text="Passwords do not match.")
            return

        success, message = auth.register_user(full_name, student_number, email, password)
        if success:
            self.error_label.configure(text="")
            self.verify_status_label.configure(text=message, text_color=colors.SUCCESS_GREEN)
            self.after(1500, self.open_login)
        else:
            self.error_label.configure(text=message)

    def open_login(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()
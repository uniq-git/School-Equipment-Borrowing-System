"""
Forgot Password screen: verify your email with a 6-digit code, then set a new password.
Reuses the same email_service verification-code system as registration.
"""
import customtkinter as ctk

from ui import colors
from ui.helpers import AuthWindow, Fields, VerifyMixin, label, link
from ui.left_panel import build_left_panel
import auth


class ForgotPasswordWindow(VerifyMixin, AuthWindow):
    def __init__(self):
        super().__init__("Reset Password", 650, 560)
        card, f = self.card, Fields(self.card, 40, h=34, gap=14)
 
        label(card, "Reset Password", 26, True).pack(anchor="w", padx=40, pady=(32, 4))
        self.email_entry = f.entry("Email Address", "Enter your email address", gap=20)
        self.verify_section(f, "Verify")
        self.new_password_entry = f.password("New Password", "Create a new password")
        self.confirm_password_entry = f.password("Confirm New Password", "Re-enter new password")
 
        self.error_label = f.error()
        f.submit("Reset Password", self.handle_reset)
        f.place(link(card, "Back to Log In", self.open_login, w=140))
 
    def handle_reset(self):
        new_password = self.new_password_entry.get()
        if new_password != self.confirm_password_entry.get():
            return self.error_label.configure(text="Passwords do not match.")
 
        ok, message = auth.reset_password(self.email_entry.get(), new_password)
        if ok:
            self.done(message, self.open_login)
        else:
            self.error_label.configure(text=message)
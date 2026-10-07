"""
Registration screen: Full Name, Student Number, Email, Password, Confirm Password,
Send Verification Code / Verification Code / Verify Email, then Register.
"""
import threading
import customtkinter as ctk

from ui import colors
from ui.helpers import AuthWindow, Fields, VerifyMixin, label, link
from services import auth, email_service


class RegisterWindow(VerifyMixin, AuthWindow):
    must_exist = False # email must not be registered yet
    
    def __init__(self):
        super().__init__("Register", 680, 620, scroll=True)
        card, f = self.card, Fields(self.card, 30, h=36, gap=16)
 
        label(card, "Create an Account", 24, True).pack(anchor="w", padx=30, pady=(18, 2))
        self.full_name_entry = f.entry("Full Name", "Enter your full name")
        self.student_number_entry = f.entry("Student Number", "e.g. CA202401234")
        self.email_entry = f.entry("Email Address", "Enter your email address")
        self.verify_section(f, "Verify Email", send_h=34)
        self.password_entry = f.password("Password", "Create a password")
        self.confirm_entry = f.password("Confirm Password", "Re-enter password")
 
        self.error_label = f.error(pady=(10, 0))
        f.submit("Register", self.handle_register, h=42, pady=(18, 10))
 
        bottom = f.place(ctk.CTkFrame(card, fg_color="transparent"), (0, 22))
        label(bottom, "Already have an account?", 12, color=colors.TEXT_GRAY).pack(side="left")
        link(bottom, "Log in here", self.open_login).pack(side="left", padx=(4, 0))
    def handle_register(self):
        password = self.password_entry.get()
        if password != self.confirm_entry.get():
            return self.error_label.configure(text="Passwords do not match.")
 
        ok, message = auth.register_user(
            self.full_name_entry.get(), self.student_number_entry.get(), self.email_entry.get(), password)
        if ok:
            self.done(message, self.open_login)
        else:
            self.error_label.configure(text=message)
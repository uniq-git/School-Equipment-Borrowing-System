"""
Login screen: Student Number + Password, matching the attached design.
"""
import customtkinter as ctk

from ui import colors
from ui.helpers import AuthWindow, Fields, label, link
from services import auth

class LoginWindow(AuthWindow):
    def __init__(self):
        super().__init__("Equipment Borrowing System", 619, 440)
        card, f = self.card, Fields(self.card, 40, h=38)
 
        label(card, "Welcome Back", 26, True).pack(anchor="w", padx=40, pady=(36, 4))
        self.student_number_entry = f.entry("ID Number", "e.g. CA202401234", gap=24)
        self.password_entry = f.password("Password", "Enter your password", gap=18)
        self.password_entry.bind("<Return>", lambda e: self.handle_login())
        f.place(link(card, "Forgot password?", self.open_forgot_password, 11, False, anchor="w"), (4, 0))
 
        self.error_label = f.error()
        f.submit("Log In", self.handle_login, h=42, pady=(18, 10))
 
        bottom = f.place(ctk.CTkFrame(card, fg_color="transparent"))
        label(bottom, "New student?", 12, color=colors.TEXT_GRAY).pack(side="left")
        link(bottom, "Register here", self.open_register).pack(side="left", padx=(4, 0))
        f.place(label(card, "© ICCT Colleges Foundation, Inc.", 10, color=colors.TEXT_GRAY), (18, 0))
 
    def handle_login(self):
        success, message, user = auth.login_user(self.student_number_entry.get(), self.password_entry.get())
        self.error_label.configure(text="" if success else message)
        if not success:
            return
 
        self.destroy()
        if user["role"] in ("Admin", "Staff"):
            from ui.admin_dashboard import AdminDashboard
            AdminDashboard(user).mainloop()
        else:
            from ui.dashboard import DashboardWindow
            DashboardWindow(user).mainloop()
 
    def open_register(self):
        self.destroy()
        from ui.register import RegisterWindow
        RegisterWindow().mainloop()
 
    def open_forgot_password(self):
        self.destroy()
        from ui.forgot_password import ForgotPasswordWindow
        ForgotPasswordWindow().mainloop()
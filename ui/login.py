"""
Login screen: Student Number + Password, matching the attached design.
"""
import customtkinter as ctk

from ui import colors
from ui.left_panel import build_left_panel
import auth

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ICCT Colleges Foundation, Inc. - Equipment Borrowing System")
        self.geometry("973x619")
        self.resizable(False, False)
        self.configure(fg_color=colors.BG_LIGHT)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        build_left_panel(self).grid(row=0, column=0, sticky="nswe")

        right = ctk.CTkFrame(self, fg_color=colors.BG_LIGHT, corner_radius=0)
        right.grid(row=0, column=1, sticky="nswe")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(right, fg_color=colors.CARD_WHITE, corner_radius=12, width=380, height=440)
        card.grid(row=0, column=0)
        card.grid_propagate(False)

        pad_x = 40

        ctk.CTkLabel(
            card, text="Welcome Back", font=ctk.CTkFont(size=26, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(36, 4))

        ctk.CTkLabel(
            card, text="ID Number", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(24, 4))
        self.student_number_entry = ctk.CTkEntry(
            card, placeholder_text="e.g. CA202401234", fg_color=colors.ENTRY_BG,
            border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK, height=38, width=300,
        )
        self.student_number_entry.pack(anchor="w", padx=pad_x)

        ctk.CTkLabel(
            card, text="Password", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(18, 4))

        pw_frame = ctk.CTkFrame(card, fg_color="transparent")
        pw_frame.pack(anchor="w", padx=pad_x)
        self.password_entry = ctk.CTkEntry(
            pw_frame, placeholder_text="Enter your password", show="*", fg_color=colors.ENTRY_BG,
            border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK, height=38, width=245,
        )
        self.password_entry.pack(side="left")
        self.password_entry.bind("<Return>", lambda e: self.handle_login())
        self.show_btn = ctk.CTkButton(
            pw_frame, text="Show", width=48, height=38, fg_color=colors.ENTRY_BG,
            hover_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK, command=self.toggle_password,
        )
        self.show_btn.pack(side="left", padx=(6, 0))

        ctk.CTkButton(
            card, text="Forgot password?", fg_color="transparent", hover=False,
            text_color=colors.LINK_BLUE, font=ctk.CTkFont(size=11),
            anchor="w", width=20, command=self.open_forgot_password,
        ).pack(anchor="w", padx=pad_x, pady=(4, 0))

        self.error_label = ctk.CTkLabel(
            card, text="", text_color=colors.ACCENT_RED, font=ctk.CTkFont(size=12),
            wraplength=300, justify="left",
        )
        self.error_label.pack(anchor="w", padx=pad_x, pady=(8, 0))

        ctk.CTkButton(
            card, text="Log In", height=42, width=300, fg_color=colors.BUTTON_BLUE,
            hover_color=colors.BUTTON_BLUE_HOVER, font=ctk.CTkFont(size=14, weight="bold"),
            command=self.handle_login,
        ).pack(anchor="w", padx=pad_x, pady=(18, 10))

        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(anchor="w", padx=pad_x)
        ctk.CTkLabel(
            bottom, text="New student?", text_color=colors.TEXT_GRAY, font=ctk.CTkFont(size=12)
        ).pack(side="left")
        ctk.CTkButton(
            bottom, text="Register here", fg_color="transparent", hover=False,
            text_color=colors.LINK_BLUE, font=ctk.CTkFont(size=12, weight="bold"),
            width=20, command=self.open_register,
        ).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(
            card, text="© ICCT Colleges Foundation, Inc.", text_color=colors.TEXT_GRAY,
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=pad_x, pady=(18, 0))

    def toggle_password(self):
        if self.password_entry.cget("show") == "*":
            self.password_entry.configure(show="")
            self.show_btn.configure(text="Hide")
        else:
            self.password_entry.configure(show="*")
            self.show_btn.configure(text="Show")

    def handle_login(self):
        student_number = self.student_number_entry.get()
        password = self.password_entry.get()

        success, message, user = auth.login_user(student_number, password)
        self.error_label.configure(text="" if success else message)

        if success:
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
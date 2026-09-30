"""
Phase 1 entry point: Login + Registration + Email Verification + User Management.

Before running:
1. Start Apache and MySQL in the XAMPP Control Panel.
2. Copy .env.example to .env and fill in your DB / SMTP settings.
3. pip install -r requirements.txt
4. Make sure the database/tables already exist (this app no longer
   creates them automatically on startup).
5. python main.py

Every account has an ID Number in the format <prefix><9 digits>:
  Student: CA   Teacher: TC   Staff: SF   Admin: AD
Students self-register through the Register screen (always gets a CA
number). Teacher/Staff/Admin accounts are created by an Admin from the
"Add User" button on the Admin dashboard, which applies the correct
prefix automatically.
"""
import customtkinter as ctk
from ui.login import LoginWindow

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
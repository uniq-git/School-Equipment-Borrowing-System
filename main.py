"""
Entry point: Login, Registration, Email Verification, User and Equipment Management, Borrowing, Returns, Overdue Monitoring and Reports.

Before running:
1. Start Apache and MySQL in the XAMPP Control Panel.
2. Copy .env.example to .env and fill in your DB / SMTP settings.
3. pip install -r requirements.txt
4. python scripts/set_admin_password.py   (first time only: creates the Admin account)
5. python main.py
   (On startup the app creates the database and tables if they are missing,
   and adds any newer columns to an older database.)

Every account has an ID Number in the format <prefix><9 digits>:
  Student: CA   Teacher: TC   Staff: SF   Admin: AD
Students self-register through the Register screen (always gets a CA
number). Teacher/Staff/Admin accounts are created by an Admin from the
"Add User" button on the Admin dashboard, which applies the correct
prefix automatically.
"""
import os
import sys

# Put the project root on the path so "database", "config", "services" and "ui" can be imported.
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from services import borrow_service  # noqa: E402
import customtkinter as ctk
from ui.login import LoginWindow

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
ctk.ThemeManager.theme["CTkFont"]["family"] = "Arial"


def upgrade_existing_database():
    """
    Create the database and tables if they do not exist yet, and add any newer
    columns (return, purpose, cancel and password-change columns) to an existing database.
    Safe to run every time; it never deletes data.
    """
    try:
        from database import init_database  # also runs upgrade_database() at the end
        init_database()
    except Exception as exc:  # the app can still open, e.g. if MySQL is not running yet
        print(f"Could not upgrade the database: {exc}")


if __name__ == "__main__":
    upgrade_existing_database()
    borrow_service.start_overdue_checker()  # overdue reminders, even when no Admin dashboard is open
    app = LoginWindow()
    app.mainloop()
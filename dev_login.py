"""
so instead normally typing py main.py and student no, password.
    python dev_login.py admin
    python dev_login.py staff
    python dev_login.py teacher
    python dev_login.py student
"""
import sys

import customtkinter as ctk
import database
from database import get_connection

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

VALID_ROLES = ("Admin", "Staff", "Student", "Teacher")


def get_first_user_by_role(role):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE role = %s ORDER BY created_at ASC LIMIT 1", (role,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1].capitalize() not in VALID_ROLES:
        print("Usage: python dev_login.py <admin|staff|student|teacher>")
        sys.exit(1)

    role = sys.argv[1].capitalize()
    database.init_database()
    user = get_first_user_by_role(role)

    if not user:
        print(f"No {role} account exists in the database yet. Register/create one first.")
        sys.exit(1)

    print(f"Opening dashboard as {user['full_name']} ({role})...")

    if role in ("Admin", "Staff"):
        from ui.admin_dashboard import AdminDashboard
        AdminDashboard(user).mainloop()
    else:
        from ui.dashboard import DashboardWindow
        DashboardWindow(user).mainloop()
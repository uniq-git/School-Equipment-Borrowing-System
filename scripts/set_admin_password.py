"""
Create the first Admin account, or reset an Admin's password.
    python scripts/set_admin_password.py

The Admin's ID Number is AD + 9 digits (e.g. AD000000001).
"""
import getpass
import os
import sys

# Make the project root (database, config, services) importable from scripts/.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services import auth
import database
from database import get_connection


def main():
    database.init_database()  # makes sure the database and tables exist

    digits = input("Admin ID number - 9 digits after 'AD' [000000001]: ").strip() or "000000001"
    id_number = f"AD{digits}"

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, full_name FROM users WHERE student_number = %s", (id_number,))
    existing = cursor.fetchone()
    cursor.close()
    conn.close()

    password = getpass.getpass("New password (at least 8 characters): ")
    if len(password) < 8:
        print("Password must be at least 8 characters long.")
        return
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match.")
        return

    if existing:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password = %s, status = 'active', email_verified = 1, "
            "failed_logins = 0, locked_until = NULL WHERE id = %s",
            (auth.hash_password(password), existing["id"]),
        )
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Password reset for {existing['full_name']} ({id_number}).")
        return

    full_name = input("Full name: ").strip()
    email = input("Email address: ").strip()
    ok, message = auth.create_user(full_name, "Admin", digits, email, password)
    print(message)


if __name__ == "__main__":
    main()
import re
from datetime import datetime, timedelta

import bcrypt

from database import get_connection
from services import email_service


# ID prefix for each role.
ROLE_ID_PREFIXES = {
    "Student": "CA",
    "Teacher": "TC",
    "Staff": "SF",
    "Admin": "AD",
}

# Login lockout: this many wrong passwords locks the account for a few minutes.
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 5
WRONG_LOGIN = "Incorrect ID number or password."

# The password hash that used to be built into database.py. It is public, so it is refused at login.
LEAKED_DEFAULT_HASH = "$2b$12$0/gqGsKbQMjHC7YA/40t5eQCHJar3QM/CWs6Lwa60lYGd9tS/Lqpy"

# General ID format used for login.
ID_NUMBER_PATTERN = re.compile(r"^[A-Z]{2}\d{9}$")

# Student ID format used during registration.
STUDENT_NUMBER_PATTERN = re.compile(r"^CA\d{9}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_student_number(student_number):
    return bool(STUDENT_NUMBER_PATTERN.match(student_number.strip().upper()))


def is_valid_id_number(id_number):
    """Check if the ID number has the correct format."""
    id_number = id_number.strip().upper()

    if not ID_NUMBER_PATTERN.match(id_number):
        return False

    return id_number[:2] in ROLE_ID_PREFIXES.values()


def is_valid_email(email):
    return bool(EMAIL_PATTERN.match(email.strip()))


def hash_password(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def check_password(password, hashed):
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed.encode("utf-8")
    )


def student_number_exists(student_number):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE student_number = %s",
        (student_number,)
    )

    exists = cursor.fetchone() is not None

    cursor.close()
    conn.close()

    return exists


def email_exists(email):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email = %s",
        (email,)
    )

    exists = cursor.fetchone() is not None

    cursor.close()
    conn.close()

    return exists


def get_user_by_email(email):
    email = email.strip().lower()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email = %s",
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user


def reset_password(email, new_password):
    """
    Change the password for an existing account.
    The email must be verified first.
    """
    email = email.strip().lower()

    if not is_valid_email(email):
        return False, "Please enter a valid email address."

    if len(new_password) < 8:
        return False, "Password must be at least 8 characters long."

    user = get_user_by_email(email)

    if not user:
        return False, "No account found with that email address."

    if not email_service.is_email_verified(email):
        return False, "Please verify your email address first."

    hashed = hash_password(new_password)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET password = %s, failed_logins = 0, locked_until = NULL, "
        "must_change_password = 0 WHERE email = %s",
        (hashed, email)
    )

    conn.commit()
    cursor.close()
    conn.close()

    email_service.clear_verification(email)  # the code can only be used once

    return True, "Password reset successfully! You can now log in."


def change_password_verified(user_id, current_password, new_password):
    """
    Change the password after the email code is verified.
    Requires the user's current password to be provided and correct.
    """
    if not current_password:
        return False, "Please enter your current password."

    if len(new_password) < 8:
        return False, "New password must be at least 8 characters long."

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE id = %s",
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return False, "User account not found."

    if not check_password(current_password, user["password"]):
        return False, "Current password is incorrect."

    email = user["email"]

    if not email_service.is_email_verified(email):
        return False, "Please verify your email with the code first."

    hashed = hash_password(new_password)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET password = %s, must_change_password = 0 WHERE id = %s",
        (hashed, user_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    email_service.clear_verification(email)  # the code can only be used once

    return True, "Password changed successfully!"

def register_user(full_name, student_number, email, password, role="Student"):
    """
    Check the registration details and create a new account.
    """
    role = "Student"  # self-registration can never create Teacher / Staff / Admin accounts

    full_name = full_name.strip()
    student_number = student_number.strip().upper()
    email = email.strip().lower()

    if not full_name:
        return False, "Full name is required."

    if not is_valid_student_number(student_number):
        return False, "Student number must follow the format CA + 9 digits (e.g. CA202401234)."

    if not is_valid_email(email):
        return False, "Please enter a valid email address."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if student_number_exists(student_number):
        return False, "This student number is already registered."

    if email_exists(email):
        return False, "This email address is already registered."

    if not email_service.is_email_verified(email):
        return False, "Please verify your email address before registering."

    hashed = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (full_name, student_number, email, password, role, email_verified, status) "
        "VALUES (%s, %s, %s, %s, %s, 1, 'active')",
        (full_name, student_number, email, hashed, role),
    )

    conn.commit()
    cursor.close()
    conn.close()

    email_service.clear_verification(email)  # the code can only be used once

    return True, "Registration successful! You can now log in."


def _set_login_state(user_id, failed_logins, locked_until=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET failed_logins = %s, locked_until = %s WHERE id = %s",
        (failed_logins, locked_until, user_id)
    )

    conn.commit()
    cursor.close()
    conn.close()


def login_user(id_number, password):
    """
    Check the login details and return the user's account.
    Too many wrong passwords locks the account for a few minutes.
    """
    id_number = id_number.strip().upper()

    if not is_valid_id_number(id_number):
        return False, "Please enter a valid ID number.", None

    if not password:
        return False, "Please enter your password.", None

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE student_number = %s",
        (id_number,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return False, WRONG_LOGIN, None  # same message as a wrong password

    now = datetime.now()

    if user.get("locked_until") and user["locked_until"] > now:
        minutes = int((user["locked_until"] - now).total_seconds() // 60) + 1
        return False, f"Too many failed attempts. Try again in {minutes} minute(s).", None

    if not check_password(password, user["password"]):
        failed = (user.get("failed_logins") or 0) + 1

        if failed >= MAX_LOGIN_ATTEMPTS:
            _set_login_state(user["id"], 0, now + timedelta(minutes=LOCKOUT_MINUTES))
            return False, f"Too many failed attempts. Try again in {LOCKOUT_MINUTES} minute(s).", None

        _set_login_state(user["id"], failed)
        return False, WRONG_LOGIN, None

    if user["password"] == LEAKED_DEFAULT_HASH:
        return False, "This account still uses the old default password. Run set_admin_password.py to set a new one.", None

    if not user["email_verified"]:
        return False, "Please verify your email before logging in.", None

    if user["status"] != "active":
        return False, "Your account has been deactivated. Please contact the administrator.", None

    if user.get("failed_logins") or user.get("locked_until"):
        _set_login_state(user["id"], 0)

    return True, "Login successful.", user


def delete_user(user_id):
    """
    Delete a user account from the database.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE id = %s",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return False, "User account not found."

    # A user who still has equipment out cannot be deleted.
    cursor.execute(
        "SELECT COUNT(*) AS active FROM borrow_requests "
        "WHERE user_id = %s AND status = 'Approved'",
        (user_id,)
    )

    if cursor.fetchone()["active"] > 0:
        cursor.close()
        conn.close()
        return False, "Cannot Delete \u2014 Has Active Records"

    # A user with borrowing records is deactivated instead, so the history is kept.
    cursor.execute(
        "SELECT COUNT(*) AS records FROM borrow_requests WHERE user_id = %s",
        (user_id,)
    )

    if cursor.fetchone()["records"] > 0:
        cursor.execute(
            "UPDATE users SET status = 'inactive' WHERE id = %s",
            (user_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, (f"{user['full_name']} has borrowing records, so the account was "
                      "deactivated instead of deleted to keep the history.")

    cursor.execute(
        "DELETE FROM users WHERE id = %s",
        (user_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, f"{user['full_name']}'s account has been deleted."


def create_user(full_name, role, digits, email, password):
    """
    Create a Teacher, Staff, or Admin account from the Admin screen.
    """
    full_name = full_name.strip()
    email = email.strip().lower()
    digits = digits.strip()

    if role not in ROLE_ID_PREFIXES:
        return False, "Please select a valid role."

    if not full_name:
        return False, "Full name is required."

    if not re.match(r"^\d{9}$", digits):
        return False, "ID number must be exactly 9 digits."

    if not is_valid_email(email):
        return False, "Please enter a valid email address."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    id_number = f"{ROLE_ID_PREFIXES[role]}{digits}"

    if student_number_exists(id_number):
        return False, "This ID number is already registered."

    if email_exists(email):
        return False, "This email address is already registered."

    hashed = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (full_name, student_number, email, password, role, email_verified, status, "
        "must_change_password) VALUES (%s, %s, %s, %s, %s, 1, 'active', 1)",  # temporary password: must change it
        (full_name, id_number, email, hashed, role),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, f"{role} account created! ID Number: {id_number}"


def set_user_status(user_id, status):
    """Activate or deactivate an account."""
    if status not in ("active", "inactive"):
        return False, "Invalid status."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True, f"Account is now {status}."


def set_user_role(user_id, role):
    """
    Change an account's role. The ID number prefix follows the role
    (e.g. CA -> TC for Student -> Teacher), keeping the same 9 digits.
    """
    if role not in ROLE_ID_PREFIXES:
        return False, "Please select a valid role."

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT student_number, role FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return False, "User account not found."

    if user["role"] == role:
        cursor.close()
        conn.close()
        return True, "The account already has that role."

    new_id = ROLE_ID_PREFIXES[role] + user["student_number"][2:]

    cursor.execute("SELECT id FROM users WHERE student_number = %s AND id != %s", (new_id, user_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return False, f"Cannot change the role: ID number {new_id} is already used by another account."

    cursor.execute("UPDATE users SET role = %s, student_number = %s WHERE id = %s", (role, new_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True, f"Role changed to {role}. The new ID number is {new_id}."
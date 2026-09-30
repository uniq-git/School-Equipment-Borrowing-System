import re
import bcrypt

from database import get_connection
import email_service


# ID prefix for each role.
ROLE_ID_PREFIXES = {
    "Student": "CA",
    "Teacher": "TC",
    "Staff": "SF",
    "Admin": "AD",
}

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
        "UPDATE users SET password = %s WHERE email = %s",
        (hashed, email)
    )

    conn.commit()
    cursor.close()
    conn.close()

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
        "UPDATE users SET password = %s WHERE id = %s",
        (hashed, user_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, "Password changed successfully!"

def register_user(full_name, student_number, email, password, role="Student"):
    """
    Check the registration details and create a new account.
    """
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

    return True, "Registration successful! You can now log in."


def login_user(id_number, password):
    """
    Check the login details and return the user's account.
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
        return False, "No account found with that ID number.", None

    if not check_password(password, user["password"]):
        return False, "Incorrect password.", None

    if not user["email_verified"]:
        return False, "Please verify your email before logging in.", None

    if user["status"] != "active":
        return False, "Your account has been deactivated. Please contact the administrator.", None

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
        "INSERT INTO users (full_name, student_number, email, password, role, email_verified, status) "
        "VALUES (%s, %s, %s, %s, %s, 1, 'active')",
        (full_name, id_number, email, hashed, role),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, f"{role} account created! ID Number: {id_number}"
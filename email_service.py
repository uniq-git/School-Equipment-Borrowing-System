import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import config
from database import get_connection


def generate_code():
    """Make a random 6-digit code."""
    return f"{random.randint(0, 999999):06d}"


def save_verification_code(email, code):
    """Save the code in the database."""
    conn = get_connection()
    cursor = conn.cursor()

    expires_at = datetime.now() + timedelta(
        minutes=config.CODE_EXPIRY_MINUTES
    )

    # Delete the old code so the new one is the only valid code.
    cursor.execute(
        "DELETE FROM email_verifications WHERE email = %s",
        (email,)
    )

    cursor.execute(
        "INSERT INTO email_verifications "
        "(email, code, expires_at) VALUES (%s, %s, %s)",
        (email, code, expires_at),
    )

    conn.commit()
    cursor.close()
    conn.close()


def send_verification_email(email, code):
    """Send the code to the student's email."""
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP is not configured. Please set SMTP_USER and SMTP_PASSWORD "
            "in your .env file."
        )

    subject = "Your ICCT Equipment Borrowing System Verification Code"

    body = (
        "Hello,\n\n"
        f"Your email verification code is: {code}\n"
        f"This code will expire in {config.CODE_EXPIRY_MINUTES} minutes.\n\n"
        "If you did not request this, you can safely ignore this email.\n\n"
        "- ICCT Colleges Foundation, Inc."
    )

    msg = MIMEMultipart()
    msg["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_USER}>"
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_USER, email, msg.as_string())


def send_and_store_code(email):
    """Make a code, save it, and send it by email."""
    code = generate_code()
    save_verification_code(email, code)
    send_verification_email(email, code)

    return code


def verify_code(email, code):
    """Check if the code entered by the student is correct."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM email_verifications WHERE email = %s "
        "ORDER BY created_at DESC LIMIT 1",
        (email,),
    )

    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        return False, "Please request a verification code first."

    if row["code"] != code:
        cursor.close()
        conn.close()
        return False, "Incorrect verification code."

    if datetime.now() > row["expires_at"]:
        cursor.close()
        conn.close()
        return False, "This code has expired. Please request a new one."

    cursor.execute(
        "UPDATE email_verifications SET is_verified = 1 WHERE id = %s",
        (row["id"],)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, "Email verified successfully!"


def is_email_verified(email):
    """Check if the email was already verified."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT id FROM email_verifications "
        "WHERE email = %s AND is_verified = 1 "
        "ORDER BY created_at DESC LIMIT 1",
        (email,),
    )

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row is not None
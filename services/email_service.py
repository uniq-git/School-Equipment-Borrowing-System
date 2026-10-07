import hmac
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import config
from database import get_connection

MAX_CODE_ATTEMPTS = 5   # wrong guesses allowed per code
RESEND_SECONDS = 60     # wait this long before another code can be requested


SMTP_TIMEOUT_SECONDS = 20  # give up instead of freezing the app when the mail server does not answer


def _deliver(msg, recipients):
    """Send one prepared message through the SMTP server from .env."""
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_USER, recipients, msg.as_string())


class CodeRequestError(Exception):
    """A problem that is safe to show the user (e.g. asking for codes too fast)."""


def generate_code():
    """Make a random 6-digit code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def save_verification_code(email, code):
    """Save the code in the database (one new code per RESEND_SECONDS)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT TIMESTAMPDIFF(SECOND, created_at, NOW()) AS age FROM email_verifications "
        "WHERE email = %s ORDER BY created_at DESC LIMIT 1",
        (email,)
    )
    last = cursor.fetchone()

    if last and last["age"] is not None and last["age"] < RESEND_SECONDS:
        cursor.close()
        conn.close()
        raise CodeRequestError(f"Please wait {RESEND_SECONDS - last['age']} seconds before requesting a new code.")

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

    _deliver(msg, email)


def send_and_store_code(email):
    """Make a code, save it, and send it by email."""
    code = generate_code()
    save_verification_code(email, code)

    try:
        send_verification_email(email, code)
    except Exception:
        clear_verification(email)  # nothing was delivered, so don't make the user wait
        raise

    return code


def verify_code(email, code):
    """Check if the code entered by the student is correct (single use, limited tries)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM email_verifications WHERE email = %s "
        "ORDER BY created_at DESC LIMIT 1",
        (email,),
    )

    row = cursor.fetchone()
    message = None

    if not row:
        message = "Please request a verification code first."
    elif datetime.now() > row["expires_at"]:
        message = "This code has expired. Please request a new one."
    elif row["attempts"] >= MAX_CODE_ATTEMPTS:
        message = "Too many incorrect attempts. Please request a new code."
    elif not hmac.compare_digest(row["code"].encode(), code.encode()):
        cursor.execute(
            "UPDATE email_verifications SET attempts = attempts + 1 WHERE id = %s",
            (row["id"],)
        )
        conn.commit()
        message = "Incorrect verification code."

    if message:
        cursor.close()
        conn.close()
        return False, message

    # Verified: keep it valid for another CODE_EXPIRY_MINUTES so the form can be finished.
    cursor.execute(
        "UPDATE email_verifications SET is_verified = 1, expires_at = %s WHERE id = %s",
        (datetime.now() + timedelta(minutes=config.CODE_EXPIRY_MINUTES), row["id"])
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, "Email verified successfully!"


def is_email_verified(email):
    """Check if the email was verified recently (and the verification was not used yet)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT id FROM email_verifications "
        "WHERE email = %s AND is_verified = 1 AND expires_at > %s "
        "ORDER BY created_at DESC LIMIT 1",
        (email, datetime.now()),
    )

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row is not None


def clear_verification(email):
    """Throw away the codes for this email (call after a verification has been used)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM email_verifications WHERE email = %s", (email,))

    conn.commit()
    cursor.close()
    conn.close()


def send_overdue_reminder(email, borrower_name, equipment_name, quantity, due_date, days_overdue):
    """Email a borrower that their equipment is overdue."""
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP is not configured. Please set SMTP_USER and SMTP_PASSWORD "
            "in your .env file."
        )

    due_text = due_date.strftime("%B %d, %Y") if hasattr(due_date, "strftime") else str(due_date)

    body = (
        f"Hello {borrower_name},\n\n"
        f"This is a reminder that the equipment you borrowed is overdue:\n\n"
        f"  Equipment: {equipment_name} (x{quantity})\n"
        f"  Due date: {due_text}\n"
        f"  Days overdue: {days_overdue}\n\n"
        "Please return it to the equipment office as soon as possible.\n\n"
        "- ICCT Colleges Foundation, Inc."
    )

    msg = MIMEMultipart()
    msg["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_USER}>"
    msg["To"] = email
    msg["Subject"] = "Overdue Equipment Reminder - ICCT Equipment Borrowing System"
    msg.attach(MIMEText(body, "plain"))

    _deliver(msg, email)


def send_denial_notice(email, borrower_name, equipment_name, quantity, reason=None):
    """Email a borrower that their borrow request was denied."""
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP is not configured. Please set SMTP_USER and SMTP_PASSWORD "
            "in your .env file."
        )

    body = (
        f"Hello {borrower_name},\n\n"
        f"Your request to borrow {equipment_name} (x{quantity}) was denied.\n"
        + (f"Reason: {reason}\n" if reason else "")
        + "\nIf you have questions, please contact the equipment office.\n\n"
        "- ICCT Colleges Foundation, Inc."
    )

    msg = MIMEMultipart()
    msg["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_USER}>"
    msg["To"] = email
    msg["Subject"] = "Borrow Request Denied - ICCT Equipment Borrowing System"
    msg.attach(MIMEText(body, "plain"))

    _deliver(msg, email)


def send_incident_notice(admin_emails, kind, equipment_name, quantity, borrower_name, processed_by, returned_on, notes=None):
    """Email the admins that returned equipment was Damaged or Lost (kind = 'Damage' or 'Loss')."""
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP is not configured. Please set SMTP_USER and SMTP_PASSWORD "
            "in your .env file."
        )

    body = (
        f"A {kind.lower()} report was logged for returned equipment:\n\n"
        f"  Equipment: {equipment_name} (x{quantity})\n"
        f"  Borrower: {borrower_name}\n"
        f"  Return processed by: {processed_by}\n"
        f"  Date: {returned_on}\n"
        f"  Notes: {notes or '-'}\n\n"
        "You can review it under Reports > Equipment Condition Report.\n\n"
        "- ICCT Equipment Borrowing System"
    )

    msg = MIMEMultipart()
    msg["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_USER}>"
    msg["To"] = ", ".join(admin_emails)
    msg["Subject"] = f"Equipment {kind} Report - ICCT Equipment Borrowing System"
    msg.attach(MIMEText(body, "plain"))

    _deliver(msg, list(admin_emails))
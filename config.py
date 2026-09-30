import os
from dotenv import load_dotenv

load_dotenv()


# Database settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "school_equipment_db")


# Email settings
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "iccthelpdesk.edu.ph@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "jxcveagfbnnrmnjq")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "ICCT Equipment Borrowing System")


# Verification code settings
CODE_EXPIRY_MINUTES = int(os.getenv("CODE_EXPIRY_MINUTES", "10"))
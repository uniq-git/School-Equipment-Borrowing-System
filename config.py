import os
import sys
from dotenv import load_dotenv

# folder of the .env file. beside the .exe if packaged, if not the project folder
APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(APP_DIR, ".env"))


# Database settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "school_equipment_db")


# Email settings (no default, put the real values in your .env file)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "ICCT Equipment Borrowing System")


# Verification code settings
CODE_EXPIRY_MINUTES = int(os.getenv("CODE_EXPIRY_MINUTES", "10"))
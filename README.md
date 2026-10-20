# School Equipment Borrowing System

A desktop application for managing how a school lends out its equipment. Students and teachers request items, staff and admins approve them and check them back in, and the system keeps track of stock, overdue items and reports.

Built with **Python**, **CustomTkinter** and **MySQL** (XAMPP).

---

## Features

**Borrowers (Students / Teachers)**
- Self-registration with email verification (Students) and a secure login
- Browse available equipment with photos, categories and live stock
- Submit borrow requests with a purpose and due date
- Cancel pending requests, view request history and request a return
- Limit of **2 units** held per user at a time

**Staff / Admins**
- Approve or deny requests (a denial reason is emailed to the borrower)
- Process returns, including split returns (e.g. some Good, some Damaged)
- Add, edit and remove equipment, manage categories, mark items as under repair
- Receive incident emails when equipment is returned Damaged or Lost
- Admins can create Teacher / Staff / Admin accounts, change roles and activate or deactivate users

**System**
- Automatic overdue reminder emails (checked every 30 minutes, repeated every 3 days until returned)
- Reports: Equipment Availability, Active Borrowings, Overdue, Returned Items, Borrowing History, Borrowing Report and Equipment Condition, with CSV export and print view
- Passwords hashed with bcrypt, account lockout after 5 wrong attempts (5 minutes)
- Email verification codes that expire (default 10 minutes), with attempt and resend limits
- The database and tables are created and upgraded automatically on startup

---

## ID Number Format

Every account has an ID number in the format `<prefix><9 digits>`:

| Role    | Prefix | Example       |
|---------|--------|---------------|
| Student | `CA`   | `CA202400001` |
| Teacher | `TC`   | `TC202400001` |
| Staff   | `SF`   | `SF000000001` |
| Admin   | `AD`   | `AD000000001` |

Students register themselves. Teacher, Staff and Admin accounts are created by an Admin from the **Add User** button on the Admin dashboard.

---

## Tech Stack

| Layer     | Technology                                   |
|-----------|----------------------------------------------|
| Language  | Python 3                                     |
| UI        | CustomTkinter 5.2.2, Pillow                  |
| Database  | MySQL / MariaDB (via XAMPP), mysql-connector-python |
| Security  | bcrypt                                       |
| Config    | python-dotenv                                |
| Email     | SMTP (Gmail by default)                      |

---

## Getting Started

### Prerequisites
- Python 3.10 or newer
- [XAMPP](https://www.apachefriends.org/) (for MySQL)
- An SMTP account for sending emails (for Gmail, use an [App Password](https://support.google.com/accounts/answer/185833))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/uniq-git/School-Equipment-Borrowing-System.git
   cd School-Equipment-Borrowing-System
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start MySQL** in the XAMPP Control Panel.

4. **Configure the environment**

   Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env      # Windows: copy .env.example .env
   ```

   ```env
   # Database (XAMPP MySQL)
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=
   DB_NAME=school_equipment_db

   # Email
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   SMTP_FROM_NAME=ICCT Equipment Borrowing System

   # Verification codes
   CODE_EXPIRY_MINUTES=10
   ```
   > `.env` is git-ignored. Never commit it.

5. **Create the first Admin account** (first run only)
   ```bash
   python scripts/set_admin_password.py
   ```

6. **Run the app**
   ```bash
   python main.py
   ```
   On startup the app creates the database and tables if they are missing and upgrades older databases without deleting data.

> **Optional:** `schoolequipment_db.sql` is a database dump you can import through phpMyAdmin if you prefer to start from a prepared schema.

---

## Project Structure

```
School-Equipment-Borrowing-System/
├── main.py                  # Entry point
├── config.py                # Loads settings from .env
├── database.py              # Connection, table creation and upgrades
├── requirements.txt
├── .env.example             # Template for your .env
├── schoolequipment_db.sql   # Database dump
├── assets/                  # Logo, campus image, uploaded equipment photos
├── services/                # Business logic
│   ├── auth.py              #   registration, login, passwords, user management
│   ├── borrow_service.py    #   requests, approvals, returns, overdue checks
│   ├── equipment_service.py #   equipment and categories
│   ├── email_service.py     #   verification codes and notification emails
│   └── report_service.py    #   reports, CSV export, print view
├── ui/                      # CustomTkinter screens
│   ├── login.py, register.py, forgot_password.py, change_password.py
│   ├── dashboard.py         #   borrower dashboard
│   ├── admin_dashboard.py   #   admin / staff dashboard
│   ├── borrow.py, add_equipment.py, add_user.py
│   └── helpers.py, colors.py, left_panel.py
├── scripts/
│   ├── set_admin_password.py  # Create the first Admin / reset the Admin password
│   ├── run_overdue_check.py   # One-off overdue check (for Task Scheduler / cron)
│   └── dev_login.py           # Developer shortcut login by role
└── testing/
    └── tester.py            # Unit tests (no MySQL or display needed)
```

---

## Running the Overdue Check Manually

The app checks for overdue items in the background while it is open. To run the check on a schedule instead (Windows Task Scheduler or cron):

```bash
python scripts/run_overdue_check.py
```

---

## Running the Tests

The tests stub out MySQL and SMTP, so they run anywhere:

```bash
python -m unittest testing/tester.py -v
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "The system cannot reach the database" | Make sure MySQL is running in the XAMPP Control Panel and your `DB_*` values in `.env` are correct. |
| Verification or reminder emails are not sent | Check `SMTP_USER` / `SMTP_PASSWORD`. Gmail requires an App Password, not your normal password. |
| Account locked | Wait 5 minutes after 5 wrong password attempts, or have an Admin help. |
| Equipment photos missing after cloning | Photos in `assets/equipment_photos/` are git-ignored and are not part of the repository. |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Open a pull request

---

## Author

**RicJohn** ([@uniq-git](https://github.com/uniq-git))

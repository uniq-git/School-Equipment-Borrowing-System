import mysql.connector
import config


DEFAULT_CATEGORIES = [
    "Camera",
    "Laptop",
    "Projector",
    "Audio Equipment",
    "Cables & Adapters",
    "Sports Equipment",
    "Other",
    "Tools",
]


def get_connection():
    """Connect to the database."""
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )


def init_database():
    """
    Create the database and tables if they are not there yet.
    This runs when the app starts.
    """

    # Create the database first.
    server_conn = mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )

    server_cursor = server_conn.cursor()

    server_cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS {config.DB_NAME} "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )

    server_cursor.close()
    server_conn.close()

    # Create the tables.
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            student_number VARCHAR(20) NOT NULL UNIQUE,
            email VARCHAR(150) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role ENUM('Admin', 'Student', 'Teacher', 'Staff') NOT NULL DEFAULT 'Student',
            email_verified TINYINT(1) NOT NULL DEFAULT 0,
            status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
            failed_logins INT NOT NULL DEFAULT 0,
            locked_until DATETIME NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for email verification codes.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_verifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(150) NOT NULL,
            code VARCHAR(6) NOT NULL,
            is_verified TINYINT(1) NOT NULL DEFAULT 0,
            attempts INT NOT NULL DEFAULT 0,
            expires_at DATETIME NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Store the equipment categories here.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment_categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Store all the equipment here.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            category VARCHAR(100) NOT NULL,
            quantity INT NOT NULL DEFAULT 1,
            condition_status ENUM('New', 'Good', 'Fair', 'Needs Repair') NOT NULL DEFAULT 'Good',
            photo_path VARCHAR(255),
            under_repair INT NOT NULL DEFAULT 0,
            is_deleted TINYINT(1) NOT NULL DEFAULT 0,
            added_by INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    # Store borrowing requests here. A single row represents the request,
    # and once it is Approved it also serves as the active borrowing
    # transaction (borrower, equipment, dates, who approved it, status).
    # When the equipment comes back the same row becomes 'Returned' and the
    # return details (date, who processed it, quantity, condition, notes)
    # are saved in the returned_* / return_* columns. The row is never deleted.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrow_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            equipment_id INT NOT NULL,
            quantity INT NOT NULL DEFAULT 1,
            status ENUM('Pending', 'Approved', 'Denied', 'Returned', 'Cancelled') NOT NULL DEFAULT 'Pending',
            request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            due_date DATE,
            approved_by INT,
            approved_at DATETIME,
            returned_at DATETIME NULL,
            returned_by INT NULL,
            returned_quantity INT NULL,
            return_condition ENUM('New', 'Good', 'Fair', 'Needs Repair', 'Damaged', 'Lost') NULL,
            return_notes VARCHAR(255) NULL,
            overdue_reminder_sent_at DATETIME NULL,
            purpose VARCHAR(255) NULL,
            deny_reason VARCHAR(255) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
            FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (returned_by) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    # Add the default categories if they are not there yet.
    for name in DEFAULT_CATEGORIES:
        cursor.execute(
            "INSERT IGNORE INTO equipment_categories (name) VALUES (%s)",
            (name,)
        )

    # No default admin account is created here (a built-in password would be public).
    # Run "python set_admin_password.py" once to create or reset the admin.

    conn.commit()
    cursor.close()
    conn.close()

    # Make sure an older database also gets the newer columns.
    upgrade_database()


# Columns added for Return Transactions: (column name, definition).
RETURN_COLUMNS = [
    ("returned_at", "DATETIME NULL"),
    ("returned_by", "INT NULL"),
    ("returned_quantity", "INT NULL"),
    ("return_condition", "ENUM('New', 'Good', 'Fair', 'Needs Repair', 'Damaged', 'Lost') NULL"),
    ("return_notes", "VARCHAR(255) NULL"),
    # When the last overdue reminder email was sent (it is repeated every few days).
    ("overdue_reminder_sent_at", "DATETIME NULL"),
    # Why the equipment is needed, and why a request was denied.
    ("purpose", "VARCHAR(255) NULL"),
    ("deny_reason", "VARCHAR(255) NULL"),
]


def upgrade_database():
    """
    Upgrade an existing database:
      - email_verifications: add the wrong-attempts counter.
      - borrow_requests: add what is needed to support returns.
    Safe to run many times: it only changes what is still missing and
    it never deletes or rewrites existing users or borrowing records.
    """
    conn = get_connection()
    cursor = conn.cursor()

    def add_missing_columns(table, columns):
        cursor.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (config.DB_NAME, table),
        )
        found = [row[0] for row in cursor.fetchall()]
        for name, definition in columns:
            if found and name not in found:  # (existing rows get the default / NULL)
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        conn.commit()

    add_missing_columns("users", [
        ("failed_logins", "INT NOT NULL DEFAULT 0"),
        ("locked_until", "DATETIME NULL"),
        # 1 = account made by an admin with a temporary password; cleared when the user changes it.
        ("must_change_password", "TINYINT(1) NOT NULL DEFAULT 0"),
    ])
    add_missing_columns("email_verifications", [("attempts", "INT NOT NULL DEFAULT 0")])
    # under_repair: units out of service after a damaged return.
    # is_deleted: equipment is hidden instead of erased so borrowing history is kept.
    add_missing_columns("equipment", [
        ("under_repair", "INT NOT NULL DEFAULT 0"),
        ("is_deleted", "TINYINT(1) NOT NULL DEFAULT 0"),
    ])

    cursor.execute(
        "SELECT COLUMN_NAME, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'borrow_requests'",
        (config.DB_NAME,),
    )
    existing = {}
    for name, column_type in cursor.fetchall():
        if isinstance(column_type, (bytes, bytearray)):
            column_type = column_type.decode()
        existing[name] = column_type

    # The table does not exist yet, so there is nothing to upgrade.
    if not existing:
        cursor.close()
        conn.close()
        return

    # 1. Allow the 'Returned' and 'Cancelled' statuses.
    if "Returned" not in existing.get("status", "") or "Cancelled" not in existing.get("status", ""):
        cursor.execute(
            "ALTER TABLE borrow_requests MODIFY status "
            "ENUM('Pending', 'Approved', 'Denied', 'Returned', 'Cancelled') "
            "NOT NULL DEFAULT 'Pending'"
        )

    # 2. Add the return columns that are missing.
    for name, definition in RETURN_COLUMNS:
        if name not in existing:
            cursor.execute(f"ALTER TABLE borrow_requests ADD COLUMN {name} {definition}")

            if name == "returned_by":
                cursor.execute(
                    "ALTER TABLE borrow_requests ADD FOREIGN KEY (returned_by) "
                    "REFERENCES users(id) ON DELETE SET NULL"
                )

    # 3. Allow the Damaged / Lost return conditions (older records keep their value).
    if "Damaged" not in existing.get("return_condition", ""):
        cursor.execute(
            "ALTER TABLE borrow_requests MODIFY return_condition "
            "ENUM('New', 'Good', 'Fair', 'Needs Repair', 'Damaged', 'Lost') NULL"
        )

    conn.commit()
    cursor.close()
    conn.close()
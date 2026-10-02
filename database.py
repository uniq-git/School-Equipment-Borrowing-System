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
            status ENUM('Pending', 'Approved', 'Denied', 'Returned') NOT NULL DEFAULT 'Pending',
            request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            due_date DATE,
            approved_by INT,
            approved_at DATETIME,
            returned_at DATETIME NULL,
            returned_by INT NULL,
            returned_quantity INT NULL,
            return_condition ENUM('New', 'Good', 'Fair', 'Needs Repair') NULL,
            return_notes VARCHAR(255) NULL,
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

    # Add the default admin account.
    cursor.execute(
        "INSERT IGNORE INTO users "
        "(full_name, student_number, email, password, role, email_verified, status) "
        "VALUES (%s, %s, %s, %s, %s, 1, 'active')",
        (
            "System Administrator",
            "AD000000001",
            "admin@icct.edu.ph",
            "$2b$12$0/gqGsKbQMjHC7YA/40t5eQCHJar3QM/CWs6Lwa60lYGd9tS/Lqpy",
            "Admin",
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()

    # Make sure an older database also gets the return columns.
    upgrade_database()


# Columns added for Return Transactions: (column name, definition).
RETURN_COLUMNS = [
    ("returned_at", "DATETIME NULL"),
    ("returned_by", "INT NULL"),
    ("returned_quantity", "INT NULL"),
    ("return_condition", "ENUM('New', 'Good', 'Fair', 'Needs Repair') NULL"),
    ("return_notes", "VARCHAR(255) NULL"),
]


def upgrade_database():
    """
    Upgrade an existing borrow_requests table so it supports returns.
    Safe to run many times: it only changes what is still missing and
    it never deletes or rewrites existing borrowing records.
    """
    conn = get_connection()
    cursor = conn.cursor()

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

    # 1. Allow the new 'Returned' status.
    if "Returned" not in existing.get("status", ""):
        cursor.execute(
            "ALTER TABLE borrow_requests MODIFY status "
            "ENUM('Pending', 'Approved', 'Denied', 'Returned') "
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

    conn.commit()
    cursor.close()
    conn.close()
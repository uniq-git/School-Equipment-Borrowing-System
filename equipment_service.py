import os
import shutil
import uuid
from database import get_connection

CONDITION_OPTIONS = ["New", "Good", "Fair", "Needs Repair"]

# Equipment Type options shown in the second dropdown, based on which
# Category is selected in the first dropdown. This is just a predefined
# dictionary (no extra database table needed) since the list of types
# per category is fixed and doesn't need to be managed dynamically.
EQUIPMENT_TYPES = {
    "Camera": [
        "DSLR Camera", "Mirrorless Camera", "Digital Camera",
        "Action Camera", "Camcorder",
    ],
    "Laptop": [
        "Gaming Laptop", "Business Laptop", "Chromebook",
        "Ultrabook", "2-in-1 Laptop",
    ],
    "Projector": [
        "LCD Projector", "DLP Projector", "Portable Projector", "Smart Projector",
    ],
    "Audio Equipment": [
        "Speaker", "Microphone", "Amplifier", "Mixer", "Headset",
    ],
    "Cables & Adapters": [
        "HDMI Cable", "VGA Cable", "USB Cable", "Power Adapter", "Extension Cord",
    ],
    "Sports Equipment": [
        "Basketball", "Volleyball", "Badminton Racket",
        "Table Tennis Paddle", "Whistle",
    ],
    "Tools": [
        "Screwdriver Set", "Hammer", "Measuring Tape", "Multimeter", "Soldering Iron",
    ],
    "Other": [
        "Miscellaneous Item",
    ],
}

# Used when a category doesn't have a predefined type list yet
# (e.g. a brand-new category added through "+ New").
DEFAULT_EQUIPMENT_TYPES = ["General Item"]


def get_equipment_types(category):
    """Get the list of equipment types for the given category."""
    return EQUIPMENT_TYPES.get(category, DEFAULT_EQUIPMENT_TYPES)

PHOTOS_DIR = os.path.join(
    os.path.dirname(__file__),
    "assets",
    "equipment_photos"
)


def get_categories():
    """Get all categories from the database."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM equipment_categories ORDER BY name ASC"
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows


def get_category_names():
    """Get the category names."""
    return [c["name"] for c in get_categories()]


def add_category(name):
    """Add a new category."""
    name = name.strip()

    if not name:
        return False, "Category name is required."

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM equipment_categories WHERE name = %s",
        (name,)
    )

    if cursor.fetchone():
        cursor.close()
        conn.close()
        return False, "This category already exists."

    cursor.execute(
        "INSERT INTO equipment_categories (name) VALUES (%s)",
        (name,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, f"Category '{name}' added."


def delete_category(category_id):
    """Delete a category."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM equipment_categories WHERE id = %s",
        (category_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()


def _store_photo(source_path):
    """Save the selected photo in the equipment photos folder."""
    if not source_path:
        return None

    os.makedirs(PHOTOS_DIR, exist_ok=True)

    ext = os.path.splitext(source_path)[1].lower() or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    destination = os.path.join(PHOTOS_DIR, filename)

    shutil.copy2(source_path, destination)

    return filename


def get_photo_full_path(photo_filename):
    """Get the full path of the photo."""
    if not photo_filename:
        return None

    full_path = os.path.join(PHOTOS_DIR, photo_filename)

    if os.path.exists(full_path):
        return full_path

    return None


def add_equipment(name,category,quantity,condition,photo_source_path,added_by_user_id):
    """
    Add new equipment.
    Check the details first before saving it.
    """
    name = name.strip()
    category = category.strip()

    if not name:
        return False, "Equipment name is required."

    if category not in get_category_names():
        return False, "Please select a valid category."

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return False, "Quantity must be a whole number."

    if quantity < 1:
        return False, "Quantity must be at least 1."

    if condition not in CONDITION_OPTIONS:
        return False, "Please select a valid condition."

    try:
        photo_filename = _store_photo(photo_source_path)
    except OSError as exc:
        return False, f"Could not save the photo: {exc}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO equipment "
        "(name, category, quantity, condition_status, photo_path, added_by) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (name,category,quantity,condition,photo_filename,added_by_user_id),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, f"'{name}' has been added to the equipment list."


def get_all_equipment():
    """Get all equipment from the database."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT equipment.*, users.full_name AS added_by_name
        FROM equipment
        LEFT JOIN users ON users.id = equipment.added_by
        ORDER BY equipment.created_at DESC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows


def delete_equipment(equipment_id):
    """Delete an equipment item."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM equipment WHERE id = %s",
        (equipment_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()


def get_condition_summary():
    """
    How much equipment is in each condition, for the Reports screen.
    Returns a list of (condition, number of items, number of units),
    always in the order New, Good, Fair, Needs Repair.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT condition_status, COUNT(*) AS items, COALESCE(SUM(quantity), 0) AS units "
        "FROM equipment GROUP BY condition_status"
    )
    found = {row["condition_status"]: row for row in cursor.fetchall()}

    cursor.close()
    conn.close()

    summary = []
    for condition in CONDITION_OPTIONS:
        row = found.get(condition)
        summary.append((
            condition,
            int(row["items"]) if row else 0,
            int(row["units"]) if row else 0,
        ))

    return summary
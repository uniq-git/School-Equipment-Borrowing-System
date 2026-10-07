import os
import shutil
import uuid
from database import get_connection

CONDITION_OPTIONS = ["New", "Good", "Fair", "Needs Repair"]

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTOS_DIR = os.path.join(ROOT_DIR, "assets", "equipment_photos")
# Older versions saved photos inside services/assets; they are still found there.
LEGACY_PHOTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "equipment_photos")


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
    """Delete a category. Not allowed while equipment still uses it."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM equipment e "
        "JOIN equipment_categories c ON c.name = e.category "
        "WHERE c.id = %s AND e.is_deleted = 0",
        (category_id,)
    )
    in_use = cursor.fetchone()[0]

    if in_use:
        cursor.close()
        conn.close()
        return False, f"Cannot Delete \u2014 {in_use} equipment item(s) still use this category."

    cursor.execute(
        "DELETE FROM equipment_categories WHERE id = %s",
        (category_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, "Category deleted."


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

    for folder in (PHOTOS_DIR, LEGACY_PHOTOS_DIR):
        full_path = os.path.join(folder, photo_filename)

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


def update_equipment(equipment_id, name, category, quantity, condition, photo_source_path=None, under_repair=None):
    """
    Edit an existing equipment item.
    Same checks as adding. A new photo is only saved if one was chosen;
    otherwise the current photo is kept.
    """
    name = name.strip()
    category = category.strip()

    if not name:
        return False, "Equipment name is required."

    if not category:
        return False, "Please select a valid category."

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return False, "Quantity must be a whole number."

    if quantity < 1:
        return False, "Quantity must be at least 1."

    if condition not in CONDITION_OPTIONS:
        return False, "Please select a valid condition."

    # Units under repair (optional): None keeps the current value.
    if under_repair is not None and str(under_repair).strip() != "":
        try:
            under_repair = int(under_repair)
        except (TypeError, ValueError):
            return False, "Units under repair must be a whole number."

        if under_repair < 0 or under_repair > quantity:
            return False, "Units under repair must be between 0 and the total quantity."
    else:
        under_repair = None

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT photo_path, under_repair FROM equipment WHERE id = %s",
        (equipment_id,)
    )

    current = cursor.fetchone()

    if not current:
        cursor.close()
        conn.close()
        return False, "This equipment no longer exists."

    cursor.execute(
        "SELECT category FROM equipment WHERE id = %s", (equipment_id,)
    )
    current_category = cursor.fetchone()["category"]

    if category != current_category and category not in get_category_names():
        cursor.close()
        conn.close()
        return False, "Please select a valid category."

    # Units that are out on an approved borrowing must stay inside the total quantity.
    cursor.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS borrowed FROM borrow_requests "
        "WHERE equipment_id = %s AND status = 'Approved'",
        (equipment_id,)
    )
    borrowed = int(cursor.fetchone()["borrowed"])

    if quantity < borrowed:
        cursor.close()
        conn.close()
        return False, f"Quantity cannot be lower than the {borrowed} unit(s) currently borrowed."

    photo_filename = current["photo_path"]
    old_photo = None

    if photo_source_path:
        try:
            new_filename = _store_photo(photo_source_path)
        except OSError as exc:
            cursor.close()
            conn.close()
            return False, f"Could not save the photo: {exc}"

        old_photo = photo_filename
        photo_filename = new_filename

    if under_repair is None:
        under_repair = min(current["under_repair"] or 0, quantity)

    cursor.execute(
        "UPDATE equipment "
        "SET name = %s, category = %s, quantity = %s, "
        "condition_status = %s, photo_path = %s, under_repair = %s "
        "WHERE id = %s",
        (name, category, quantity, condition, photo_filename, under_repair, equipment_id),
    )

    conn.commit()
    cursor.close()
    conn.close()

    # Remove the replaced photo file (if any) once the update is saved.
    if old_photo:
        old_path = get_photo_full_path(old_photo)
        if old_path:
            try:
                os.remove(old_path)
            except OSError:
                pass

    return True, f"'{name}' has been updated."


def get_all_equipment(include_deleted=False):
    """Get the equipment list. Removed items are left out unless include_deleted is True."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    where = "" if include_deleted else "WHERE equipment.is_deleted = 0"

    cursor.execute(f"""
        SELECT equipment.*, users.full_name AS added_by_name
        FROM equipment
        LEFT JOIN users ON users.id = equipment.added_by
        {where}
        ORDER BY equipment.created_at DESC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows


def is_currently_borrowed(equipment_id):
    """True if any unit of this equipment is out on an approved (active) borrowing."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM borrow_requests "
        "WHERE equipment_id = %s AND status = 'Approved'",
        (equipment_id,)
    )

    borrowed = cursor.fetchone()[0] > 0

    cursor.close()
    conn.close()

    return borrowed


def delete_equipment(equipment_id):
    """
    Remove an equipment item.
    Not allowed while the equipment is currently borrowed.
    An item with borrowing records is only hidden (is_deleted) so its history
    and reports are kept; an item that was never borrowed is erased.
    """
    if is_currently_borrowed(equipment_id):
        return False, "Cannot Delete \u2014 Currently Borrowed"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM borrow_requests "
        "WHERE equipment_id = %s AND status IN ('Approved', 'Returned')",
        (equipment_id,)
    )
    has_history = cursor.fetchone()[0] > 0

    if has_history:
        # Waiting requests can no longer be fulfilled.
        cursor.execute(
            "UPDATE borrow_requests SET status = 'Denied' "
            "WHERE equipment_id = %s AND status = 'Pending'",
            (equipment_id,)
        )
        cursor.execute(
            "UPDATE equipment SET is_deleted = 1 WHERE id = %s",
            (equipment_id,)
        )
        message = "Equipment has been removed. Its borrowing history was kept."
    else:
        cursor.execute(
            "DELETE FROM equipment WHERE id = %s",
            (equipment_id,)
        )
        message = "Equipment has been removed."

    conn.commit()
    cursor.close()
    conn.close()

    return True, message
"""
Borrowing Transactions service layer.

Workflow: Request -> Approval -> Borrowing Transaction

A single table (borrow_requests) is used for both the request and, once
Approved, the active borrowing transaction - there's no separate table
for transactions. Return handling is a separate feature to be added later,
so an Approved row is treated as "currently borrowed" for availability
purposes until that feature exists.
"""
from datetime import datetime, date

from database import get_connection

STATUS_OPTIONS = ["Pending", "Approved", "Denied"]

DATE_FORMAT = "%Y-%m-%d"


def _parse_due_date(due_date_str):
    """Turn a 'YYYY-MM-DD' string into a date object, or raise ValueError."""
    return datetime.strptime(due_date_str.strip(), DATE_FORMAT).date()


def get_available_quantity(equipment_id, exclude_request_id=None):
    """
    How many units of this equipment are free to be approved right now.
    Total quantity minus whatever is currently out on Approved requests.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT quantity FROM equipment WHERE id = %s",
        (equipment_id,)
    )
    equipment = cursor.fetchone()

    if not equipment:
        cursor.close()
        conn.close()
        return 0

    query = (
        "SELECT COALESCE(SUM(quantity), 0) AS borrowed FROM borrow_requests "
        "WHERE equipment_id = %s AND status = 'Approved'"
    )
    params = [equipment_id]

    if exclude_request_id is not None:
        query += " AND id != %s"
        params.append(exclude_request_id)

    cursor.execute(query, tuple(params))
    borrowed = cursor.fetchone()["borrowed"]

    cursor.close()
    conn.close()

    return equipment["quantity"] - borrowed


def create_request(user_id, equipment_id, quantity, due_date_str):
    """
    Submit a new borrow request. Starts as Pending.
    The borrower proposes a due date here; Admin/Staff can override it
    when they approve the request.
    """
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return False, "Quantity must be a whole number."

    if quantity < 1:
        return False, "Quantity must be at least 1."

    if not due_date_str or not due_date_str.strip():
        return False, "Please provide a due date."

    try:
        due_date = _parse_due_date(due_date_str)
    except ValueError:
        return False, "Due date must be in YYYY-MM-DD format."

    if due_date <= date.today():
        return False, "Due date must be after today."

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM equipment WHERE id = %s",
        (equipment_id,)
    )
    equipment = cursor.fetchone()

    if not equipment:
        cursor.close()
        conn.close()
        return False, "This equipment no longer exists."

    cursor.close()
    conn.close()

    available = get_available_quantity(equipment_id)

    if quantity > available:
        return False, (
            f"Only {available} unit(s) of '{equipment['name']}' "
            "are currently available."
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO borrow_requests "
        "(user_id, equipment_id, quantity, status, due_date) "
        "VALUES (%s, %s, %s, 'Pending', %s)",
        (user_id, equipment_id, quantity, due_date),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return True, f"Request to borrow '{equipment['name']}' has been submitted."


def _select_with_joins(where_clause, params=()):
    """Shared SELECT for borrow_requests joined with borrower/equipment/approver names."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(f"""
        SELECT
            br.*,
            borrower.full_name AS borrower_name,
            borrower.role AS borrower_role,
            eq.name AS equipment_name,
            eq.category AS equipment_category,
            approver.full_name AS approved_by_name
        FROM borrow_requests br
        JOIN users borrower ON borrower.id = br.user_id
        JOIN equipment eq ON eq.id = br.equipment_id
        LEFT JOIN users approver ON approver.id = br.approved_by
        {where_clause}
        ORDER BY br.created_at DESC
    """, params)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows


def get_pending_requests():
    """All requests waiting for Admin/Staff review."""
    return _select_with_joins("WHERE br.status = 'Pending'")


def get_active_transactions():
    """All Approved requests - these are the active borrowing transactions."""
    return _select_with_joins("WHERE br.status = 'Approved'")


def get_requests_for_user(user_id):
    """A borrower's own request history (Pending, Approved, and Denied)."""
    return _select_with_joins("WHERE br.user_id = %s", (user_id,))


def get_request_by_id(request_id):
    rows = _select_with_joins("WHERE br.id = %s", (request_id,))
    return rows[0] if rows else None


def approve_request(request_id, approved_by_user_id, due_date_str=None):
    """
    Approve a Pending request, turning it into an active borrowing
    transaction. Equipment availability is re-checked here since other
    requests may have been approved since this one was submitted.
    An optional due_date_str lets Admin/Staff override the borrower's
    proposed due date.
    """
    request = get_request_by_id(request_id)

    if not request:
        return False, "Request not found."

    if request["status"] != "Pending":
        return False, f"This request has already been {request['status'].lower()}."

    due_date = request["due_date"]

    if due_date_str and due_date_str.strip():
        try:
            due_date = _parse_due_date(due_date_str)
        except ValueError:
            return False, "Due date must be in YYYY-MM-DD format."

        if due_date <= date.today():
            return False, "Due date must be after today."

    available = get_available_quantity(request["equipment_id"], exclude_request_id=request_id)

    if request["quantity"] > available:
        return False, (
            f"Cannot approve: only {available} unit(s) of "
            f"'{request['equipment_name']}' are currently available."
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE borrow_requests SET "
        "status = 'Approved', approved_by = %s, approved_at = NOW(), due_date = %s "
        "WHERE id = %s AND status = 'Pending'",
        (approved_by_user_id, due_date, request_id),
    )

    updated = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if updated == 0:
        return False, "This request has already been reviewed."

    return True, f"Request approved. '{request['equipment_name']}' is now borrowed."


def deny_request(request_id, approved_by_user_id):
    """Deny a Pending request."""
    request = get_request_by_id(request_id)

    if not request:
        return False, "Request not found."

    if request["status"] != "Pending":
        return False, f"This request has already been {request['status'].lower()}."

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE borrow_requests SET "
        "status = 'Denied', approved_by = %s, approved_at = NOW() "
        "WHERE id = %s AND status = 'Pending'",
        (approved_by_user_id, request_id),
    )

    updated = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if updated == 0:
        return False, "This request has already been reviewed."

    return True, "Request has been denied."
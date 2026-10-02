"""
Borrowing Transactions service layer.

Workflow: Request -> Pending -> Approved (Active) -> Returned

A single table (borrow_requests) is used for the request, the active
borrowing transaction and the return - there's no separate table for
transactions. The row's status tells where it is:

    Pending   - waiting for Admin/Staff
    Approved  - the equipment is currently borrowed (Active)
    Denied    - request was rejected
    Returned  - equipment came back; the row stays for history/reports

Only Approved rows count as "currently borrowed", so the moment a row
becomes Returned its quantity is available again.

Due-date states (Active / Due Soon / Due Today / Overdue) are NOT saved
in the database. They are worked out from today's date and the due date
every time (see get_borrow_state), so they can never go out of date.
"""
from datetime import datetime, date

from database import get_connection

STATUS_OPTIONS = ["Pending", "Approved", "Denied", "Returned"]

DATE_FORMAT = "%Y-%m-%d"

# An active borrowing is "Due Soon" when it is due within this many days.
DUE_SOON_DAYS = 3

# Only these roles may process a return.
RETURN_ROLES = ("Admin", "Staff")

# Same list as equipment_service.CONDITION_OPTIONS.
CONDITION_OPTIONS = ["New", "Good", "Fair", "Needs Repair"]


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

    # Never return a negative number, even if the data is out of sync.
    return max(0, equipment["quantity"] - int(borrowed))


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


def get_borrow_state(row, today=None):
    """
    The status shown to users, worked out from the row and today's date.

    Pending / Denied / Returned are shown as they are. An Approved row is
    an active borrowing, so it becomes one of:
        Overdue    - due date has passed
        Due Today  - due date is today
        Due Soon   - due within DUE_SOON_DAYS days
        Active     - anything later

    A Returned row always stays "Returned", so it is never overdue.
    """
    if row["status"] != "Approved":
        return row["status"]

    due_date = row["due_date"]
    if due_date is None:
        return "Active"
    if isinstance(due_date, datetime):
        due_date = due_date.date()

    today = today or date.today()
    days_left = (due_date - today).days

    if days_left < 0:
        return "Overdue"
    if days_left == 0:
        return "Due Today"
    if days_left <= DUE_SOON_DAYS:
        return "Due Soon"
    return "Active"


def get_days_overdue(row, today=None):
    """How many days past the due date (0 if it is not overdue)."""
    today = today or date.today()

    if get_borrow_state(row, today) != "Overdue":
        return 0

    due_date = row["due_date"]
    if isinstance(due_date, datetime):
        due_date = due_date.date()

    return (today - due_date).days


def _select_with_joins(where_clause, params=(), order_by="br.created_at DESC"):
    """
    Shared SELECT for borrow_requests joined with borrower/equipment/approver names.
    Every row also gets two extra keys: "state" (Active / Due Soon / Due Today /
    Overdue / Returned ...) and "days_overdue".
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(f"""
        SELECT
            br.*,
            borrower.full_name AS borrower_name,
            borrower.role AS borrower_role,
            eq.name AS equipment_name,
            eq.category AS equipment_category,
            eq.condition_status AS equipment_condition,
            approver.full_name AS approved_by_name,
            returner.full_name AS returned_by_name
        FROM borrow_requests br
        JOIN users borrower ON borrower.id = br.user_id
        JOIN equipment eq ON eq.id = br.equipment_id
        LEFT JOIN users approver ON approver.id = br.approved_by
        LEFT JOIN users returner ON returner.id = br.returned_by
        {where_clause}
        ORDER BY {order_by}
    """, params)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    today = date.today()
    for row in rows:
        row["state"] = get_borrow_state(row, today)
        row["days_overdue"] = get_days_overdue(row, today)

    return rows


def get_pending_requests():
    """All requests waiting for Admin/Staff review."""
    return _select_with_joins("WHERE br.status = 'Pending'")


def get_active_transactions():
    """
    All Approved requests - these are the active borrowing transactions.
    Returned transactions are NOT included. Earliest due date comes first.
    """
    return _select_with_joins("WHERE br.status = 'Approved'", order_by="br.due_date ASC")


def get_overdue_transactions():
    """
    Active borrowings that are past their due date.
    Overdue = today is after the due date AND it has not been returned
    (status is still Approved), so Returned rows can never appear here.
    """
    return _select_with_joins(
        "WHERE br.status = 'Approved' AND br.due_date < %s",
        (date.today(),),
        order_by="br.due_date ASC",
    )


def parse_date_range(from_str, to_str):
    """
    Turn two optional 'YYYY-MM-DD' strings into (date_from, date_to).
    A blank box means no limit (None). Raises ValueError with a message
    that can be shown to the user.
    """
    date_from = date_to = None

    if from_str and from_str.strip():
        try:
            date_from = _parse_due_date(from_str)
        except ValueError:
            raise ValueError("'From' date must be in YYYY-MM-DD format.")

    if to_str and to_str.strip():
        try:
            date_to = _parse_due_date(to_str)
        except ValueError:
            raise ValueError("'To' date must be in YYYY-MM-DD format.")

    if date_from and date_to and date_from > date_to:
        raise ValueError("'From' date must not be after the 'To' date.")

    return date_from, date_to


def get_borrow_history(date_from=None, date_to=None, returned_only=False):
    """
    Borrowing history: every transaction that was approved, whether it is
    still out (Active/Overdue...) or already Returned. Newest first.
    Pending and Denied requests are not borrowings, so they are not here
    (borrowers still see them under My Requests).
    The optional dates filter by borrow date (the day it was approved).
    """
    if returned_only:
        where = "WHERE br.status = 'Returned'"
    else:
        where = "WHERE br.status IN ('Approved', 'Returned')"
    params = []

    if date_from:
        where += " AND DATE(br.approved_at) >= %s"
        params.append(date_from)
    if date_to:
        where += " AND DATE(br.approved_at) <= %s"
        params.append(date_to)

    return _select_with_joins(where, tuple(params), order_by="br.approved_at DESC")


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


def process_return(request_id, processed_by_user_id, return_condition, notes=""):
    """
    Process the return of an active (Approved) borrowing.

    What happens:
      1. The row becomes 'Returned' and stores the return date, who processed
         it, the returned quantity, the condition and optional notes.
      2. The equipment's condition is updated to the condition at return.
      3. The row is NOT deleted - it stays for history and reports.

    Available quantity goes back up by itself: availability only counts
    'Approved' rows, and this row is no longer Approved.

    The whole return is saved together (one commit), so it can't be
    half-done. The whole borrowed quantity is returned at once.
    """
    if return_condition not in CONDITION_OPTIONS:
        return False, "Please select the condition of the returned equipment."

    notes = (notes or "").strip()
    if len(notes) > 255:
        return False, "Return notes must be 255 characters or less."

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT role, status FROM users WHERE id = %s",
        (processed_by_user_id,)
    )
    processor = cursor.fetchone()
    cursor.close()
    conn.close()

    if not processor or processor["role"] not in RETURN_ROLES or processor["status"] != "active":
        return False, "Only an Admin or Staff account can process returns."

    request = get_request_by_id(request_id)

    if not request:
        return False, "Transaction not found."

    if request["status"] == "Returned":
        return False, "This equipment has already been returned."

    if request["status"] != "Approved":
        return False, "Only active borrowings can be returned."

    conn = get_connection()
    cursor = conn.cursor()

    # "AND status = 'Approved'" stops the same borrowing from being returned twice.
    cursor.execute(
        "UPDATE borrow_requests SET "
        "status = 'Returned', returned_at = NOW(), returned_by = %s, "
        "returned_quantity = quantity, return_condition = %s, return_notes = %s "
        "WHERE id = %s AND status = 'Approved'",
        (processed_by_user_id, return_condition, notes or None, request_id),
    )

    if cursor.rowcount == 0:
        conn.rollback()
        cursor.close()
        conn.close()
        return False, "This borrowing was already returned or is no longer active."

    # Keep the equipment's condition in sync with what was just recorded.
    cursor.execute(
        "UPDATE equipment SET condition_status = %s WHERE id = %s",
        (return_condition, request["equipment_id"]),
    )

    conn.commit()
    cursor.close()
    conn.close()

    message = f"'{request['equipment_name']}' has been returned (condition: {return_condition})."
    if request["days_overdue"] > 0:
        message += f" It was returned {request['days_overdue']} day(s) late."

    return True, message


def get_report_summary(date_from=None, date_to=None):
    """
    Numbers for the Reports screen, taken straight from the database.

    Total / Available / Borrowed / Overdue are the situation right now.
    Returned counts the transactions returned inside the date range
    (all of them if no dates are given).
    """
    import equipment_service

    today = date.today()
    items = equipment_service.get_all_equipment()

    # Available uses the same function as the rest of the system.
    available_units = sum(get_available_quantity(item["id"]) for item in items)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT COUNT(*) AS transactions, COALESCE(SUM(quantity), 0) AS units "
        "FROM borrow_requests WHERE status = 'Approved'"
    )
    borrowed = cursor.fetchone()

    cursor.execute(
        "SELECT COUNT(*) AS transactions, COALESCE(SUM(quantity), 0) AS units "
        "FROM borrow_requests WHERE status = 'Approved' AND due_date < %s",
        (today,),
    )
    overdue = cursor.fetchone()

    returned_query = (
        "SELECT COUNT(*) AS transactions, COALESCE(SUM(returned_quantity), 0) AS units "
        "FROM borrow_requests WHERE status = 'Returned'"
    )
    returned_params = []
    if date_from:
        returned_query += " AND DATE(returned_at) >= %s"
        returned_params.append(date_from)
    if date_to:
        returned_query += " AND DATE(returned_at) <= %s"
        returned_params.append(date_to)
    cursor.execute(returned_query, tuple(returned_params))
    returned = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "total_items": len(items),
        "total_units": sum(item["quantity"] for item in items),
        "available_units": available_units,
        "borrowed_units": int(borrowed["units"]),
        "borrowed_transactions": int(borrowed["transactions"]),
        "overdue_units": int(overdue["units"]),
        "overdue_transactions": int(overdue["transactions"]),
        "returned_units": int(returned["units"]),
        "returned_transactions": int(returned["transactions"]),
    }
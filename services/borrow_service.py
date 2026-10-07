import threading
import time
from datetime import datetime, date
from database import get_connection

STATUS_OPTIONS = ["Pending", "Approved", "Denied", "Returned", "Cancelled"]
REMINDER_REPEAT_DAYS = 3  # an overdue borrower is reminded again after this many days
DATE_FORMAT = "%Y-%m-%d"
RETURN_ROLES = ("Admin", "Staff")
CONDITION_OPTIONS = ["New", "Good", "Fair", "Needs Repair"]
RETURN_CONDITIONS = ["Good", "Damaged", "Lost"]  # what the borrower brings back


def _parse_due_date(due_date_str):
    return datetime.strptime(due_date_str.strip(), DATE_FORMAT).date()


def get_available_quantity(equipment_id, exclude_request_id=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT quantity, under_repair FROM equipment WHERE id = %s", (equipment_id,))
    equipment = cursor.fetchone()

    if not equipment:
        cursor.close()
        conn.close()
        return 0

    query = "SELECT COALESCE(SUM(quantity), 0) AS borrowed FROM borrow_requests WHERE equipment_id = %s AND status = 'Approved'"
    params = [equipment_id]

    if exclude_request_id is not None:
        query += " AND id != %s"
        params.append(exclude_request_id)

    cursor.execute(query, tuple(params))
    borrowed = cursor.fetchone()["borrowed"]
    cursor.close()
    conn.close()

    # Units under repair (damaged returns) are not available to borrow.
    return max(0, equipment["quantity"] - int(equipment["under_repair"] or 0) - int(borrowed))


def create_request(user_id, equipment_id, quantity, due_date_str, purpose=None):
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

    purpose = (purpose or "").strip()

    if len(purpose) > 255:
        return False, "Purpose must be 255 characters or fewer."

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM equipment WHERE id = %s", (equipment_id,))
    equipment = cursor.fetchone()
    cursor.close()
    conn.close()

    if not equipment or equipment.get("is_deleted"):
        return False, "This equipment no longer exists."

    available = get_available_quantity(equipment_id)

    if quantity > available:
        return False, f"Only {available} units of '{equipment['name']}' are currently available."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO borrow_requests (user_id, equipment_id, quantity, status, due_date, purpose) "
        "VALUES (%s, %s, %s, 'Pending', %s, %s)",
        (user_id, equipment_id, quantity, due_date, purpose or None)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return True, f"Request to borrow '{equipment['name']}' has been submitted."


def get_borrow_state(row, today=None):
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

    return "Active"


def get_days_overdue(row, today=None):
    today = today or date.today()

    if get_borrow_state(row, today) != "Overdue":
        return 0

    due_date = row["due_date"]

    if isinstance(due_date, datetime):
        due_date = due_date.date()

    return (today - due_date).days


def _select_with_joins(where_clause, params=(), order_by="br.created_at DESC"):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        f"""
        SELECT br.*, borrower.full_name AS borrower_name,
               borrower.email AS borrower_email,
               borrower.role AS borrower_role,
               eq.name AS equipment_name,
               eq.category AS equipment_category,
               eq.condition_status AS equipment_condition,
               eq.is_deleted AS equipment_deleted,
               approver.full_name AS approved_by_name,
               returner.full_name AS returned_by_name
        FROM borrow_requests br
        JOIN users borrower ON borrower.id = br.user_id
        JOIN equipment eq ON eq.id = br.equipment_id
        LEFT JOIN users approver ON approver.id = br.approved_by
        LEFT JOIN users returner ON returner.id = br.returned_by
        {where_clause}
        ORDER BY {order_by}
        """,
        params
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    today = date.today()

    for row in rows:
        row["state"] = get_borrow_state(row, today)
        row["days_overdue"] = get_days_overdue(row, today)

    return rows


def get_borrower_history(user_id, returned_only=False):
    statuses = "('Returned')" if returned_only else "('Approved', 'Returned')"

    return _select_with_joins(
        f"WHERE br.user_id = %s AND br.status IN {statuses}",
        (user_id,),
        order_by="br.returned_at DESC, br.approved_at DESC" if returned_only else "br.approved_at DESC"
    )


def get_pending_requests():
    return _select_with_joins("WHERE br.status = 'Pending'")


def get_active_transactions():
    return _select_with_joins(
        "WHERE br.status = 'Approved'",
        order_by="br.due_date ASC"
    )


def get_overdue_transactions():
    return _select_with_joins(
        "WHERE br.status = 'Approved' AND br.due_date < %s",
        (date.today(),),
        order_by="br.due_date ASC"
    )


def _send_overdue_reminders():
    """
    Scheduled check (Overdue Handling in the flowchart).
    Looks at every active (unreturned) borrowing; any that is past its due date
    is Overdue. The borrower is emailed a reminder, and again every
    REMINDER_REPEAT_DAYS days until the equipment is returned. Returns (reminders sent, reminders that failed, first error).
    """
    from services import email_service

    sent, failed, first_error = 0, 0, None

    for row in get_overdue_transactions():
        last = row.get("overdue_reminder_sent_at")
        if last and (datetime.now() - last).days < REMINDER_REPEAT_DAYS:
            continue

        try:
            email_service.send_overdue_reminder(
                row["borrower_email"], row["borrower_name"], row["equipment_name"],
                row["quantity"], row["due_date"], row["days_overdue"]
            )
        except Exception as exc:
            failed += 1
            first_error = first_error or str(exc)
            continue

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE borrow_requests SET overdue_reminder_sent_at = NOW() WHERE id = %s",
            (row["id"],)
        )
        conn.commit()
        cursor.close()
        conn.close()
        sent += 1

    return sent, failed, first_error


_overdue_lock = threading.Lock()
OVERDUE_CHECK_SECONDS = 30 * 60  # the background check repeats every 30 minutes


def run_overdue_check():
    """
    Run the overdue check. If another check is already running (for example the background one),
    this call is skipped so nobody receives the same reminder twice.
    Returns (reminders sent, reminders that failed, first error).
    """
    if not _overdue_lock.acquire(blocking=False):
        return 0, 0, None

    try:
        return _send_overdue_reminders()
    finally:
        _overdue_lock.release()


def start_overdue_checker():
    """
    Start the overdue check in the background: once right away, then every 30 minutes.
    It does not belong to any window, so it keeps working while only the login screen
    or a student dashboard is open, not just the Admin/Staff dashboard.
    """
    def loop():
        while True:
            try:
                sent, failed, first_error = run_overdue_check()

                if failed:
                    print(f"Overdue check: {failed} reminder(s) could not be sent ({first_error})")
            except Exception as exc:  # e.g. MySQL is not running yet; try again at the next check
                print(f"Overdue check failed: {exc}")

            time.sleep(OVERDUE_CHECK_SECONDS)

    threading.Thread(target=loop, daemon=True).start()


def parse_date_range(from_str, to_str):
    date_from = None
    date_to = None

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
    where = "WHERE br.status = 'Returned'" if returned_only else "WHERE br.status IN ('Approved', 'Returned')"
    params = []

    if date_from:
        where += " AND DATE(br.approved_at) >= %s"
        params.append(date_from)

    if date_to:
        where += " AND DATE(br.approved_at) <= %s"
        params.append(date_to)

    return _select_with_joins(
        where,
        tuple(params),
        order_by="br.returned_at DESC" if returned_only else "br.approved_at DESC"
    )


def get_requests_for_user(user_id):
    return _select_with_joins("WHERE br.user_id = %s", (user_id,))


def get_request_by_id(request_id):
    rows = _select_with_joins("WHERE br.id = %s", (request_id,))
    return rows[0] if rows else None


def _check_reviewer(user_id):
    """Only an active Admin or Staff account may approve or deny requests. Returns an error message or None."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT role, status FROM users WHERE id = %s", (user_id,))
    reviewer = cursor.fetchone()
    cursor.close()
    conn.close()

    if not reviewer or reviewer["status"] != "active" or reviewer["role"] not in RETURN_ROLES:
        return "Only an active Admin or Staff account can review borrow requests."

    return None


def approve_request(request_id, approved_by_user_id, due_date_str=None):
    error = _check_reviewer(approved_by_user_id)

    if error:
        return False, error

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

    # Lock the equipment row so two staff members approving at the same time
    # cannot hand out more units than exist.
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT quantity, under_repair FROM equipment WHERE id = %s FOR UPDATE",
            (request["equipment_id"],)
        )
        equipment = cursor.fetchone()

        if request.get("equipment_deleted") or not equipment:
            conn.rollback()
            return False, "This equipment no longer exists."

        cursor.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS borrowed FROM borrow_requests "
            "WHERE equipment_id = %s AND status = 'Approved' AND id != %s",
            (request["equipment_id"], request_id)
        )
        borrowed = int(cursor.fetchone()["borrowed"])
        available = max(0, equipment["quantity"] - int(equipment["under_repair"] or 0) - borrowed) if equipment else 0

        if request["quantity"] > available:
            conn.rollback()
            return False, f"Cannot approve: only {available} units of '{request['equipment_name']}' are currently available."

        cursor.execute(
            """
            UPDATE borrow_requests
            SET status = 'Approved',
                approved_by = %s,
                approved_at = NOW(),
                due_date = %s
            WHERE id = %s AND status = 'Pending'
            """,
            (approved_by_user_id, due_date, request_id)
        )

        updated = cursor.rowcount
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    if updated == 0:
        return False, "This request has already been reviewed."

    return True, f"Request approved. '{request['equipment_name']}' is now borrowed."


def cancel_request(request_id, user_id):
    """A borrower withdraws their own request while it is still Pending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE borrow_requests SET status = 'Cancelled' "
        "WHERE id = %s AND user_id = %s AND status = 'Pending'",
        (request_id, user_id)
    )
    changed = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if changed == 0:
        return False, "Only your own pending requests can be cancelled."

    return True, "Your request has been cancelled."


def _notify_denied(request):
    """Email the borrower that the request was denied (runs in the background)."""
    from services import email_service

    try:
        email_service.send_denial_notice(
            request["borrower_email"], request["borrower_name"],
            request["equipment_name"], request["quantity"], request.get("deny_reason")
        )
    except Exception as exc:  # the request stays denied even if the email cannot be sent
        print(f"Could not send the denial email: {exc}")


def deny_request(request_id, approved_by_user_id, reason=None):
    error = _check_reviewer(approved_by_user_id)

    if error:
        return False, error

    request = get_request_by_id(request_id)

    if not request:
        return False, "Request not found."

    if request["status"] != "Pending":
        return False, f"This request has already been {request['status'].lower()}."

    reason = (reason or "").strip()

    if len(reason) > 255:
        return False, "The reason must be 255 characters or fewer."

    request["deny_reason"] = reason or None

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE borrow_requests
        SET status = 'Denied',
            approved_by = %s,
            approved_at = NOW(),
            deny_reason = %s
        WHERE id = %s AND status = 'Pending'
        """,
        (approved_by_user_id, reason or None, request_id)
    )

    updated = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if updated == 0:
        return False, "This request has already been reviewed."

    # Notify Borrower (Request Denied)
    threading.Thread(target=_notify_denied, args=(request,), daemon=True).start()

    return True, "Request has been denied. The borrower is being notified by email."


def _notify_admins_of_incident(request, return_condition, processed_by_name, notes=None):
    """Notify Admin: email every active admin about a damage or loss report (runs in the background)."""
    from services import email_service

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE role = 'Admin' AND status = 'active'")
        admin_emails = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        if not admin_emails:
            return

        email_service.send_incident_notice(
            admin_emails, "Damage" if return_condition == "Damaged" else "Loss",
            request["equipment_name"], request["quantity"], request["borrower_name"],
            processed_by_name, date.today().strftime("%B %d, %Y"), notes
        )
    except Exception as exc:  # the return is already saved even if the email cannot be sent
        print(f"Could not notify the admins: {exc}")


def _load_return(request_id, processed_by_user_id):
    """Checks every return needs. Returns (error_message, request, processor); error_message is None when all is fine."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT role, status, full_name FROM users WHERE id = %s",
        (processed_by_user_id,)
    )

    processor = cursor.fetchone()
    cursor.close()
    conn.close()

    if not processor or processor["status"] != "active":
        return "This account cannot process returns.", None, None

    request = get_request_by_id(request_id)

    if not request:
        return "Transaction not found.", None, None

    # Borrower / Admin selects an active transaction to return:
    # Admin and Staff can return any borrowing, a borrower only their own.
    if processor["role"] not in RETURN_ROLES and request["user_id"] != processed_by_user_id:
        return "You can only return equipment that you borrowed.", None, None

    if request["status"] == "Returned":
        return "This equipment has already been returned.", None, None

    if request["status"] != "Approved":
        return "Only active borrowings can be returned.", None, None

    return None, request, processor


def _return_units(cursor, request, processed_by_user_id, condition, notes, quantity, remaining):
    """
    Save ONE part of a return (for example the 2 damaged units of a 4-unit borrowing).
    It only runs the SQL; the caller commits, so a mixed return is saved all together or not at all.
    `remaining` is how many units of this borrowing are still out right now.
    Returns (ok, error_message).
    """
    if quantity < remaining:
        # Keep the rest as an active borrowing; the returned part becomes its own Returned record.
        cursor.execute(
            "UPDATE borrow_requests SET quantity = quantity - %s "
            "WHERE id = %s AND status = 'Approved' AND quantity = %s",
            (quantity, request["id"], remaining)
        )

        if cursor.rowcount == 0:
            return False, "This borrowing was changed by someone else. Please refresh and try again."

        cursor.execute(
            """
            INSERT INTO borrow_requests
                (user_id, equipment_id, quantity, status, request_date, due_date, approved_by, approved_at,
                 returned_at, returned_by, returned_quantity, return_condition, return_notes, purpose)
            VALUES (%s, %s, %s, 'Returned', %s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s)
            """,
            (request["user_id"], request["equipment_id"], quantity, request["request_date"], request["due_date"],
             request["approved_by"], request["approved_at"], processed_by_user_id, quantity,
             condition, notes or None, request.get("purpose"))
        )
    else:
        cursor.execute(
            """
            UPDATE borrow_requests
            SET status = 'Returned',
                returned_at = NOW(),
                returned_by = %s,
                returned_quantity = quantity,
                return_condition = %s,
                return_notes = %s
            WHERE id = %s AND status = 'Approved' AND quantity = %s
            """,
            (processed_by_user_id, condition, notes or None, request["id"], remaining)
        )

        if cursor.rowcount == 0:
            return False, "This borrowing was already returned or is no longer active."

    # Update Equipment Condition and Availability.
    if condition == "Damaged":
        # The returned units are out of service until an admin clears them in Edit Equipment.
        cursor.execute(
            "UPDATE equipment SET condition_status = 'Needs Repair', "
            "under_repair = LEAST(quantity, under_repair + %s) WHERE id = %s",
            (quantity, request["equipment_id"])
        )
    elif condition == "Lost":
        # The unit never came back, so it is taken out of the total quantity.
        cursor.execute(
            "UPDATE equipment SET quantity = GREATEST(quantity - %s, 0), "
            "under_repair = LEAST(under_repair, quantity) WHERE id = %s",
            (quantity, request["equipment_id"])
        )
    # Good: back in stock; the item's recorded condition is left as it was.

    return True, ""


def check_split_parts(parts, notes):
    """
    Check a mixed return such as {"Good": 2, "Damaged": 2, "Lost": 0}.
    Returns (ok, message, cleaned) where cleaned only keeps the conditions with a quantity above 0.
    """
    cleaned = {}

    for condition in RETURN_CONDITIONS:
        value = parts.get(condition)

        if value is None or str(value).strip() == "":
            value = 0

        try:
            value = int(value)
        except (TypeError, ValueError):
            return False, f"The {condition} quantity must be a whole number.", None

        if value < 0:
            return False, f"The {condition} quantity cannot be negative.", None

        if value > 0:
            cleaned[condition] = value

    if not cleaned:
        return False, "Enter how many units are being returned.", None

    if (cleaned.get("Damaged") or cleaned.get("Lost")) and not (notes or "").strip():
        return False, "Please describe what happened in the notes for damaged or lost items.", None

    return True, "", cleaned


def process_split_return(request_id, processed_by_user_id, parts, notes=None):
    """
    Return a borrowing where the units came back in different conditions
    (for example 2 Good + 2 Damaged). Each condition is saved as its own Returned record,
    so reports count only the damaged units as damaged. Units not entered stay borrowed.
    All parts are saved in ONE database transaction: if anything fails, nothing is saved.
    """
    ok, message, cleaned = check_split_parts(parts, notes)

    if not ok:
        return False, message

    notes = (notes or "").strip()

    if len(notes) > 255:
        return False, "Return notes must be 255 characters or fewer."

    error, request, processor = _load_return(request_id, processed_by_user_id)

    if error:
        return False, error

    total = request["quantity"]
    entered = sum(cleaned.values())

    if entered > total:
        return False, f"You entered {entered} units but only {total} are borrowed."

    conn = get_connection()
    cursor = conn.cursor()

    try:
        remaining = total

        # Damaged and Lost first (they carry the notes), then Good.
        for condition in ("Damaged", "Lost", "Good"):
            quantity = cleaned.get(condition)

            if not quantity:
                continue

            ok, error = _return_units(
                cursor, request, processed_by_user_id, condition,
                notes if condition != "Good" else None, quantity, remaining
            )

            if not ok:
                conn.rollback()
                return False, error

            remaining -= quantity

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    summary = ", ".join(f"{qty} {condition}" for condition, qty in cleaned.items())
    result = f"Return recorded for '{request['equipment_name']}': {summary}."

    if entered < total:
        result += f" {total - entered} unit(s) are still borrowed."

    # Log Damage / Loss Report + Notify Admin (the report is the saved return record).
    for condition in ("Damaged", "Lost"):
        if condition in cleaned:
            threading.Thread(
                target=_notify_admins_of_incident,
                args=(dict(request, quantity=cleaned[condition]), condition, processor["full_name"], notes),
                daemon=True
            ).start()

    if cleaned.get("Damaged") or cleaned.get("Lost"):
        result += " A report was logged and the admins are being notified."

    if cleaned.get("Damaged"):
        result += " The damaged unit(s) are marked under repair and are not available to borrow."

    if request["days_overdue"] > 0:
        result += f" It was returned {request['days_overdue']} days late."

    return True, result


def process_return(request_id, processed_by_user_id, return_condition, notes=None, quantity=None):
    """Return units that are all in the same condition (a mixed return uses process_split_return)."""
    if return_condition not in RETURN_CONDITIONS:
        return False, "Please select the condition of the returned equipment."

    notes = (notes or "").strip()

    if len(notes) > 255:
        return False, "Return notes must be 255 characters or fewer."

    if return_condition in ("Damaged", "Lost") and not notes:
        return False, "Please describe what happened in the notes for a damaged or lost item."

    if quantity is None or str(quantity).strip() == "":
        request = get_request_by_id(request_id)

        if not request:
            return False, "Transaction not found."

        quantity = request["quantity"]  # no quantity entered: all the borrowed units

    return process_split_return(request_id, processed_by_user_id, {return_condition: quantity}, notes)


def get_report_summary(date_from=None, date_to=None):
    from services import equipment_service

    today = date.today()
    items = equipment_service.get_all_equipment()
    available_units = sum(get_available_quantity(item["id"]) for item in items)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT COUNT(*) AS transactions,
               COALESCE(SUM(quantity), 0) AS units
        FROM borrow_requests
        WHERE status = 'Approved'
        """
    )
    borrowed = cursor.fetchone()

    cursor.execute(
        """
        SELECT COUNT(*) AS transactions,
               COALESCE(SUM(quantity), 0) AS units
        FROM borrow_requests
        WHERE status = 'Approved' AND due_date < %s
        """,
        (today,)
    )
    overdue = cursor.fetchone()

    returned_query = """
        SELECT COUNT(*) AS transactions,
               COALESCE(SUM(returned_quantity), 0) AS units
        FROM borrow_requests
        WHERE status = 'Returned'
    """
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
        "returned_transactions": int(returned["transactions"])
    }
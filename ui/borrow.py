"""
Dialogs for the borrowing workflow: Request -> Approval -> Borrowing Transaction.

RequestEquipmentDialog - used by Student/Teacher/Staff to submit a borrow request.
ApproveRequestDialog   - used by Admin/Staff to approve a Pending request
                         (with an optional due-date override) or review before denying.
"""

from ui import colors
from ui.helpers import FormDialog, label
import borrow_service


class RequestEquipmentDialog(FormDialog):
    def __init__(self, parent, user, equipment_item, available_quantity, on_success=None):
        super().__init__(parent, "Request Equipment", "360x400", heading="Request to Borrow", gap=16)
        self.user, self.equipment_item, self.on_success = user, equipment_item, on_success
 
        label(self, equipment_item["name"], 14, True).pack(anchor="w", padx=30, pady=(8, 0))
        label(self, f"{available_quantity} unit(s) currently available", color=colors.TEXT_GRAY).pack(anchor="w", padx=30)
        self.quantity_entry = self.f.entry("Quantity", "e.g. 1")
        self.quantity_entry.insert(0, "1")
        self.due_date_entry = self.f.entry("Due Date (when you'll return it)", "YYYY-MM-DD")
        self.footer("Submit Request", self.handle_submit)
 
    def handle_submit(self):
        ok, message = borrow_service.create_request(
            self.user["id"], self.equipment_item["id"], self.quantity_entry.get(), self.due_date_entry.get())
        self.result(ok, message, self.on_success)
 
 
class ApproveRequestDialog(FormDialog):
    def __init__(self, parent, approver_user, request_row, on_success=None):
        super().__init__(parent, "Approve Request", "360x400", gap=16)
        self.approver_user, self.request_row, self.on_success = approver_user, request_row, on_success
 
        label(self, f"{request_row['equipment_name']}  x{request_row['quantity']}", 14, True).pack(anchor="w", padx=30, pady=(8, 0))
        label(self, f"Requested by {request_row['borrower_name']} ({request_row['borrower_role']})",
              color=colors.TEXT_GRAY).pack(anchor="w", padx=30)
        available = borrow_service.get_available_quantity(request_row["equipment_id"], exclude_request_id=request_row["id"])
        label(self, f"{available} unit(s) currently available", color=colors.TEXT_GRAY).pack(anchor="w", padx=30, pady=(2, 0))
 
        self.due_date_entry = self.f.entry("Due Date", "YYYY-MM-DD")  # pre-filled with the borrower's proposed date
        if request_row.get("due_date"):
            self.due_date_entry.insert(0, str(request_row["due_date"]))
        self.footer("Approve Request", self.handle_approve, fg=colors.SUCCESS_GREEN, hover="#166838")
 
    def handle_approve(self):
        ok, message = borrow_service.approve_request(
            self.request_row["id"], self.approver_user["id"], self.due_date_entry.get())
        self.result(ok, message, self.on_success, 1000)
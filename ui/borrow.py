"""Dialogs for the borrowing workflow: Request -> Approval -> Borrowing Transaction."""
from ui import colors
from ui.helpers import FormDialog, label
import borrow_service


class RequestEquipmentDialog(FormDialog):
    """Student / Teacher / Staff: submit a borrow request."""

    def __init__(self, parent, user, item, available, on_success=None):
        super().__init__(parent, "Request to Borrow", "360x440")
        self.user, self.item, self.on_success = user, item, on_success
        f = self.f
        f.place(label(self, item["name"], 14, True), (8, 0))
        f.place(label(self, f"{available} unit(s) currently available", color=colors.TEXT_GRAY))
        self.quantity_entry = f.entry("Quantity", "e.g. 1")
        self.quantity_entry.insert(0, "1")
        self.due_date_entry = f.entry("Due Date (when you'll return it)", "YYYY-MM-DD")
        self.footer("Submit Request", self.handle_submit)

    def handle_submit(self):
        ok, message = borrow_service.create_request(
            self.user["id"], self.item["id"], self.quantity_entry.get(), self.due_date_entry.get())
        self.result(ok, message, self.on_success)


class ApproveRequestDialog(FormDialog):
    """Admin / Staff: approve a Pending request, optionally overriding the due date."""

    def __init__(self, parent, approver_user, request_row, on_success=None):
        super().__init__(parent, "Approve Request", "360x470")
        self.approver, self.req, self.on_success = approver_user, request_row, on_success
        f, r = self.f, request_row
        available = borrow_service.get_available_quantity(r["equipment_id"], exclude_request_id=r["id"])
        f.place(label(self, f"{r['equipment_name']}  x{r['quantity']}", 14, True), (8, 0))
        f.place(label(self, f"Requested by {r['borrower_name']} ({r['borrower_role']})", color=colors.TEXT_GRAY))
        f.place(label(self, f"{available} units currently available", color=colors.TEXT_GRAY))
        self.due_date_entry = f.entry("Due Date", "YYYY-MM-DD")
        if r.get("due_date"):
            self.due_date_entry.insert(0, str(r["due_date"]))
        f.place(label(self, "This was proposed by the borrower. Edit it to override.", 11,
                      color=colors.TEXT_GRAY, wraplength=300, justify="left"), (4, 0))
        self.footer("Approve Request", self.handle_approve)
        self.submit_btn.configure(fg_color=colors.SUCCESS_GREEN, hover_color="#166838")

    def handle_approve(self):
        ok, message = borrow_service.approve_request(self.req["id"], self.approver["id"], self.due_date_entry.get())
        self.result(ok, message, self.on_success, 1000)
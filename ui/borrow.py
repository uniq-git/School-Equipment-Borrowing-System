"""Dialogs for the borrowing workflow: Request -> Approval -> Borrowing Transaction -> Return."""
from datetime import date, timedelta

import customtkinter as ctk

from ui import colors
from ui.helpers import FormDialog, fmt_date, label
from services import borrow_service


class RequestEquipmentDialog(FormDialog):
    """Student / Teacher: submit a borrow request."""

    def __init__(self, parent, user, item, available, on_success=None):
        super().__init__(parent, "Request to Borrow", "360x520")
        self.user, self.item, self.on_success = user, item, on_success
        f = self.f
        f.place(label(self, item["name"], 14, True), (8, 0))
        f.place(label(self, f"{available} units currently available", color=colors.TEXT_GRAY))
        self.quantity_entry = f.entry("Quantity", "e.g. 1")
        self.quantity_entry.insert(0, "1")
        self.due_date_entry = f.date("Due Date (when you'll return it)",
                                     min_date=date.today() + timedelta(days=1))
        self.purpose_entry = f.entry("Purpose (optional)", "e.g. Class presentation")
        self.footer("Submit Request", self.handle_submit)

    def handle_submit(self):
        ok, message = borrow_service.create_request(
            self.user["id"], self.item["id"], self.quantity_entry.get(), self.due_date_entry.get(),
            self.purpose_entry.get())
        self.result(ok, message, self.on_success)


class ApproveRequestDialog(FormDialog):
    """Admin / Staff: approve a Pending request, optionally overriding the due date."""

    def __init__(self, parent, approver_user, request_row, on_success=None):
        super().__init__(parent, "Approve Request", "360x540")
        self.approver, self.req, self.on_success = approver_user, request_row, on_success
        f, r = self.f, request_row
        available = borrow_service.get_available_quantity(r["equipment_id"], exclude_request_id=r["id"])
        f.place(label(self, f"{r['equipment_name']}  x{r['quantity']}", 14, True), (8, 0))
        f.place(label(self, f"Requested by {r['borrower_name']} ({r['borrower_role']})", color=colors.TEXT_GRAY))
        f.place(label(self, f"{available} units currently available", color=colors.TEXT_GRAY))
        if r.get("purpose"):
            f.place(label(self, f"Purpose: {r['purpose']}", color=colors.TEXT_GRAY, wraplength=300,
                          justify="left", anchor="w"))
        self.due_date_entry = f.date("Due Date", min_date=date.today() + timedelta(days=1),
                                     initial=r.get("due_date"))
        f.place(label(self, "This was proposed by the borrower. Pick another date to override.", 11,
                      color=colors.TEXT_GRAY, wraplength=300, justify="left"), (4, 0))
        self.footer("Approve Request", self.handle_approve)
        self.submit_btn.configure(fg_color=colors.SUCCESS_GREEN, hover_color="#166838")

    def handle_approve(self):
        ok, message = borrow_service.approve_request(self.req["id"], self.approver["id"], self.due_date_entry.get())
        self.result(ok, message, self.on_success, 1000)


class DenyRequestDialog(FormDialog):
    """Admin / Staff: deny a Pending request with an optional reason (included in the borrower's email)."""

    def __init__(self, parent, approver_user, request_row, on_success=None):
        super().__init__(parent, "Deny Request", "360x340")
        self.approver, self.req, self.on_success = approver_user, request_row, on_success
        f, r = self.f, request_row
        f.place(label(self, f"{r['equipment_name']}  x{r['quantity']}", 14, True), (8, 0))
        f.place(label(self, f"Requested by {r['borrower_name']} ({r['borrower_role']})", color=colors.TEXT_GRAY))
        self.reason_entry = f.entry("Reason (optional)", "e.g. Needed for another class")
        self.footer("Deny Request", self.handle_deny)
        self.submit_btn.configure(fg_color=colors.ACCENT_RED, hover_color="#b52a48")

    def handle_deny(self):
        ok, message = borrow_service.deny_request(self.req["id"], self.approver["id"], self.reason_entry.get())
        self.result(ok, message, self.on_success, 1000)


class ReturnDialog(FormDialog):
    """Borrower / Admin / Staff: record the return of an active borrowing (uses borrow_service.process_return)."""

    def __init__(self, parent, processor_user, txn, on_success=None):
        super().__init__(parent, "Return Equipment", "380x700")
        self.processor, self.txn, self.on_success = processor_user, txn, on_success
        f, t = self.f, txn
        f.place(label(self, f"{t['equipment_name']}  x{t['quantity']}", 14, True), (8, 0))
        details = (f"Transaction ID: {t['id']}\n"
                   f"Borrower: {t['borrower_name']} ({t['borrower_role']})\n"
                   f"Borrow date: {fmt_date(t['approved_at'] or t['request_date'])}\n"
                   f"Due date: {fmt_date(t['due_date'])}\n"
                   f"Status: {t['state']}")
        f.place(label(self, details, color=colors.TEXT_GRAY, justify="left", anchor="w"), (4, 0))
        if t["days_overdue"] > 0:
            f.place(label(self, f"Overdue by {t['days_overdue']} days. It can still be returned; "
                                "the original due date is kept.", 11, color=colors.ACCENT_RED,
                          wraplength=300, justify="left"), (6, 0))

        f.place(label(self, f"Enter how many units came back in each condition (up to {t['quantity']} in total). "
                            "Units not entered stay borrowed.", 11, color=colors.TEXT_GRAY,
                      wraplength=300, justify="left"), (6, 0))
        self.good_var = self._qty_field("Good condition (qty)", str(t["quantity"]))
        self.damaged_var = self._qty_field("Damaged (qty)", "0")
        self.lost_var = self._qty_field("Lost (qty)", "0")

        # The notes box only shows while at least 1 unit is Damaged or Lost.
        self.notes_label = f.label("Notes (what happened?)")
        self.notes_entry = f.place(f.input(self, "Describe the damage or loss", 300))
        self._toggle_notes()
        self.footer("Confirm Return", self.handle_return)
        self.submit_btn.configure(fg_color=colors.SUCCESS_GREEN, hover_color="#166838")

    def _qty_field(self, text, value):
        """A labelled quantity box; the notes box is re-checked every time it changes."""
        var = ctk.StringVar(value=value)
        self.f.label(text)
        self.f.place(self.f.input(self, "0", 300, textvariable=var))
        var.trace_add("write", lambda *_: self._toggle_notes())
        return var

    @staticmethod
    def _qty(var):
        text = var.get().strip()
        return int(text) if text.isdigit() else 0

    def _toggle_notes(self):
        """Show the notes box only if Damaged or Lost is 1 or more; hide it for Good-only returns."""
        if not hasattr(self, "notes_entry"):  # the form is still being built
            return
        needs_notes = self._qty(self.damaged_var) > 0 or self._qty(self.lost_var) > 0
        if needs_notes:
            self.notes_label.pack(anchor="w", padx=30, pady=(10, 4))
            self.notes_entry.pack(anchor="w", padx=30)
        else:
            self.notes_label.pack_forget()
            self.notes_entry.pack_forget()

    def handle_return(self):
        parts = {"Good": self.good_var.get(), "Damaged": self.damaged_var.get(), "Lost": self.lost_var.get()}
        ok, message = borrow_service.process_split_return(
            self.txn["id"], self.processor["id"], parts, self.notes_entry.get())
        self.result(ok, message, self.on_success, 1200)
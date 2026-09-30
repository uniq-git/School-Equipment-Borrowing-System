"""
Dialogs for the borrowing workflow: Request -> Approval -> Borrowing Transaction.

RequestEquipmentDialog - used by Student/Teacher/Staff to submit a borrow request.
ApproveRequestDialog   - used by Admin/Staff to approve a Pending request
                         (with an optional due-date override) or review before denying.
"""
import customtkinter as ctk

from ui import colors
import borrow_service


class RequestEquipmentDialog(ctk.CTkToplevel):
    def __init__(self, parent, user, equipment_item, available_quantity, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.user = user
        self.equipment_item = equipment_item
        self.available_quantity = available_quantity
        self.on_success = on_success

        self.title("Request Equipment")
        self.geometry("360x400")
        self.resizable(False, False)
        self.configure(fg_color=colors.CARD_WHITE)
        self.transient(parent)
        self.grab_set()

        pad_x = 30

        ctk.CTkLabel(
            self, text="Request to Borrow", font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors.TEXT_DARK,
        ).pack(anchor="w", padx=pad_x, pady=(20, 4))

        ctk.CTkLabel(
            self, text=equipment_item["name"], font=ctk.CTkFont(size=14, weight="bold"),
            text_color=colors.TEXT_DARK,
        ).pack(anchor="w", padx=pad_x, pady=(8, 0))

        ctk.CTkLabel(
            self, text=f"{available_quantity} unit(s) currently available",
            font=ctk.CTkFont(size=12), text_color=colors.TEXT_GRAY,
        ).pack(anchor="w", padx=pad_x)

        ctk.CTkLabel(
            self, text="Quantity", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(16, 4))

        self.quantity_entry = ctk.CTkEntry(
            self, placeholder_text="e.g. 1", height=34, width=300,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.pack(anchor="w", padx=pad_x)

        ctk.CTkLabel(
            self, text="Due Date (when you'll return it)",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(16, 4))

        self.due_date_entry = ctk.CTkEntry(
            self, placeholder_text="YYYY-MM-DD", height=34, width=300,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        self.due_date_entry.pack(anchor="w", padx=pad_x)

        ctk.CTkLabel(
            self, text="Admin/Staff may adjust this date when approving your request.",
            font=ctk.CTkFont(size=11), text_color=colors.TEXT_GRAY, wraplength=300, justify="left",
        ).pack(anchor="w", padx=pad_x, pady=(4, 0))

        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color=colors.ACCENT_RED,
            wraplength=300, justify="left",
        )
        self.status_label.pack(anchor="w", padx=pad_x, pady=(12, 0))

        ctk.CTkButton(
            self, text="Submit Request", height=40, width=300, fg_color=colors.BUTTON_BLUE,
            hover_color=colors.BUTTON_BLUE_HOVER, font=ctk.CTkFont(size=13, weight="bold"),
            command=self.handle_submit,
        ).pack(anchor="w", padx=pad_x, pady=(16, 6))

        ctk.CTkButton(
            self, text="Cancel", height=32, width=300, fg_color="transparent",
            hover_color=colors.BG_LIGHT, text_color=colors.TEXT_GRAY, command=self.destroy,
        ).pack(anchor="w", padx=pad_x)

    def handle_submit(self):
        quantity = self.quantity_entry.get()
        due_date = self.due_date_entry.get()

        success, message = borrow_service.create_request(
            self.user["id"], self.equipment_item["id"], quantity, due_date
        )

        if success:
            self.status_label.configure(text=message, text_color=colors.SUCCESS_GREEN)

            if self.on_success:
                self.on_success()

            self.after(1200, self.destroy)
        else:
            self.status_label.configure(text=message, text_color=colors.ACCENT_RED)


class ApproveRequestDialog(ctk.CTkToplevel):
    def __init__(self, parent, approver_user, request_row, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.approver_user = approver_user
        self.request_row = request_row
        self.on_success = on_success

        self.title("Approve Request")
        self.geometry("360x400")
        self.resizable(False, False)
        self.configure(fg_color=colors.CARD_WHITE)
        self.transient(parent)
        self.grab_set()

        pad_x = 30

        ctk.CTkLabel(
            self, text="Approve Request", font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors.TEXT_DARK,
        ).pack(anchor="w", padx=pad_x, pady=(20, 4))

        ctk.CTkLabel(
            self, text=f"{request_row['equipment_name']}  x{request_row['quantity']}",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=colors.TEXT_DARK,
        ).pack(anchor="w", padx=pad_x, pady=(8, 0))

        ctk.CTkLabel(
            self,
            text=f"Requested by {request_row['borrower_name']} ({request_row['borrower_role']})",
            font=ctk.CTkFont(size=12), text_color=colors.TEXT_GRAY,
        ).pack(anchor="w", padx=pad_x)

        available = borrow_service.get_available_quantity(
            request_row["equipment_id"], exclude_request_id=request_row["id"]
        )
        ctk.CTkLabel(
            self, text=f"{available} unit(s) currently available",
            font=ctk.CTkFont(size=12), text_color=colors.TEXT_GRAY,
        ).pack(anchor="w", padx=pad_x, pady=(2, 0))

        ctk.CTkLabel(
            self, text="Due Date", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(16, 4))

        self.due_date_entry = ctk.CTkEntry(
            self, placeholder_text="YYYY-MM-DD", height=34, width=300,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        self.due_date_entry = ctk.CTkEntry(self, justify="center")
        proposed_due_date = request_row.get("due_date")
        if proposed_due_date:
            self.due_date_entry.insert(0, str(proposed_due_date))
        self.due_date_entry.pack(anchor="w", padx=pad_x, )

        ctk.CTkLabel(
            self, text="This was proposed by the borrower. Edit it to override.",
            font=ctk.CTkFont(size=11), text_color=colors.TEXT_GRAY, wraplength=300, justify="left",
        ).pack(anchor="w", padx=pad_x, pady=(4, 0))

        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color=colors.ACCENT_RED,
            wraplength=300, justify="left",
        )
        self.status_label.pack(anchor="w", padx=pad_x, pady=(12, 0))

        ctk.CTkButton(
            self, text="Approve Request", height=40, width=300, fg_color=colors.SUCCESS_GREEN,
            hover_color="#166838", font=ctk.CTkFont(size=13, weight="bold"),
            command=self.handle_approve,
        ).pack(anchor="w", padx=pad_x, pady=(16, 6))

        ctk.CTkButton(
            self, text="Cancel", height=32, width=300, fg_color="transparent",
            hover_color=colors.BG_LIGHT, text_color=colors.TEXT_GRAY, command=self.destroy,
        ).pack(anchor="w", padx=pad_x)

    def handle_approve(self):
        due_date = self.due_date_entry.get()

        success, message = borrow_service.approve_request(
            self.request_row["id"], self.approver_user["id"], due_date
        )

        if success:
            self.status_label.configure(text=message, text_color=colors.SUCCESS_GREEN)

            if self.on_success:
                self.on_success()

            self.after(1000, self.destroy)
        else:
            self.status_label.configure(text=message, text_color=colors.ACCENT_RED)
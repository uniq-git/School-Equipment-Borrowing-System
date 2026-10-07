"""Change Password pop-up: verify your email with a 6-digit code, then set a new password."""
from ui import colors
from ui.helpers import FormDialog, VerifyMixin
from services import auth


class ChangePasswordDialog(VerifyMixin, FormDialog):
    def __init__(self, parent, user):
        super().__init__(parent, "Change Password", "380x680")
        self.user = user
        f = self.f

        # The logged-in user's own email: shown in a locked box, not typed in.
        self.email_entry = f.entry("Email Address", "")
        self.email_entry.insert(0, user["email"])
        self.email_entry.configure(state="disabled", text_color=colors.TEXT_GRAY)
        self.verify_section(f, "Verify")
        self.current_password_entry = f.password("Current Password", "Enter your current password")
        self.new_password_entry = f.password("New Password", "Create a new password")
        self.confirm_password_entry = f.password("Confirm New Password", "Re-enter new password")
        self.footer("Change Password", self.handle_submit)
        self.error_label = self.status  # VerifyMixin shows its messages in the same status line

    def handle_submit(self):
        current, new = self.current_password_entry.get(), self.new_password_entry.get()
        if not current:
            return self.show("Please enter your current password.")
        if new != self.confirm_password_entry.get():
            return self.show("Passwords do not match.")

        ok, message = auth.change_password_verified(self.user["id"], current, new)
        self.result(ok, message)  # on success: shows the message, disables the button, closes the window
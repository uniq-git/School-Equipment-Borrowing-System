"""Student / Teacher dashboard (navy sidebar + light content area, like the login screen)."""
from ui import colors
from ui.helpers import FormDialog, VerifyMixin, label
import auth


class ChangePasswordDialog(VerifyMixin, FormDialog):
    def __init__(self, parent, user):
        super().__init__(parent, "Change Password", "380x680", top=24)
        self.user, self.email = user, user["email"]
        f = self.f
 
        f.title("Email Address", gap=18)
        f.place(label(self, self.email, 13, fg_color=colors.ENTRY_BG, corner_radius=6,
                      height=36, width=300, anchor="w"))
        self.verify_section(f, "Verify")
        self.current_password_entry = f.password("Current Password", "Enter your current password")
        self.new_password_entry = f.password("New Password", "Create a new password")
        self.confirm_password_entry = f.password("Confirm New Password", "Re-enter new password")
        self.footer("Change Password", self.handle_submit, status_pady=(8, 0))
 
    def get_email(self):
        return self.email  # the logged-in user's email, not typed in
 
    def handle_submit(self):
        current, new = self.current_password_entry.get(), self.new_password_entry.get()
        if not current:
            return self.error_label.configure(text="Please enter your current password.")
        if new != self.confirm_password_entry.get():
            return self.error_label.configure(text="Passwords do not match.")
 
        ok, message = auth.change_password_verified(self.user["id"], current, new)
        if ok:
            self.done(message, self.destroy, 1200)
        else:
            self.error_label.configure(text=message)
 
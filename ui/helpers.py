# Shortcuts for making the buttons, labels and input boxes
# so we don't repeat the same lines in every screen.
import threading
import customtkinter as ctk

from ui import colors
from ui.left_panel import build_left_panel
import auth
import email_service


def font(size=12, bold=False):
    return ctk.CTkFont(size=size, weight="bold" if bold else "normal")


def label(parent, text, size=12, bold=False, color=colors.TEXT_DARK, **kw):
    return ctk.CTkLabel(parent, text=text, font=font(size, bold), text_color=color, **kw)


def button(parent, text, command, w=100, h=36, fg=colors.BUTTON_BLUE, hover=colors.BUTTON_BLUE_HOVER, **kw):
    return ctk.CTkButton(parent, text=text, command=command, width=w, height=h,
                         fg_color=fg, hover_color=hover, **kw)


def soft_button(parent, text, command, w=100, h=34, **kw):
    # gray button (Show, Browse, Send Verification Code)
    return button(parent, text, command, w, h, colors.ENTRY_BG, colors.BORDER_GRAY,
                  text_color=colors.TEXT_DARK, **kw)


def link(parent, text, command, size=12, bold=True, w=20, **kw):
    # blue text that acts like a button, e.g. "Register here"
    return ctk.CTkButton(parent, text=text, command=command, width=w, fg_color="transparent", hover=False,
                         text_color=colors.LINK_BLUE, font=font(size, bold), **kw)


def entry(parent, placeholder, w=300, h=34, **kw):
    return ctk.CTkEntry(parent, placeholder_text=placeholder, width=w, height=h, fg_color=colors.ENTRY_BG,
                        border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK, **kw)


def goto_login(window):
    # used for log out and "back to login"
    window.destroy()
    from ui.login import LoginWindow
    LoginWindow().mainloop()


class Fields:
    # makes a title + input row. Example:
    #   f = Fields(card, pad_x=30, h=34, gap=14)
    #   name_box = f.entry("Full Name", "Enter your full name")

    def __init__(self, parent, pad_x=30, h=34, gap=14):
        self.parent, self.pad_x, self.h, self.gap = parent, pad_x, h, gap

    def place(self, widget, pady=0):
        widget.pack(anchor="w", padx=self.pad_x, pady=pady)
        return widget

    def title(self, text, gap=None):
        label(self.parent, text, 13, True).pack(anchor="w", padx=self.pad_x, pady=(gap or self.gap, 4))

    def entry(self, title, placeholder, gap=None):
        self.title(title, gap)
        return self.place(entry(self.parent, placeholder, h=self.h))

    def password(self, title, placeholder, gap=None):
        self.title(title, gap)
        row = self.place(ctk.CTkFrame(self.parent, fg_color="transparent"))
        field = entry(row, placeholder, w=245, h=self.h, show="*")
        field.pack(side="left")

        def toggle():
            # switch between hidden and visible password
            hidden = field.cget("show") == "*"
            field.configure(show="" if hidden else "*")
            btn.configure(text="Hide" if hidden else "Show")

        btn = soft_button(row, "Show", toggle, w=48, h=self.h)
        btn.pack(side="left", padx=(6, 0))
        return field

    def menu(self, title, values, variable, command=None):
        self.title(title)
        return self.place(ctk.CTkOptionMenu(self.parent, values=values, variable=variable, width=300, command=command))

    def error(self, pady=(8, 0)):
        # red message under the form
        return self.place(label(self.parent, "", 12, color=colors.ACCENT_RED, wraplength=300, justify="left"), pady)

    def submit(self, text, command, h=40, pady=(14, 10), **kw):
        # the big main button
        return self.place(button(self.parent, text, command, w=300, h=h, font=font(14, True), **kw), pady)


class AuthWindow(ctk.CTk):
    # login, register and forgot password all look the same:
    # navy panel on the left, white card on the right. Put the form inside self.card.

    def __init__(self, title, height, card_h, scroll=False):
        super().__init__()
        self.title(f"ICCT Colleges Foundation, Inc. - {title}")
        self.geometry(f"973x{height}")
        self.resizable(False, False)
        self.configure(fg_color=colors.BG_LIGHT)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        build_left_panel(self, height=height).grid(row=0, column=0, sticky="nswe")
        right = ctk.CTkFrame(self, fg_color=colors.BG_LIGHT, corner_radius=0)
        right.grid(row=0, column=1, sticky="nswe")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        if scroll:  # for long forms like register
            self.card = ctk.CTkScrollableFrame(
                right, fg_color=colors.CARD_WHITE, corner_radius=12, width=380, height=card_h,
                scrollbar_button_color=colors.BORDER_GRAY, scrollbar_fg_color=colors.CARD_WHITE)
            self.card.grid(row=0, column=0, pady=18)
        else:
            self.card = ctk.CTkFrame(right, fg_color=colors.CARD_WHITE, corner_radius=12, width=380, height=card_h)
            self.card.grid(row=0, column=0)
            self.card.grid_propagate(False)

    def open_login(self):
        goto_login(self)


class FormDialog(ctk.CTkToplevel):
    # popup form (Add User, Change Password, Request...)
    # add the fields with self.f, then call self.footer() at the end

    def __init__(self, parent, title, size, heading=None, top=20, gap=14):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.geometry(size)
        self.resizable(False, False)
        self.configure(fg_color=colors.CARD_WHITE)
        self.transient(parent)
        self.grab_set()
        self.f = Fields(self, 30, h=34, gap=gap)
        label(self, heading or title, 20, True).pack(anchor="w", padx=30, pady=(top, 4))

    def footer(self, text, command, status_pady=(12, 0), fg=colors.BUTTON_BLUE, hover=colors.BUTTON_BLUE_HOVER):
        # message line, main button, then Cancel
        self.error_label = self.f.error(status_pady)
        self.f.place(button(self, text, command, w=300, h=40, fg=fg, hover=hover, font=font(13, True)), (16, 6))
        self.f.place(button(self, "Cancel", self.destroy, w=300, h=32, fg="transparent",
                            hover=colors.BG_LIGHT, text_color=colors.TEXT_GRAY))

    def show(self, message, ok=False):
        # green if it worked, red if not
        self.error_label.configure(text=message, text_color=colors.SUCCESS_GREEN if ok else colors.ACCENT_RED)

    def result(self, ok, message, on_success=None, delay=1200):
        # if it worked: refresh the list behind, then close the popup after a moment
        self.show(message, ok)
        if ok:
            if on_success:
                on_success()
            self.after(delay, self.destroy)


class VerifyMixin:
    # send code / verify code, shared by register, forgot password and change password.
    # The screen needs self.error_label and an email (see get_email).
    #
    # must_exist:
    #   True  = email must already have an account (forgot password)
    #   False = email must not be registered yet (register)
    #   None  = don't check (change password)

    must_exist = None

    def get_email(self):
        return self.email_entry.get().strip().lower()

    def verify_section(self, f, verify_text="Verify", send_h=32):
        soft_button(f.parent, "Send Verification Code", self.handle_send_code, w=300, h=send_h,
                    font=font(12, True)).pack(anchor="w", padx=f.pad_x, pady=(8, 0))
        f.title("Verification Code")
        row = f.place(ctk.CTkFrame(f.parent, fg_color="transparent"))
        self.code_var = ctk.StringVar()
        self._last_checked = None
        self.code_var.trace_add("write", self._on_code_changed)
        entry(row, "6-digit code", w=210, h=f.h, textvariable=self.code_var).pack(side="left")
        button(row, verify_text, self.handle_verify_code, w=84, h=f.h).pack(side="left", padx=(6, 0))
        self.verify_status_label = f.place(
            label(f.parent, "Email not verified yet.", 11, color=colors.TEXT_GRAY, wraplength=300, justify="left"),
            (4, 0))

    def _status(self, text, color=colors.TEXT_GRAY):
        self.verify_status_label.configure(text=text, text_color=color)

    def handle_send_code(self):
        email, error = self.get_email(), None
        if self.must_exist is not None:
            if not auth.is_valid_email(email):
                error = "Please enter a valid email address first."
            elif bool(auth.email_exists(email)) != self.must_exist:
                error = ("No account found with that email address." if self.must_exist
                         else "This email is already registered.")
        self.error_label.configure(text=error or "")
        if error:
            return

        self._status("Sending code...")

        def worker():
            # runs in the background so the window doesn't freeze
            try:
                email_service.send_and_store_code(email)
                self._status(f"Code sent to {email}. Check your inbox.")
            except Exception as exc:
                self._status(f"Failed to send email: {exc}", colors.ACCENT_RED)

        threading.Thread(target=worker, daemon=True).start()

    def _on_code_changed(self, *_):
        # verify by itself once 6 digits are typed or pasted
        code = self.code_var.get().strip()
        if len(code) == 6 and code.isdigit() and code != self._last_checked:
            self._last_checked = code
            self.handle_verify_code()

    def handle_verify_code(self):
        code = self.code_var.get().strip()
        if not code:
            return self.error_label.configure(text="Please enter the verification code.")
        ok, message = email_service.verify_code(self.get_email(), code)
        self.error_label.configure(text="" if ok else message)
        self._status(message, colors.SUCCESS_GREEN if ok else colors.ACCENT_RED)

    def done(self, message, then, delay=1500):
        # success: show the message in green, then run `then` (close or go to login)
        self.error_label.configure(text="")
        self._status(message, colors.SUCCESS_GREEN)
        self.after(delay, then)
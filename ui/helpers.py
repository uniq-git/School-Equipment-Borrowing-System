# Shared UI helpers: dashboards (sidebar, tables) and auth screens (login / register / forgot password)
import calendar
import os
import threading
import tkinter as tk
from datetime import date, datetime

import customtkinter as ctk
from tkinter import messagebox, ttk
from PIL import Image

from ui import colors
from ui.left_panel import ASSETS_DIR, build_left_panel
from services import auth, email_service

SIDEBAR_W, NAV_TEXT, NAV_ACTIVE, NAV_HOVER = 250, "#c7cede", "#1f3357", "#1a2b49"
RED_HOVER, GREEN_HOVER, SELECT_BG, AMBER = "#b52a48", "#166838", "#dbe4f3", "#b7791f"


# small widgets

def label(parent, text, size=12, bold=False, color=colors.TEXT_DARK, **kw):
    font = ctk.CTkFont(size=size, weight="bold" if bold else "normal")
    return ctk.CTkLabel(parent, text=text, font=font, text_color=color, **kw)


def button(parent, text, command, w=100, h=36, fg=colors.BUTTON_BLUE, hover=colors.BUTTON_BLUE_HOVER, **kw):
    kw.setdefault("corner_radius", 3)  # square-ish corners, like a normal desktop button
    return ctk.CTkButton(parent, text=text, command=command, width=w, height=h,
                         fg_color=fg, hover_color=hover, **kw)


def entry(parent, placeholder, w=300, h=36, **kw):
    return ctk.CTkEntry(parent, placeholder_text=placeholder, width=w, height=h, fg_color=colors.ENTRY_BG,
                        border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK, **kw)


def soft_button(parent, text, command, w=100, h=36):
    """Light grey button for secondary actions (+ New, Browse)."""
    return button(parent, text, command, w=w, h=h, fg=colors.ENTRY_BG, hover=colors.BORDER_GRAY,
                  text_color=colors.TEXT_DARK)


def fmt_date(value):
    """Short, readable date (e.g. 'Sep 29, 2026'); passes through anything that isn't a date."""
    if not value:
        return "-"
    return value.strftime("%b %d, %Y") if hasattr(value, "strftime") else str(value)


# Window Layout

def build_sidebar(window, nav_items, on_select, user, on_logout, on_change_password=None, menu_title="MENU"):
    """Navy sidebar with logo, nav buttons, user card and Log Out. Returns {key: nav button}."""
    side = ctk.CTkFrame(window, fg_color=colors.NAVY_DARK, corner_radius=0, width=SIDEBAR_W)
    side.grid(row=0, column=0, sticky="nswe")
    side.pack_propagate(False)
    ctk.CTkFrame(side, fg_color=colors.ACCENT_RED, width=4, height=64, corner_radius=0).place(x=0, y=34)

    logo = os.path.join(ASSETS_DIR, "logo.png")
    if os.path.exists(logo):
        img = Image.open(logo)
        window._logo = ctk.CTkImage(img, img, size=(120, 120))  # keep a reference so it isn't garbage collected
        ctk.CTkLabel(side, image=window._logo, text="").pack(pady=(12, 4))
    label(side, "ICCT Colleges\nFoundation, Inc.", 15, True, "white").pack(pady=(0 if os.path.exists(logo) else 30, 0))
    label(side, "Equipment Borrowing System", 11, color=NAV_TEXT).pack(pady=(2, 6))
    ctk.CTkFrame(side, fg_color=colors.ACCENT_RED, width=50, height=3, corner_radius=2).pack()

    bottom = ctk.CTkFrame(side, fg_color="transparent")
    bottom.pack(side="bottom", fill="x", padx=16, pady=12)
    card = ctk.CTkFrame(bottom, fg_color=NAV_ACTIVE, corner_radius=4)
    card.pack(fill="x", pady=(0, 6))
    label(card, user["full_name"], 13, True, "white", anchor="w", wraplength=SIDEBAR_W - 70,
          justify="left").pack(fill="x", padx=14, pady=(6, 0))
    label(card, user["role"], 11, color=NAV_TEXT, anchor="w").pack(fill="x", padx=14, pady=(0, 0))
    label(card, f"ID: {user['student_number']}", 11, True, "white", anchor="w").pack(fill="x", padx=14, pady=(0, 6))
    if on_change_password:
        button(bottom, "Change Password", on_change_password, w=0, h=32, fg="transparent", hover=NAV_HOVER,
               border_width=1, border_color="#3a4a6b", text_color="white").pack(fill="x")
    button(bottom, "Log Out", on_logout, w=0, h=32, fg=colors.ACCENT_RED, hover=RED_HOVER,
           font=ctk.CTkFont(size=13)).pack(fill="x", pady=(8 if on_change_password else 0, 0))

    nav = ctk.CTkFrame(side, fg_color="transparent")
    nav.pack(fill="x", padx=16, pady=(14, 0))
    label(nav, menu_title, 10, True, "#7f8ba6", anchor="w").pack(fill="x", padx=8, pady=(0, 6))
    buttons = {}
    for key, title in nav_items.items():
        buttons[key] = button(nav, title, lambda k=key: on_select(k), h=32, corner_radius=3,
                              fg="transparent", hover=NAV_HOVER, text_color=NAV_TEXT,
                              anchor="w", font=ctk.CTkFont(size=13))
        buttons[key].pack(fill="x", pady=1)

    return buttons


def build_topbar(parent, stats):
    """Page title on the left, stat boxes on the right. stats = [(key, title, color)].
    Returns (title_label, {key: value_label})."""
    bar = ctk.CTkFrame(parent, fg_color="transparent")
    bar.grid(row=0, column=0, sticky="we", padx=20, pady=(16, 10))
    bar.grid_columnconfigure(0, weight=1)
    title_lbl = label(bar, "", 20, True, anchor="w")
    title_lbl.grid(row=0, column=0, sticky="w")

    box_row = ctk.CTkFrame(bar, fg_color="transparent")
    box_row.grid(row=0, column=1, sticky="e")
    value_lbls = {}
    for key, title, color in stats:
        box = ctk.CTkFrame(box_row, fg_color=colors.CARD_WHITE, corner_radius=4, width=90, height=50)
        box.pack(side="left", padx=(8, 0))
        box.pack_propagate(False)
        value_lbls[key] = label(box, "0", 18, True, color)
        value_lbls[key].pack(pady=(4, 0))
        label(box, title, 11, color=colors.TEXT_GRAY).pack()
    return title_lbl, value_lbls


def build_main(window):
    """Right-hand area: returns (main frame, body frame) with the topbar slot in row 0."""
    main = ctk.CTkFrame(window, fg_color=colors.BG_LIGHT, corner_radius=0)
    main.grid(row=0, column=1, sticky="nswe")
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(1, weight=1)
    body = ctk.CTkFrame(main, fg_color="transparent")
    body.grid(row=1, column=0, sticky="nswe", padx=20, pady=(0, 16))
    body.grid_columnconfigure(0, weight=1)
    body.grid_rowconfigure(0, weight=1)
    return main, body


def show_page(key, pages, nav, title_lbl, titles):
    """Show one page, highlight its nav button and set the page title."""
    for name, page in pages.items():
        page.grid(row=0, column=0, sticky="nswe") if name == key else page.grid_forget()
    for name, btn in nav.items():
        btn.configure(fg_color=NAV_ACTIVE if name == key else "transparent",
                      text_color="white" if name == key else NAV_TEXT)
    title_lbl.configure(text=titles[key])


KINDS = {"blue": (colors.BUTTON_BLUE, colors.BUTTON_BLUE_HOVER), "green": (colors.SUCCESS_GREEN, GREEN_HOVER),
         "red": (colors.ACCENT_RED, RED_HOVER)}
LEFT_COLS = {"Full Name", "Email", "Name", "Category", "Added By", "Borrower", "Equipment", "Approved By"}


def tool_row(bar, left=(), right=(), search=None, pady=(8, 8)):
    """A row of buttons inside a toolbar card. left/right = [(text, command[, kind[, width]])],
    kind = blue / green / red; search = (StringVar, placeholder). Returns the row frame."""
    row = ctk.CTkFrame(bar, fg_color="transparent")
    row.pack(fill="x", pady=pady)
    if search:
        ctk.CTkEntry(row, textvariable=search[0], placeholder_text=search[1], width=240, height=32,
                     corner_radius=3, fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY,
                     text_color=colors.TEXT_DARK).pack(side="left", padx=(10, 8))
    for i, (text, command, *opt) in enumerate(left):
        fg, hover = KINDS[opt[0] if opt else "blue"]
        button(row, text, command, w=opt[1] if len(opt) > 1 else 100, h=32, fg=fg, hover=hover).pack(
            side="left", padx=(10 if i == 0 and not search else 0, 8))
    for i, (text, command) in enumerate(right):
        button(row, text, command, h=32).pack(side="right", padx=(0, 10 if i == 0 else 8))
    return row


def table_page(parent, cols, tags=None):
    """Page with a white toolbar card (row 0) and a styled table card (row 1). Returns (page, toolbar, tree)."""
    page = ctk.CTkFrame(parent, fg_color="transparent")
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(1, weight=1)
    bar = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=4)
    bar.grid(row=0, column=0, sticky="we", pady=(0, 8))
    return page, bar, make_table(page, cols, tags)


# Tables

def setup_table_style():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Admin.Treeview", background=colors.CARD_WHITE, fieldbackground=colors.CARD_WHITE,
                    foreground=colors.TEXT_DARK, rowheight=30, borderwidth=0, relief="flat",
                    font=("Arial", 10))
    style.configure("Admin.Treeview.Heading", background=colors.BG_LIGHT, foreground=colors.TEXT_GRAY,
                    font=("Arial", 9, "bold"), relief="flat", borderwidth=0, padding=(6, 10))
    style.map("Admin.Treeview", background=[("selected", SELECT_BG)],
              foreground=[("selected", colors.TEXT_DARK)])
    style.map("Admin.Treeview.Heading", background=[("active", colors.BG_LIGHT)])
    style.layout("Admin.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


def make_table(page, cols, tags=None):
    """White card with a styled Treeview + scrollbar in row 1. cols = [(heading, min width)]."""
    card = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=4)
    card.grid(row=1, column=0, sticky="nswe")
    card.grid_columnconfigure(0, weight=1)
    card.grid_rowconfigure(0, weight=1)
    tree = ttk.Treeview(card, columns=[c[0] for c in cols], show="headings", style="Admin.Treeview",
                        selectmode="browse")
    for title, width in cols:
        anchor = "w" if title in LEFT_COLS else "center"
        tree.heading(title, text=title.upper(), anchor=anchor)
        tree.column(title, width=width, minwidth=60, stretch=True, anchor=anchor)
    for tag, color in (tags or {}).items():
        tree.tag_configure(tag, foreground=color)
    scroll = ctk.CTkScrollbar(card, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.grid(row=0, column=0, sticky="nswe", padx=(12, 0), pady=12)
    scroll.grid(row=0, column=1, sticky="ns", padx=(4, 6), pady=12)
    return tree


def fill_table(tree, rows, values_of, tag_of=lambda row: (), show_id=False):
    """Replace the table's rows. Each row (a dict with an 'id') becomes (row number, *values_of(row)).
    With show_id=True the first column shows the row's real database id instead of the row number."""
    tree.delete(*tree.get_children())
    for n, row in enumerate(rows, 1):
        tree.insert("", "end", iid=str(row["id"]), values=(row["id"] if show_id else n, *values_of(row)),
                    tags=tag_of(row))


def selected_id(tree, what):
    """Selected row's id, or None after telling the user to pick one."""
    if not tree.selection():
        messagebox.showinfo("No selection", f"Please select {what} first.")
        return None
    return tree.selection()[0]


# Auth screens (login / register / forgot password)

def link(parent, text, command, size=12, bold=True, w=20, **kw):
    """Flat blue text button, e.g. 'Forgot password?'."""
    return ctk.CTkButton(parent, text=text, command=command, width=w, fg_color="transparent", hover=False,
                         text_color=colors.LINK_BLUE,
                         font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"), **kw)


class AuthWindow(ctk.CTk):
    """Navy left panel + white card on the right. Put your widgets in self.card.
    height = window height, card_h = card height, scroll = make the card scrollable."""

    def __init__(self, title, height, card_h, scroll=False):
        super().__init__()
        self.title(f"ICCT Colleges Foundation, Inc. - {title}")
        self.geometry(f"973x{height}")
        self.resizable(False, False)
        self.configure(fg_color=colors.BG_LIGHT)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        build_left_panel(self, height=height).grid(row=0, column=0, sticky="nswe")

        right = ctk.CTkFrame(self, fg_color=colors.BG_LIGHT, corner_radius=0)
        right.grid(row=0, column=1, sticky="nswe")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        if scroll:
            self.card = ctk.CTkScrollableFrame(
                right, fg_color=colors.CARD_WHITE, corner_radius=12, width=380, height=card_h,
                scrollbar_button_color=colors.BORDER_GRAY, scrollbar_fg_color=colors.CARD_WHITE)
            self.card.grid(row=0, column=0, pady=18)
        else:
            self.card = ctk.CTkFrame(right, fg_color=colors.CARD_WHITE, corner_radius=12, width=380, height=card_h)
            self.card.grid(row=0, column=0)
            self.card.grid_propagate(False)

    def open_login(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()


class Fields:
    """Builds the repeated rows of an auth card. pad_x = left padding, h = input height, gap = space above labels."""

    def __init__(self, card, pad_x, h=36, gap=16):
        self.card, self.pad_x, self.h, self.gap = card, pad_x, h, gap

    def place(self, widget, pady=0):
        """Pack any widget into the card with the card's left padding; returns the widget."""
        widget.pack(anchor="w", padx=self.pad_x, pady=pady)
        return widget

    def label(self, text, gap=None):
        return self.place(label(self.card, text, 13, True), (self.gap if gap is None else gap, 4))

    def input(self, parent, placeholder, width, **kw):
        return ctk.CTkEntry(parent, placeholder_text=placeholder, width=width, height=self.h,
                            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY,
                            text_color=colors.TEXT_DARK, **kw)

    title = label  # same as label(); used by the pop-up forms

    def entry(self, text, placeholder, gap=None):
        self.label(text, gap)
        return self.place(self.input(self.card, placeholder, 300))

    def menu(self, text, values, variable, command=None):
        """Labelled dropdown. Returns the option menu."""
        self.label(text)
        return self.place(ctk.CTkOptionMenu(self.card, values=values, variable=variable, width=300,
                                            command=command))

    def password(self, text, placeholder, gap=None):
        """Password entry with a Show/Hide button. Returns the entry."""
        self.label(text, gap)
        row = self.place(ctk.CTkFrame(self.card, fg_color="transparent"))
        entry = self.input(row, placeholder, 245, show="*")
        entry.pack(side="left")

        def toggle():
            hidden = entry.cget("show") == "*"
            entry.configure(show="" if hidden else "*")
            btn.configure(text="Hide" if hidden else "Show")

        btn = ctk.CTkButton(row, text="Show", width=48, height=self.h, corner_radius=3, fg_color=colors.ENTRY_BG,
                            hover_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK, command=toggle)
        btn.pack(side="left", padx=(6, 0))
        return entry

    def date(self, text, min_date=None, initial=None, gap=None):
        """Labelled date field that opens a calendar (no typing). Returns the DatePicker; .get() gives YYYY-MM-DD."""
        self.label(text, gap)
        return self.place(DatePicker(self.card, width=300, height=self.h, min_date=min_date, initial=initial))

    def error(self, pady=(8, 0)):
        return self.place(ctk.CTkLabel(self.card, text="", text_color=colors.ACCENT_RED, font=ctk.CTkFont(size=12),
                                       wraplength=300, justify="left"), pady)

    def submit(self, text, command, h=40, pady=(14, 10)):
        return self.place(button(self.card, text, command, w=300, h=h,
                                 font=ctk.CTkFont(size=14, weight="bold")), pady)


class DatePicker(ctk.CTkFrame):
    """A date field that opens a small month calendar instead of making the user type.
    get() returns 'YYYY-MM-DD' (or '' when nothing is picked); days before min_date cannot be chosen."""

    DISABLED_TEXT = "#b4bac4"

    def __init__(self, parent, width=300, height=34, min_date=None, initial=None, placeholder="Select a date"):
        super().__init__(parent, width=width, height=height, fg_color=colors.ENTRY_BG, border_width=2,
                         border_color=colors.BORDER_GRAY, corner_radius=6)
        self.pack_propagate(False)
        self.min_date, self.value, self.popup = min_date, None, None
        self.placeholder = placeholder
        self.text = ctk.CTkLabel(self, text=placeholder, anchor="w", text_color=colors.TEXT_GRAY,
                                 font=ctk.CTkFont(size=13))
        self.text.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.arrow = ctk.CTkButton(self, text="\u25be", width=36, corner_radius=4, fg_color=colors.BUTTON_BLUE,
                                   hover_color=colors.BUTTON_BLUE_HOVER, command=self.toggle)
        self.arrow.pack(side="right", fill="y", padx=3, pady=3)
        for w in (self, self.text):
            w.bind("<Button-1>", lambda _e: self.toggle())
        self.winfo_toplevel().bind("<Button-1>", self._on_outside_click, add="+")  # click elsewhere closes it
        if initial:
            self.set(initial)

    # value

    def get(self):
        return self.value.isoformat() if self.value else ""

    def clear(self):
        """Forget the picked date and show the placeholder again."""
        self.value = None
        self.text.configure(text=self.placeholder, text_color=colors.TEXT_GRAY)

    def set(self, value):
        """Accepts a date or a 'YYYY-MM-DD' string; anything unreadable is ignored."""
        if isinstance(value, datetime):
            value = value.date()
        elif isinstance(value, str):
            try:
                value = datetime.strptime(value.strip(), "%Y-%m-%d").date()
            except ValueError:
                return
        if not isinstance(value, date):
            return
        self.value = value
        self.text.configure(text=value.strftime("%b %d, %Y"), text_color=colors.TEXT_DARK)

    # popup calendar

    def toggle(self):
        self.close() if self.popup else self.open()

    def open(self):
        start = self.value or max(date.today(), self.min_date or date.today())
        self.view_year, self.view_month = start.year, start.month
        self.popup = tk.Toplevel(self)
        self.popup.overrideredirect(True)
        try:
            self.popup.attributes("-topmost", True)  # stay above the dialog
        except tk.TclError:
            pass
        self.popup.configure(bg=colors.CARD_WHITE, highlightthickness=1, highlightbackground=colors.BORDER_GRAY)
        self.popup.bind("<Escape>", lambda _e: self.close())
        self._render()

    def close(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def _on_outside_click(self, event):
        if self.popup and not str(event.widget).startswith(str(self)):
            self.close()

    def _shift(self, months):
        index = self.view_year * 12 + self.view_month - 1 + months
        self.view_year, self.view_month = index // 12, index % 12 + 1
        self._render()

    def _pick(self, chosen):
        self.set(chosen)
        self.close()

    def _render(self):
        pop, year, month = self.popup, self.view_year, self.view_month
        for w in pop.winfo_children():
            w.destroy()
        box = ctk.CTkFrame(pop, fg_color=colors.CARD_WHITE, corner_radius=0)
        box.pack(padx=10, pady=10)

        can_prev = not self.min_date or (year, month) > (self.min_date.year, self.min_date.month)
        nav = dict(width=30, height=28, corner_radius=4, fg_color=colors.ENTRY_BG, hover_color=colors.BORDER_GRAY,
                   text_color=colors.TEXT_DARK, text_color_disabled=self.DISABLED_TEXT)
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkButton(head, text="\u2039", command=lambda: self._shift(-1),
                      state="normal" if can_prev else "disabled", **nav).pack(side="left")
        ctk.CTkButton(head, text="\u203a", command=lambda: self._shift(1), **nav).pack(side="right")
        label(head, f"{calendar.month_name[month]} {year}", 13, True).pack(expand=True)

        grid = ctk.CTkFrame(box, fg_color="transparent")
        grid.pack(pady=(8, 0))
        for c, name in enumerate(("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa")):
            label(grid, name, 11, True, colors.TEXT_GRAY, width=36).grid(row=0, column=c, pady=(0, 2))
        today = date.today()
        for r, week in enumerate(calendar.Calendar(firstweekday=6).monthdayscalendar(year, month), 1):
            for c, day in enumerate(week):
                if not day:
                    continue
                d = date(year, month, day)
                off, picked = bool(self.min_date and d < self.min_date), d == self.value
                ctk.CTkButton(grid, text=str(day), width=36, height=30, corner_radius=4,
                              fg_color=colors.BUTTON_BLUE if picked else "transparent",
                              hover_color=colors.BUTTON_BLUE_HOVER if picked else SELECT_BG,
                              text_color="white" if picked else colors.TEXT_DARK,
                              text_color_disabled=self.DISABLED_TEXT, state="disabled" if off else "normal",
                              border_width=1 if d == today and not picked else 0, border_color=colors.ACCENT_RED,
                              command=lambda d=d: self._pick(d)).grid(row=r, column=c, padx=1, pady=1)
        self._position()

    def _position(self):
        """Put the calendar just under the field, or above it when there is no room below."""
        pop = self.popup
        pop.update_idletasks()
        x, y = self.winfo_rootx(), self.winfo_rooty() + self.winfo_height() + 2
        if y + pop.winfo_reqheight() > pop.winfo_screenheight() - 40:
            y = self.winfo_rooty() - pop.winfo_reqheight() - 2
        pop.geometry(f"+{x}+{max(y, 0)}")
        pop.lift()


class FormDialog(ctk.CTkToplevel):
    """Pop-up form: heading, fields via self.f, then footer() adds the status line + submit/Cancel buttons."""

    def __init__(self, parent, title, size):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        w, h = map(int, size.split("x"))
        h = min(h, int((self.winfo_screenheight() - 120) / self._get_window_scaling()))  # keep buttons on screen
        self.geometry(f"{w}x{h}")
        self.resizable(False, False)
        self.configure(fg_color=colors.CARD_WHITE)
        self.transient(parent)
        self.after(150, lambda: (self.lift(), self.focus_force(), self.grab_set()))  # grab once visible
        self.f = Fields(self, 30, h=34, gap=10)
        self.heading = label(self, title, 20, True)
        self.heading.pack(anchor="w", padx=30, pady=(16, 4))

    def footer(self, text, command, status_pady=(12, 0)):
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(side="bottom", fill="x", before=self.heading)  # packed first, so it is never cut off
        ff = Fields(foot, 30)
        self.status = ff.error(status_pady)
        self.submit_btn = ff.submit(text, command, pady=(12, 6))
        ff.place(button(foot, "Cancel", self.destroy, w=300, h=32, fg="transparent",
                        hover=colors.BG_LIGHT, text_color=colors.TEXT_GRAY), (0, 12))

    def show(self, message, ok=False):
        self.status.configure(text=message, text_color=colors.SUCCESS_GREEN if ok else colors.ACCENT_RED)

    def result(self, ok, message, refresh=None, delay=1200):
        """Show the outcome; on success refresh the parent list and close after `delay` ms."""
        self.show(message, ok)
        if ok:
            self.submit_btn.configure(state="disabled")
            if refresh:
                refresh()
            self.after(delay, self.destroy)


class VerifyMixin:
    """Email verification (send code / enter code) for Register and Forgot Password.
    The window needs self.email_entry and self.error_label, and a Fields helper to build the section."""
    must_exist = True  # True: email must already be registered (reset). False: must be new (register).

    def verify_section(self, f, verify_text, send_h=32):
        f.place(button(f.card, "Send Verification Code", self.handle_send_code, w=300, h=send_h,
                       fg=colors.ENTRY_BG, hover=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
                       font=ctk.CTkFont(size=12, weight="bold")), (8, 0))
        f.label("Verification Code")
        row = f.place(ctk.CTkFrame(f.card, fg_color="transparent"))
        self.code_var = ctk.StringVar()
        self._last_auto_checked_code = None
        self.code_var.trace_add("write", self._on_code_changed)
        self.code_entry = f.input(row, "6-digit code", 210, textvariable=self.code_var)
        self.code_entry.pack(side="left")
        button(row, verify_text, self.handle_verify_code, w=84, h=f.h).pack(side="left", padx=(6, 0))
        self.verify_status_label = f.place(
            label(f.card, "Email not verified yet.", 11, color=colors.TEXT_GRAY, wraplength=300, justify="left"), (4, 0))

    def _status(self, text, color=colors.TEXT_GRAY):
        self.verify_status_label.configure(text=text, text_color=color)

    def handle_send_code(self):
        email = self.email_entry.get().strip().lower()
        if not auth.is_valid_email(email):
            return self.error_label.configure(text="Please enter a valid email address first.")
        if bool(auth.email_exists(email)) != self.must_exist:
            return self.error_label.configure(text="No account found with that email address."
                                              if self.must_exist else "This email is already registered.")
        self.error_label.configure(text="")
        self._status("Sending code...")

        def worker():
            try:
                email_service.send_and_store_code(email)
                self._status(f"Code sent to {email}. Check your inbox.")
            except email_service.CodeRequestError as exc:
                self._status(str(exc), colors.ACCENT_RED)
            except Exception:  # don't show mail-server details to the user
                self._status("Could not send the email. Please try again later.", colors.ACCENT_RED)

        threading.Thread(target=worker, daemon=True).start()

    def _on_code_changed(self, *_):
        """Auto verify the moment a 6-digit code has been typed or pasted in."""
        code = self.code_var.get().strip()
        if len(code) == 6 and code.isdigit() and code != self._last_auto_checked_code:
            self._last_auto_checked_code = code
            self.handle_verify_code()

    def handle_verify_code(self):
        code = self.code_entry.get().strip()
        if not code:
            return self.error_label.configure(text="Please enter the verification code.")
        ok, message = email_service.verify_code(self.email_entry.get().strip().lower(), code)
        self.error_label.configure(text="" if ok else message)
        self._status(message, colors.SUCCESS_GREEN if ok else colors.ACCENT_RED)

    def done(self, message, next_step):
        """Show a success message, then run next_step (for example: open the login screen) after 1.5 s."""
        self.error_label.configure(text="")
        self._status(message, colors.SUCCESS_GREEN)
        self.after(1500, next_step)
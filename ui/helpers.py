#This help both dashboard ui
import os
import customtkinter as ctk
from tkinter import messagebox, ttk
from PIL import Image

from ui import colors
from ui.left_panel import ASSETS_DIR

SIDEBAR_W, NAV_TEXT, NAV_ACTIVE, NAV_HOVER = 250, "#c7cede", "#1f3357", "#1a2b49"
RED_HOVER, GREEN_HOVER, SELECT_BG, AMBER = "#b52a48", "#166838", "#dbe4f3", "#b7791f"


# small widgets

def label(parent, text, size=12, bold=False, color=colors.TEXT_DARK, **kw):
    font = ctk.CTkFont(size=size, weight="bold" if bold else "normal")
    return ctk.CTkLabel(parent, text=text, font=font, text_color=color, **kw)


def button(parent, text, command, w=100, h=36, fg=colors.BUTTON_BLUE, hover=colors.BUTTON_BLUE_HOVER, **kw):
    return ctk.CTkButton(parent, text=text, command=command, width=w, height=h,
                         fg_color=fg, hover_color=hover, **kw)


def fmt_date(value):
    """Short, readable date (e.g. 'Sep 29, 2026'); passes through anything that isn't a date."""
    if not value:
        return "-"
    return value.strftime("%b %d, %Y") if hasattr(value, "strftime") else str(value)


# Window Layout

def build_sidebar(window, nav_items, on_select, user, on_logout, on_change_password=None):
    """Navy sidebar with logo, nav buttons, user card and Log Out. Returns {key: nav button}."""
    side = ctk.CTkFrame(window, fg_color=colors.NAVY_DARK, corner_radius=0, width=SIDEBAR_W)
    side.grid(row=0, column=0, sticky="nswe")
    side.pack_propagate(False)
    ctk.CTkFrame(side, fg_color=colors.ACCENT_RED, width=4, height=64, corner_radius=0).place(x=0, y=34)

    logo = os.path.join(ASSETS_DIR, "logo.png")
    if os.path.exists(logo):
        img = Image.open(logo)
        window._logo = ctk.CTkImage(img, img, size=(84, 84))  # keep a reference so it isn't garbage collected
        ctk.CTkLabel(side, image=window._logo, text="").pack(pady=(26, 10))
    label(side, "ICCT Colleges\nFoundation, Inc.", 15, True, "white").pack(pady=(0 if os.path.exists(logo) else 30, 0))
    label(side, "Equipment Borrowing System", 11, color=NAV_TEXT).pack(pady=(4, 10))
    ctk.CTkFrame(side, fg_color=colors.ACCENT_RED, width=50, height=3, corner_radius=2).pack()

    nav = ctk.CTkFrame(side, fg_color="transparent")
    nav.pack(fill="x", padx=16, pady=(30, 0))
    label(nav, "MENU", 10, True, "#7f8ba6", anchor="w").pack(fill="x", padx=8, pady=(0, 6))
    buttons = {}
    for key, title in nav_items.items():
        buttons[key] = button(nav, title, lambda k=key: on_select(k), h=40, corner_radius=8,
                              fg="transparent", hover=NAV_HOVER, text_color=NAV_TEXT,
                              anchor="w", font=ctk.CTkFont(size=13, weight="bold"))
        buttons[key].pack(fill="x", pady=2)

    bottom = ctk.CTkFrame(side, fg_color="transparent")
    bottom.pack(side="bottom", fill="x", padx=16, pady=18)
    card = ctk.CTkFrame(bottom, fg_color=NAV_ACTIVE, corner_radius=10)
    card.pack(fill="x", pady=(0, 10))
    label(card, user["full_name"], 13, True, "white", anchor="w", wraplength=SIDEBAR_W - 70,
          justify="left").pack(fill="x", padx=14, pady=(10, 0))
    label(card, user["role"], 11, color=NAV_TEXT, anchor="w").pack(fill="x", padx=14, pady=(0, 10))
    if on_change_password:
        button(bottom, "Change Password", on_change_password, w=0, fg="transparent", hover=NAV_HOVER,
               border_width=1, border_color="#3a4a6b", text_color="white").pack(fill="x")
    button(bottom, "Log Out", on_logout, w=0, fg=colors.ACCENT_RED, hover=RED_HOVER,
           font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", pady=(8 if on_change_password else 0, 0))
    return buttons


def build_topbar(parent, stats):
    """Page title on the left, stat boxes on the right. stats = [(key, title, color)].
    Returns (title_label, {key: value_label})."""
    bar = ctk.CTkFrame(parent, fg_color="transparent")
    bar.grid(row=0, column=0, sticky="we", padx=28, pady=(24, 14))
    bar.grid_columnconfigure(0, weight=1)
    title_lbl = label(bar, "", 24, True, anchor="w")
    title_lbl.grid(row=0, column=0, sticky="w")

    box_row = ctk.CTkFrame(bar, fg_color="transparent")
    box_row.grid(row=0, column=1, sticky="e")
    value_lbls = {}
    for key, title, color in stats:
        box = ctk.CTkFrame(box_row, fg_color=colors.CARD_WHITE, corner_radius=10, width=96, height=58)
        box.pack(side="left", padx=(8, 0))
        box.pack_propagate(False)
        value_lbls[key] = label(box, "0", 20, True, color)
        value_lbls[key].pack(pady=(6, 0))
        label(box, title, 11, color=colors.TEXT_GRAY).pack()
    return title_lbl, value_lbls


def build_main(window):
    """Right-hand area: returns (main frame, body frame) with the topbar slot in row 0."""
    main = ctk.CTkFrame(window, fg_color=colors.BG_LIGHT, corner_radius=0)
    main.grid(row=0, column=1, sticky="nswe")
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(1, weight=1)
    body = ctk.CTkFrame(main, fg_color="transparent")
    body.grid(row=1, column=0, sticky="nswe", padx=28, pady=(0, 24))
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


def tool_row(bar, left=(), right=(), search=None, pady=(12, 12)):
    """A row of buttons inside a toolbar card. left/right = [(text, command[, kind[, width]])],
    kind = blue / green / red; search = (StringVar, placeholder). Returns the row frame."""
    row = ctk.CTkFrame(bar, fg_color="transparent")
    row.pack(fill="x", pady=pady)
    if search:
        ctk.CTkEntry(row, textvariable=search[0], placeholder_text=search[1], width=260, height=36,
                     fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY,
                     text_color=colors.TEXT_DARK).pack(side="left", padx=(14, 10))
    for i, (text, command, *opt) in enumerate(left):
        fg, hover = KINDS[opt[0] if opt else "blue"]
        button(row, text, command, w=opt[1] if len(opt) > 1 else 100, fg=fg, hover=hover).pack(
            side="left", padx=(14 if i == 0 and not search else 0, 12))
    for i, (text, command) in enumerate(right):
        button(row, text, command).pack(side="right", padx=(0, 14 if i == 0 else 12))
    return row


def table_page(parent, cols, tags=None):
    """Page with a white toolbar card (row 0) and a styled table card (row 1). Returns (page, toolbar, tree)."""
    page = ctk.CTkFrame(parent, fg_color="transparent")
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(1, weight=1)
    bar = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=10)
    bar.grid(row=0, column=0, sticky="we", pady=(0, 12))
    return page, bar, make_table(page, cols, tags)


# Tables

def setup_table_style():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Admin.Treeview", background=colors.CARD_WHITE, fieldbackground=colors.CARD_WHITE,
                    foreground=colors.TEXT_DARK, rowheight=40, borderwidth=0, relief="flat",
                    font=("Segoe UI", 10))
    style.configure("Admin.Treeview.Heading", background=colors.BG_LIGHT, foreground=colors.TEXT_GRAY,
                    font=("Segoe UI", 9, "bold"), relief="flat", borderwidth=0, padding=(6, 10))
    style.map("Admin.Treeview", background=[("selected", SELECT_BG)],
              foreground=[("selected", colors.TEXT_DARK)])
    style.map("Admin.Treeview.Heading", background=[("active", colors.BG_LIGHT)])
    style.layout("Admin.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


def make_table(page, cols, tags=None):
    """White card with a styled Treeview + scrollbar in row 1. cols = [(heading, min width)]."""
    card = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=12)
    card.grid(row=1, column=0, sticky="nswe")
    card.grid_columnconfigure(0, weight=1)
    card.grid_rowconfigure(0, weight=1)
    tree = ttk.Treeview(card, columns=[c[0] for c in cols], show="headings", style="Admin.Treeview",
                        selectmode="browse")
    for title, width in cols:
        tree.heading(title, text=title.upper())
        tree.column(title, width=width, minwidth=60, stretch=True, anchor="w" if title in LEFT_COLS else "center")
    for tag, color in (tags or {}).items():
        tree.tag_configure(tag, foreground=color)
    scroll = ctk.CTkScrollbar(card, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.grid(row=0, column=0, sticky="nswe", padx=(12, 0), pady=12)
    scroll.grid(row=0, column=1, sticky="ns", padx=(4, 6), pady=12)
    return tree


def fill_table(tree, rows, values_of, tag_of=lambda row: ()):
    """Replace the table's rows. Each row (a dict with an 'id') becomes (row number, *values_of(row))."""
    tree.delete(*tree.get_children())
    for n, row in enumerate(rows, 1):
        tree.insert("", "end", iid=str(row["id"]), values=(n, *values_of(row)), tags=tag_of(row))


def selected_id(tree, what):
    """Selected row's id, or None after telling the user to pick one."""
    if not tree.selection():
        messagebox.showinfo("No selection", f"Please select {what} first.")
        return None
    return tree.selection()[0]
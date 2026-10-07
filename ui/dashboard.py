"""Student / Teacher dashboard (navy sidebar + light content area), built on ui.helpers."""
import os
from collections import Counter

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

from services import borrow_service, equipment_service
from ui import colors
from ui.helpers import (AMBER, NAV_ACTIVE, NAV_HOVER, NAV_TEXT, RED_HOVER, button, fill_table, fmt_date, label,
                        make_table, selected_id, setup_table_style, tool_row)
from ui.left_panel import ASSETS_DIR

PAGES = {"catalog": "Equipment Catalog", "requests": "My Requests", "history": "Borrowing History"}
SUBTITLES = {"catalog": "Pick equipment and send a borrow request.",
             "requests": "Your requests. Select an active one to return it.",
             "history": "Equipment you have already returned."}
STATUS_TINTS = {"Pending": "#fdf3df", "Active": "#e3f4ea", "Overdue": "#fbe4ea", "Returned": "#e4eaf6",
                "Denied": "#eceef2"}
CHIP_STATUSES = ("Pending", "Active", "Overdue", "Returned", "Denied")  # the counters shown in the banner
CATALOG_COLS = 3
STATUS_COLORS = {"Pending": AMBER, "Active": colors.SUCCESS_GREEN, "Overdue": colors.ACCENT_RED,
                 "Returned": colors.BUTTON_BLUE, "Denied": colors.TEXT_GRAY,
                 "Cancelled": colors.TEXT_GRAY}


def display_status(row):
    """Status shown to the borrower. An approved borrowing is Active, or Overdue once it is past its due date."""
    if row["status"] == "Approved":
        return "Overdue" if row["state"] == "Overdue" else "Active"
    return row["status"]
HISTORY_COLS = [("ID", 50), ("Equipment", 220), ("Borrow Date", 110), ("Due Date", 110),
                ("Return Date", 110), ("Status", 90), ("Condition", 100)]
REQUEST_COLS = [("ID", 50), ("Equipment", 190), ("Qty", 50), ("Status", 90),
                ("Requested", 110), ("Due Date", 100), ("Approved By", 120), ("Note", 170)]


class DashboardWindow(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user, self._imgs, self._items = user, [], []
        self.title("ICCT Colleges Foundation, Inc. - Equipment Borrowing System")
        self.geometry("1150x700")
        self.minsize(980, 620)
        self.configure(fg_color=colors.BG_LIGHT)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        setup_table_style()

        self._build_navbar()
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nswe", padx=28, pady=(0, 16))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)
        self._build_welcome(content)
        body = ctk.CTkFrame(content, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nswe")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.pages = {"catalog": self._build_catalog(body), "requests": self._build_requests(body),
                      "history": self._build_history(body)}
        self.show_page("catalog")
        if user.get("must_change_password"):
            self.after(600, self.prompt_password_change)

    # ---------- layout: top navigation bar + welcome banner ----------

    def _build_navbar(self):
        bar = ctk.CTkFrame(self, fg_color=colors.NAVY_DARK, corner_radius=0, height=112)
        bar.grid(row=0, column=0, sticky="we")
        bar.grid_propagate(False)
        bar.grid_rowconfigure(0, weight=1)
        bar.grid_columnconfigure(1, weight=1)

        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w", padx=(20, 10))
        logo = os.path.join(ASSETS_DIR, "logo.png")
        if os.path.exists(logo):
            img = Image.open(logo)
            self._logo = ctk.CTkImage(img, img, size=(92, 92))  # keep a reference so it isn't garbage collected
            ctk.CTkLabel(brand, image=self._logo, text="").pack(side="left", padx=(0, 10))
        label(brand, "ICCT Equipment\nBorrowing System", 13, True, "white", justify="left").pack(side="left")

        tabs = ctk.CTkFrame(bar, fg_color="transparent")
        tabs.grid(row=0, column=1, sticky="nsw", padx=20)
        self.nav, self._underlines = {}, {}
        for key, title in PAGES.items():
            cell = ctk.CTkFrame(tabs, fg_color="transparent")
            cell.pack(side="left", fill="y", padx=4)
            self._underlines[key] = ctk.CTkFrame(cell, fg_color="transparent", height=3, corner_radius=0)
            self._underlines[key].pack(side="bottom", fill="x")
            self.nav[key] = button(cell, title, lambda k=key: self.show_page(k), w=130, h=40, fg="transparent",
                                   hover=NAV_HOVER, text_color=NAV_TEXT, font=ctk.CTkFont(size=13, weight="bold"))
            self.nav[key].pack(side="top", expand=True)

        who = ctk.CTkFrame(bar, fg_color="transparent")
        who.grid(row=0, column=2, sticky="e", padx=(0, 20))
        info = ctk.CTkFrame(who, fg_color="transparent")
        info.pack(side="left", padx=(0, 14))
        label(info, self.user["full_name"], 13, True, "white", anchor="e").pack(anchor="e")
        label(info, self.user["role"], 11, color=NAV_TEXT, anchor="e").pack(anchor="e")
        label(info, f"ID: {self.user['student_number']}", 11, True, "white", anchor="e").pack(anchor="e")
        button(who, "Change Password", self.open_change_password, w=130, h=32, fg="transparent", hover=NAV_HOVER,
               border_width=1, border_color="#3a4a6b", text_color="white").pack(side="left", padx=(0, 8))
        button(who, "Log Out", self.logout, w=90, h=32, fg=colors.ACCENT_RED, hover=RED_HOVER).pack(side="left")

    def _build_welcome(self, parent):
        """Greeting card with the borrower's request counts shown as colored chips."""
        banner = ctk.CTkFrame(parent, fg_color=colors.CARD_WHITE, corner_radius=8)
        banner.grid(row=0, column=0, sticky="we", pady=(18, 12))
        banner.grid_columnconfigure(0, weight=1)
        text = ctk.CTkFrame(banner, fg_color="transparent")
        text.grid(row=0, column=0, sticky="w", padx=20, pady=14)
        first_name = (self.user["full_name"].split() or ["there"])[0]
        label(text, f"Welcome, {first_name}", 22, True, anchor="w").pack(anchor="w")
        self.title_lbl = label(text, "", 12, color=colors.TEXT_GRAY, anchor="w")
        self.title_lbl.pack(anchor="w", pady=(2, 0))

        chips = ctk.CTkFrame(banner, fg_color="transparent")
        chips.grid(row=0, column=1, sticky="e", padx=16)
        self.stat_lbls = {}
        for status in CHIP_STATUSES:
            color = STATUS_COLORS[status]
            chip = ctk.CTkFrame(chips, fg_color=STATUS_TINTS[status], corner_radius=8, width=88, height=58)
            chip.pack(side="left", padx=4)
            chip.pack_propagate(False)
            self.stat_lbls[status] = label(chip, "0", 19, True, color)
            self.stat_lbls[status].pack(pady=(7, 0))
            label(chip, status, 11, color=colors.TEXT_GRAY).pack()

    def show_page(self, key):
        for name, page in self.pages.items():
            page.grid(row=0, column=0, sticky="nswe") if name == key else page.grid_forget()
        for name, btn in self.nav.items():
            active = name == key
            btn.configure(text_color="white" if active else NAV_TEXT)
            self._underlines[name].configure(fg_color=colors.ACCENT_RED if active else "transparent")
        self.title_lbl.configure(text=SUBTITLES[key])

    # ---------- Equipment Catalog ----------

    def _build_catalog(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=4)
        bar.grid(row=0, column=0, sticky="we", pady=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.render_catalog())
        self.category_var = ctk.StringVar(value="All")
        row = tool_row(bar, right=[("Refresh", self.load_catalog)], search=(self.search_var, "Search equipment..."))
        label(row, "Category:", color=colors.TEXT_GRAY).pack(side="left", padx=(8, 6))
        self.category_menu = ctk.CTkOptionMenu(
            row, values=["All"] + equipment_service.get_category_names(), variable=self.category_var,
            width=170, height=32, corner_radius=3, fg_color=colors.ENTRY_BG, button_color=colors.BUTTON_BLUE,
            button_hover_color=colors.BUTTON_BLUE_HOVER, text_color=colors.TEXT_DARK,
            command=lambda _: self.render_catalog())
        self.category_menu.pack(side="left")

        self.catalog_frame = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        self.catalog_frame.grid(row=1, column=0, sticky="nswe")
        for c in range(CATALOG_COLS):
            self.catalog_frame.grid_columnconfigure(c, weight=1, uniform="catalog")
        self.load_catalog()
        return page

    def load_catalog(self):
        # Refresh the category list too, so categories added by an admin appear without a restart.
        names = ["All"] + equipment_service.get_category_names()
        self.category_menu.configure(values=names)
        if self.category_var.get() not in names:
            self.category_var.set("All")
        self._items = [(i, borrow_service.get_available_quantity(i["id"]))
                       for i in equipment_service.get_all_equipment()]
        self.render_catalog()

    def render_catalog(self):
        for w in self.catalog_frame.winfo_children():
            w.destroy()
        self._imgs.clear()
        cat, query = self.category_var.get(), self.search_var.get().strip().lower()
        rows = [(i, a) for i, a in self._items if cat in ("All", i["category"]) and query in i["name"].lower()]
        if not rows:
            label(self.catalog_frame, "No equipment found.", 13, color=colors.TEXT_GRAY).grid(
                row=0, column=0, columnspan=CATALOG_COLS, pady=20)
        for n, (item, available) in enumerate(rows):
            self._item_card(item, available, n)

    def _item_card(self, item, available, n):
        """One equipment card in the catalog grid: photo on top, details, availability, Request button."""
        ok = available > 0
        color, tint = (colors.SUCCESS_GREEN, "#e3f4ea") if ok else (colors.ACCENT_RED, "#fbe4ea")
        card = ctk.CTkFrame(self.catalog_frame, fg_color=colors.CARD_WHITE, corner_radius=8)
        card.grid(row=n // CATALOG_COLS, column=n % CATALOG_COLS, sticky="nsew", padx=6, pady=6)

        thumb = label(card, "No Photo", 12, color=colors.TEXT_GRAY, fg_color=colors.ENTRY_BG, height=130,
                      corner_radius=6)
        try:
            path = equipment_service.get_photo_full_path(item["photo_path"])
            if path:
                img = Image.open(path)
                img.thumbnail((240, 130))
                self._imgs.append(ctk.CTkImage(img, img, size=img.size))
                thumb.configure(image=self._imgs[-1], text="")
        except Exception:
            pass  # fall back to the "No Photo" placeholder
        thumb.pack(fill="x", padx=10, pady=(10, 0))

        label(card, item["name"], 15, True, anchor="w", wraplength=230, justify="left").pack(
            fill="x", padx=14, pady=(10, 0))
        label(card, f"{item['category']} - {item['condition_status']}", 12, color=colors.TEXT_GRAY,
              anchor="w").pack(fill="x", padx=14, pady=(2, 8))
        label(card, f"{available} available" if ok else "Out of stock", 12, True, color, fg_color=tint,
              corner_radius=4, height=26).pack(fill="x", padx=14)
        button(card, "Request", lambda: self.open_request_dialog(item, available), h=34,
               font=ctk.CTkFont(size=13, weight="bold"), state="normal" if ok else "disabled").pack(
            fill="x", padx=14, pady=(10, 14))

    def open_request_dialog(self, item, available):
        from ui.borrow import RequestEquipmentDialog
        RequestEquipmentDialog(self, self.user, item, available,
                               on_success=lambda: (self.load_catalog(), self.load_my_requests()))

    # ---------- My Requests ----------

    def _build_requests(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=4)
        bar.grid(row=0, column=0, sticky="we", pady=(0, 8))
        tool_row(bar, left=[("Return Equipment", self.return_selected, "green", 150),
                            ("Cancel Request", self.cancel_selected, "red", 130),
                            ("Refresh", self.load_my_requests)])
        self.req_tree = make_table(page, REQUEST_COLS, tags=STATUS_COLORS)
        self.load_my_requests()
        return page

    def load_my_requests(self):
        rows = borrow_service.get_requests_for_user(self.user["id"])
        fill_table(self.req_tree, rows,
                   lambda r: (r["equipment_name"], r["quantity"], display_status(r), fmt_date(r["request_date"]),
                              fmt_date(r["due_date"]), r["approved_by_name"] or "-",
                              (r.get("deny_reason") if r["status"] == "Denied" else r.get("purpose")) or "-"),
                   lambda r: (display_status(r),))
        counts = Counter(display_status(r) for r in rows)
        for status, lbl in self.stat_lbls.items():
            lbl.configure(text=str(counts[status]))

    def cancel_selected(self):
        """The borrower withdraws one of their own pending requests."""
        rid = selected_id(self.req_tree, "a pending request")
        if not rid:
            return
        if not messagebox.askyesno("Cancel Request", "Cancel this request?"):
            return
        ok, msg = borrow_service.cancel_request(int(rid), self.user["id"])
        (messagebox.showinfo if ok else messagebox.showerror)("Cancel Request" if ok else "Not Allowed", msg)
        self.load_my_requests()
        self.load_catalog()

    def return_selected(self):
        """The borrower selects one of their active borrowings and returns it."""
        tid = selected_id(self.req_tree, "an active borrowing")
        if not tid:
            return
        txn = borrow_service.get_request_by_id(int(tid))
        if not txn or txn["user_id"] != self.user["id"] or txn["status"] != "Approved":
            messagebox.showinfo("Not Available", "Only your active borrowings can be returned.")
            self.load_my_requests()
            return
        from ui.borrow import ReturnDialog
        ReturnDialog(self, self.user, txn, on_success=lambda: (
            self.load_my_requests(), self.load_catalog(), self.load_history()))

    # ---------- Borrowing History ----------

    def _build_history(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=4)
        bar.grid(row=0, column=0, sticky="we", pady=(0, 8))
        tool_row(bar, left=[("Refresh", self.load_history)])
        self.history_tree = make_table(page, HISTORY_COLS)
        self.load_history()
        return page

    def load_history(self):
        """The borrower's own completed (returned) borrowings."""
        rows = borrow_service.get_borrower_history(self.user["id"], returned_only=True)
        fill_table(self.history_tree, rows,
                   lambda r: (r["equipment_name"], fmt_date(r["approved_at"] or r["request_date"]),
                              fmt_date(r["due_date"]), fmt_date(r["returned_at"]), r["status"],
                              r["return_condition"] or "-"))

    # ---------- shared ----------

    def prompt_password_change(self):
        """Accounts made by an admin start with a temporary password: ask for a new one right away."""
        messagebox.showinfo("Change Your Password", "Your account was created with a temporary password.\n"
                            "Please set your own password now.")
        self.open_change_password()

    def open_change_password(self):
        from ui.change_password import ChangePasswordDialog
        ChangePasswordDialog(self, self.user)

    def logout(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()
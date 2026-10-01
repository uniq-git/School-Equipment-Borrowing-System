"""Student / Teacher dashboard (navy sidebar + light content area), built on ui.helpers."""
from collections import Counter

import customtkinter as ctk
from PIL import Image

import borrow_service
import equipment_service
from ui import colors
from ui.helpers import (AMBER, build_main, build_sidebar, build_topbar, button, fill_table, fmt_date, label,
                        make_table, setup_table_style, show_page as switch_page, tool_row)

PAGES = {"catalog": "Equipment Catalog", "requests": "My Requests"}
STATUS_COLORS = {"Pending": AMBER, "Approved": colors.SUCCESS_GREEN, "Denied": colors.ACCENT_RED}
REQUEST_COLS = [("ID", 50), ("Equipment", 220), ("Qty", 60), ("Status", 110),
                ("Requested", 140), ("Due Date", 110), ("Approved By", 150)]


class DashboardWindow(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user, self._imgs, self._items = user, [], []
        self.title("ICCT Colleges Foundation, Inc. - Equipment Borrowing System")
        self.geometry("1150x700")
        self.minsize(980, 620)
        self.configure(fg_color=colors.BG_LIGHT)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        setup_table_style()

        self.nav = build_sidebar(self, PAGES, self.show_page, user, self.logout, self.open_change_password)
        main, body = build_main(self)
        self.title_lbl, self.stat_lbls = build_topbar(main, [(s, s, c) for s, c in STATUS_COLORS.items()])
        self.pages = {"catalog": self._build_catalog(body), "requests": self._build_requests(body)}
        self.show_page("catalog")

    def show_page(self, key):
        switch_page(key, self.pages, self.nav, self.title_lbl, PAGES)

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
        ctk.CTkOptionMenu(row, values=["All"] + equipment_service.get_category_names(), variable=self.category_var,
                          width=170, height=32, corner_radius=3, fg_color=colors.ENTRY_BG, button_color=colors.BUTTON_BLUE,
                          button_hover_color=colors.BUTTON_BLUE_HOVER, text_color=colors.TEXT_DARK,
                          command=lambda _: self.render_catalog()).pack(side="left")

        self.catalog_frame = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        self.catalog_frame.grid(row=1, column=0, sticky="nswe")
        self.load_catalog()
        return page

    def load_catalog(self):
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
            label(self.catalog_frame, "No equipment found.", 13, color=colors.TEXT_GRAY).pack(pady=20)
        for item, available in rows:
            self._item_card(item, available)

    def _item_card(self, item, available):
        ok = available > 0
        color, tint = (colors.SUCCESS_GREEN, "#e3f4ea") if ok else (colors.ACCENT_RED, "#fbe4ea")
        card = ctk.CTkFrame(self.catalog_frame, fg_color=colors.CARD_WHITE, corner_radius=4)
        card.pack(fill="x", pady=6, padx=(0, 6))
        ctk.CTkFrame(card, fg_color=color, width=5, corner_radius=0).pack(side="left", fill="y")

        thumb = label(card, "No\nPhoto", 11, color=colors.TEXT_GRAY, fg_color=colors.ENTRY_BG,
                      width=72, height=72, corner_radius=3)
        try:
            path = equipment_service.get_photo_full_path(item["photo_path"])
            if path:
                img = Image.open(path)
                img.thumbnail((72, 72))
                self._imgs.append(ctk.CTkImage(img, img, size=img.size))
                thumb.configure(image=self._imgs[-1], text="")
        except Exception:
            pass  # fall back to the "No Photo" placeholder
        thumb.pack(side="left", padx=16, pady=14)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=14)
        label(info, item["name"], 15, True, anchor="w").pack(fill="x")
        label(info, f"{item['category']}  \u2022  Condition: {item['condition_status']}", 12,
              color=colors.TEXT_GRAY, anchor="w").pack(fill="x", pady=(2, 0))

        button(card, "Request", lambda: self.open_request_dialog(item, available), h=34,
               font=ctk.CTkFont(size=13, weight="bold"), state="normal" if ok else "disabled").pack(
            side="right", padx=(8, 18))
        label(card, f"{available} available" if ok else "Out of stock", 12, True, color,
              fg_color=tint, corner_radius=4, width=110, height=26).pack(side="right", padx=8)

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
        tool_row(bar, left=[("Refresh", self.load_my_requests)])
        self.req_tree = make_table(page, REQUEST_COLS, tags=STATUS_COLORS)
        self.load_my_requests()
        return page

    def load_my_requests(self):
        rows = borrow_service.get_requests_for_user(self.user["id"])
        fill_table(self.req_tree, rows,
                   lambda r: (r["equipment_name"], r["quantity"], r["status"], fmt_date(r["request_date"]),
                              fmt_date(r["due_date"]), r["approved_by_name"] or "-"),
                   lambda r: (r["status"],))
        counts = Counter(r["status"] for r in rows)
        for status, lbl in self.stat_lbls.items():
            lbl.configure(text=str(counts[status]))

    # ---------- shared ----------

    def open_change_password(self):
        from ui.change_password import ChangePasswordDialog
        ChangePasswordDialog(self, self.user)

    def logout(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()
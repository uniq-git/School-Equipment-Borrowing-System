"""Student / Teacher dashboard (navy sidebar + light content area, like the login screen)."""
from ui.helpers import button, goto_login, label
import os
import customtkinter as ctk
from PIL import Image

from ui import colors
from ui.left_panel import ASSETS_DIR
import equipment_service
import borrow_service

SIDEBAR_W, NAV_TEXT, NAV_ACTIVE, NAV_HOVER = 250, "#c7cede", "#1f3357", "#1a2b49"
STATUS = {  # status: (text color, soft badge background)
    "Pending": ("#b7791f", "#fdf3dc"),
    "Approved": (colors.SUCCESS_GREEN, "#e3f4ea"),
    "Denied": (colors.ACCENT_RED, "#fbe4ea"),
}
# My Requests columns: (title, min width, stretch weight)
REQ_COLS = (("ID", 50, 0), ("Equipment", 220, 3), ("Qty", 60, 0), ("Status", 120, 0),
            ("Requested", 150, 1), ("Due Date", 110, 1), ("Approved By", 150, 1))
PAGES = {"catalog": "Equipment Catalog", "requests": "My Requests"}

class DashboardWindow(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user, self._imgs, self._items, self._pages, self._nav = user, [], [], {}, {}
        self.title("ICCT Colleges Foundation, Inc. - Equipment Borrowing System")
        self.geometry("1150x700")
        self.minsize(980, 620)
        self.configure(fg_color=colors.BG_LIGHT)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()

        main = ctk.CTkFrame(self, fg_color=colors.BG_LIGHT, corner_radius=0)
        main.grid(row=0, column=1, sticky="nswe")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        self._build_topbar(main)

        body = ctk.CTkFrame(main, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nswe", padx=28, pady=(0, 24))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self._pages = {"catalog": self._build_catalog(body), "requests": self._build_requests(body)}
        self.show_page("catalog")

    # ---------- layout ----------

    def _build_sidebar(self):
        side = ctk.CTkFrame(self, fg_color=colors.NAVY_DARK, corner_radius=0, width=SIDEBAR_W)
        side.grid(row=0, column=0, sticky="nswe")
        side.pack_propagate(False)
        ctk.CTkFrame(side, fg_color=colors.ACCENT_RED, width=4, height=64, corner_radius=0).place(x=0, y=34)

        logo = os.path.join(ASSETS_DIR, "logo.png")
        if os.path.exists(logo):
            img = Image.open(logo)
            self._logo = ctk.CTkImage(img, img, size=(84, 84))
            ctk.CTkLabel(side, image=self._logo, text="").pack(pady=(26, 10))
        label(side, "ICCT Colleges\nFoundation, Inc.", 15, True, "white").pack(pady=(0 if os.path.exists(logo) else 30, 0))
        label(side, "Equipment Borrowing System", 11, color=NAV_TEXT).pack(pady=(4, 10))
        ctk.CTkFrame(side, fg_color=colors.ACCENT_RED, width=50, height=3, corner_radius=2).pack()

        nav = ctk.CTkFrame(side, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=(30, 0))
        label(nav, "MENU", 10, True, "#7f8ba6", anchor="w").pack(fill="x", padx=8, pady=(0, 6))
        for key, title in PAGES.items():
            self._nav[key] = button(nav, title, lambda k=key: self.show_page(k), h=40, corner_radius=8,
                                    fg="transparent", hover=NAV_HOVER, text_color=NAV_TEXT,
                                    anchor="w", font=ctk.CTkFont(size=13, weight="bold"))
            self._nav[key].pack(fill="x", pady=2)

        bottom = ctk.CTkFrame(side, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=18)
        card = ctk.CTkFrame(bottom, fg_color=NAV_ACTIVE, corner_radius=10)
        card.pack(fill="x", pady=(0, 10))
        label(card, self.user["full_name"], 13, True, "white", anchor="w", wraplength=SIDEBAR_W - 70,
              justify="left").pack(fill="x", padx=14, pady=(10, 0))
        label(card, self.user["role"], 11, color=NAV_TEXT, anchor="w").pack(fill="x", padx=14, pady=(0, 10))
        button(bottom, "Change Password", self.open_change_password, w=0, fg="transparent", hover=NAV_HOVER,
               border_width=1, border_color="#3a4a6b", text_color="white").pack(fill="x")

    def _build_topbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="we", padx=28, pady=(24, 14))
        bar.grid_columnconfigure(0, weight=1)
        self.title_lbl = label(bar, "", 24, True, anchor="w")
        self.title_lbl.grid(row=0, column=0, sticky="w")

        stats = ctk.CTkFrame(bar, fg_color="transparent")
        stats.grid(row=0, column=1, sticky="e")
        self.stat_lbls = {}
        for status, (color, _) in STATUS.items():
            box = ctk.CTkFrame(stats, fg_color=colors.CARD_WHITE, corner_radius=10, width=96, height=58)
            box.pack(side="left", padx=(8, 0))
            box.pack_propagate(False)
            self.stat_lbls[status] = label(box, "0", 20, True, color)
            self.stat_lbls[status].pack(pady=(6, 0))
            label(box, status, 11, color=colors.TEXT_GRAY).pack()

    def show_page(self, key):
        for name, page in self._pages.items():
            page.grid(row=0, column=0, sticky="nswe") if name == key else page.grid_forget()
        for name, btn in self._nav.items():
            btn.configure(fg_color=NAV_ACTIVE if name == key else "transparent",
                          text_color="white" if name == key else NAV_TEXT)
        self.title_lbl.configure(text=PAGES[key])

    # ---------- Equipment Catalog ----------

    def _build_catalog(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=10)
        bar.grid(row=0, column=0, sticky="we", pady=(0, 12))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.render_catalog())
        ctk.CTkEntry(bar, textvariable=self.search_var, placeholder_text="Search equipment...", width=260,
                     height=36, fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY,
                     text_color=colors.TEXT_DARK).pack(side="left", padx=(14, 10), pady=12)
        label(bar, "Category", color=colors.TEXT_GRAY).pack(side="left", padx=6)
        self.category_var = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(bar, values=["All"] + equipment_service.get_category_names(), variable=self.category_var,
                          width=190, height=36, fg_color=colors.ENTRY_BG, button_color=colors.BUTTON_BLUE,
                          button_hover_color=colors.BUTTON_BLUE_HOVER, text_color=colors.TEXT_DARK,
                          command=lambda _: self.render_catalog()).pack(side="left")
        button(bar, "Refresh", self.load_catalog).pack(side="right", padx=14)

        self.catalog_frame = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        self.catalog_frame.grid(row=1, column=0, sticky="nswe")
        self.load_catalog()
        return page

    def load_catalog(self):
        self._items = [(i, borrow_service.get_available_quantity(i["id"])) for i in equipment_service.get_all_equipment()]
        self.render_catalog()

    def render_catalog(self):
        for w in self.catalog_frame.winfo_children():
            w.destroy()
        self._imgs.clear()
        cat, query = self.category_var.get(), self.search_var.get().strip().lower()
        rows = [(i, a) for i, a in self._items
                if cat in ("All", i["category"]) and query in i["name"].lower()]
        if not rows:
            label(self.catalog_frame, "No equipment found.", 13, color=colors.TEXT_GRAY).pack(pady=40)
        for item, available in rows:
            self._item_card(item, available)

    def _item_card(self, item, available):
        ok = available > 0
        color, tint = (colors.SUCCESS_GREEN, "#e3f4ea") if ok else (colors.ACCENT_RED, "#fbe4ea")
        card = ctk.CTkFrame(self.catalog_frame, fg_color=colors.CARD_WHITE, corner_radius=12)
        card.pack(fill="x", pady=6, padx=(0, 6))
        ctk.CTkFrame(card, fg_color=color, width=5, corner_radius=0).pack(side="left", fill="y")

        thumb = label(card, "No\nPhoto", 11, color=colors.TEXT_GRAY, fg_color=colors.ENTRY_BG,
                      width=72, height=72, corner_radius=8)
        path = equipment_service.get_photo_full_path(item["photo_path"])
        try:
            if path:
                img = Image.open(path)
                img.thumbnail((72, 72))
                self._imgs.append(ctk.CTkImage(img, img, size=img.size))
                thumb.configure(image=self._imgs[-1], text="")
        except Exception:
            pass
        thumb.pack(side="left", padx=16, pady=14)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=14)
        label(info, item["name"], 15, True, anchor="w").pack(fill="x")
        label(info, f"{item['category']}  •  Condition: {item['condition_status']}", 12,
              color=colors.TEXT_GRAY, anchor="w").pack(fill="x", pady=(2, 0))

        button(card, "Request", lambda: self.open_request_dialog(item, available), h=34,
               font=ctk.CTkFont(size=13, weight="bold"),
               state="normal" if ok else "disabled").pack(side="right", padx=(8, 18))
        label(card, f"{available} available" if ok else "Out of stock", 12, True, color,
              fg_color=tint, corner_radius=12, width=110, height=26).pack(side="right", padx=8)

    def open_request_dialog(self, item, available):
        from ui.borrow import RequestEquipmentDialog
        RequestEquipmentDialog(self, self.user, item, available,
                               on_success=lambda: (self.load_catalog(), self.load_my_requests()))

    # ---------- My Requests ----------

    def _build_requests(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        button(page, "Refresh", self.load_my_requests).grid(row=0, column=0, sticky="w", pady=(0, 12))

        card = ctk.CTkFrame(page, fg_color=colors.CARD_WHITE, corner_radius=12)
        card.grid(row=1, column=0, sticky="nswe")

        head = ctk.CTkFrame(card, fg_color=colors.BG_LIGHT, corner_radius=8, height=38)
        head.pack(fill="x", padx=16, pady=(16, 4))
        self._req_row(head, [label(head, t.upper(), 10, True, colors.TEXT_GRAY) for t, _, _ in REQ_COLS])

        self.req_list = ctk.CTkScrollableFrame(card, fg_color="transparent", corner_radius=0)
        self.req_list.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        self.load_my_requests()
        return page

    def _req_row(self, row, cells):
        """Lay cells out on the shared column grid so header and rows line up."""
        for i, ((_, width, weight), cell) in enumerate(zip(REQ_COLS, cells)):
            row.grid_columnconfigure(i, minsize=width, weight=weight)
            cell.grid(row=0, column=i, sticky="w" if i == 1 else "", padx=6, pady=10)

    def load_my_requests(self):
        for w in self.req_list.winfo_children():
            w.destroy()
        counts = dict.fromkeys(STATUS, 0)
        rows = borrow_service.get_requests_for_user(self.user["id"])
        if not rows:
            label(self.req_list, "You haven't made any requests yet.", 13, color=colors.TEXT_GRAY).pack(pady=40)
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
            color, tint = STATUS.get(r["status"], (colors.TEXT_GRAY, colors.BG_LIGHT))
            row = ctk.CTkFrame(self.req_list, fg_color="transparent", height=44)
            row.pack(fill="x", padx=8)
            plain = [r["id"], r["equipment_name"], r["quantity"]]
            rest = [r["request_date"], r["due_date"] or "-", r["approved_by_name"] or "-"]
            cells = [label(row, str(v), 12, i == 1) for i, v in enumerate(plain)]
            cells.append(label(row, r["status"], 11, True, color, fg_color=tint, corner_radius=12, width=90, height=24))
            cells += [label(row, str(v), 12, color=colors.TEXT_GRAY) for v in rest]
            self._req_row(row, cells)
            ctk.CTkFrame(self.req_list, fg_color=colors.BG_LIGHT, height=1, corner_radius=0).pack(fill="x", padx=8)
        for status, lbl in self.stat_lbls.items():
            lbl.configure(text=str(counts[status]))

    # ---------- shared ----------

    def open_change_password(self):
        from ui.change_password import ChangePasswordDialog
        ChangePasswordDialog(self, self.user)

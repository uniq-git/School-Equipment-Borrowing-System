"""Student / Teacher dashboard (navy sidebar + light content area, like the login screen)."""
import os
import customtkinter as ctk
from tkinter import ttk
from PIL import Image

from ui import colors
from ui.left_panel import ASSETS_DIR
import equipment_service
import borrow_service

SIDEBAR_W, NAV_TEXT, NAV_ACTIVE, NAV_HOVER = 250, "#c7cede", "#1f3357", "#1a2b49"
STATUS = {"Pending": "#b7791f", "Approved": colors.SUCCESS_GREEN, "Denied": colors.ACCENT_RED}
PAGES = {
    "catalog": ("Equipment Catalog", "Browse available equipment and send a borrow request."),
    "requests": ("My Requests", "Track the status of everything you have requested."),
}


def label(parent, text, size=12, bold=False, color=colors.TEXT_DARK, **kw):
    font = ctk.CTkFont(size=size, weight="bold" if bold else "normal")
    return ctk.CTkLabel(parent, text=text, font=font, text_color=color, **kw)


def button(parent, text, command, w=100, h=36, fg=colors.BUTTON_BLUE, hover=colors.BUTTON_BLUE_HOVER, **kw):
    return ctk.CTkButton(parent, text=text, command=command, width=w, height=h,
                         fg_color=fg, hover_color=hover, **kw)


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

        self._style_tables()
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
        for key, (title, _) in PAGES.items():
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
        button(bottom, "Log Out", self.logout, w=0, fg=colors.ACCENT_RED, hover="#b52a48",
               font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", pady=(8, 0))

    def _build_topbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="we", padx=28, pady=(24, 14))
        bar.grid_columnconfigure(0, weight=1)
        self.title_lbl = label(bar, "", 24, True, anchor="w")
        self.title_lbl.grid(row=0, column=0, sticky="w")
        self.sub_lbl = label(bar, "", 13, color=colors.TEXT_GRAY, anchor="w")
        self.sub_lbl.grid(row=1, column=0, sticky="w")

        stats = ctk.CTkFrame(bar, fg_color="transparent")
        stats.grid(row=0, column=1, rowspan=2, sticky="e")
        self.stat_lbls = {}
        for status, color in STATUS.items():
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
        self.title_lbl.configure(text=PAGES[key][0])
        self.sub_lbl.configure(text=PAGES[key][1])

    def _style_tables(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("Treeview", rowheight=36, font=("Segoe UI", 10), background=colors.CARD_WHITE,
                    fieldbackground=colors.CARD_WHITE, foreground=colors.TEXT_DARK, borderwidth=0)
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=colors.NAVY_DARK,
                    foreground="white", relief="flat", padding=(6, 8))
        s.map("Treeview.Heading", background=[("active", colors.BUTTON_BLUE)])
        s.map("Treeview", background=[("selected", colors.BUTTON_BLUE)], foreground=[("selected", "white")])

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
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        cols = {"id": 50, "equipment": 240, "quantity": 80, "status": 110,
                "request_date": 150, "due_date": 110, "approved_by": 170}
        self.tree = ttk.Treeview(card, columns=list(cols), show="headings", selectmode="browse")
        for col, width in cols.items():
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=width, anchor="w" if col == "equipment" else "center")
        for status, color in STATUS.items():
            self.tree.tag_configure(status, foreground=color)
        scroll = ctk.CTkScrollbar(card, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nswe", padx=(10, 0), pady=10)
        scroll.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=10)

        self.empty_lbl = label(card, "You haven't made any requests yet.", 13, color=colors.TEXT_GRAY)
        self.load_my_requests()
        return page

    def load_my_requests(self):
        self.tree.delete(*self.tree.get_children())
        counts = dict.fromkeys(STATUS, 0)
        rows = borrow_service.get_requests_for_user(self.user["id"])
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
            self.tree.insert("", "end", iid=str(r["id"]), tags=(r["status"],), values=(
                r["id"], r["equipment_name"], r["quantity"], r["status"], r["request_date"],
                r["due_date"] or "-", r["approved_by_name"] or "-"))
        for status, lbl in self.stat_lbls.items():
            lbl.configure(text=str(counts[status]))
        self.empty_lbl.place_forget() if rows else self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")

    # ---------- shared ----------

    def open_change_password(self):
        from ui.change_password import ChangePasswordDialog
        ChangePasswordDialog(self, self.user)

    def logout(self):
        self.destroy()
        from ui.login import LoginWindow
        LoginWindow().mainloop()
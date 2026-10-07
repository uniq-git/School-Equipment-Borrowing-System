"""
Admin/Staff dialog for registering a new equipment item into the catalog.
"""
import os
from tkinter import filedialog, messagebox
import customtkinter as ctk

from ui import colors
from ui.helpers import FormDialog, button, label, soft_button
from services import equipment_service


class AddEquipmentDialog(FormDialog):
    def __init__(self, parent, user):
        super().__init__(parent, "Register Equipment", "380x640")
        self.user, self.photo_path = user, None
        f = self.f
 
        self.name_entry = f.entry("Name", "Equipment name")
 
        # Category dropdown + "+ New" button
        categories = equipment_service.get_category_names()
        self.category_var = ctk.StringVar(value=categories[0] if categories else "")
        f.title("Category")
        row = f.place(ctk.CTkFrame(self, fg_color="transparent"))
        self.category_menu = ctk.CTkOptionMenu(
            row, values=categories or ["No categories yet"], variable=self.category_var,
            width=244)
        self.category_menu.pack(side="left")
        soft_button(row, "+ New", self._open_add_category, w=48, h=28).pack(side="left", padx=(6, 0))
 
        self.quantity_entry = f.entry("Quantity", "0")
        self.condition_var = ctk.StringVar(value=equipment_service.CONDITION_OPTIONS[0])
        f.menu("Condition", equipment_service.CONDITION_OPTIONS, self.condition_var)
 
        # Photo picker
        f.title("Photo")
        row = f.place(ctk.CTkFrame(self, fg_color="transparent"))
        self.photo_label = label(row, "No photo selected", 12, color=colors.TEXT_GRAY, width=210, anchor="w")
        self.photo_label.pack(side="left")
        soft_button(row, "Browse", self._choose_photo, w=80, h=28).pack(side="left", padx=(6, 0))
 
        self.footer("Register Equipment", self.handle_submit)
 
    def _choose_photo(self):
        path = filedialog.askopenfilename(
            title="Select a photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")])
        if path:
            self.photo_path = path
            self.photo_label.configure(text=os.path.basename(path))
 
    def _open_add_category(self):
        name = ctk.CTkInputDialog(text="New category name:", title="Add Category").get_input()
        if not name:
            return
        ok, message = equipment_service.add_category(name)
        if ok:
            self.category_menu.configure(values=equipment_service.get_category_names())
            self.category_var.set(name.strip())
        self.show(message, ok)
 
    def handle_submit(self):
        name, category = self.name_entry.get(), self.category_var.get()
        if category == "No categories yet":
            return self.show("Please add a category first.")
 
        ok, message = equipment_service.add_equipment(
            name, category, self.quantity_entry.get(), self.condition_var.get(), self.photo_path, self.user["id"])
        self.result(ok, message, getattr(self.parent, "load_equipment", None))


class EditEquipmentDialog(FormDialog):
    """Admin/Staff: edit Name, Category, Quantity, Condition and Photo of an existing item."""

    def __init__(self, parent, item):
        super().__init__(parent, "Edit Equipment", "380x700")
        self.item, self.photo_path = item, None
        f = self.f

        self.name_entry = f.entry("Name", "Equipment name")
        self.name_entry.insert(0, item["name"])

        categories = equipment_service.get_category_names()
        if item["category"] not in categories:
            categories.append(item["category"])
        self.category_var = ctk.StringVar(value=item["category"])
        f.menu("Category", categories, self.category_var)

        self.quantity_entry = f.entry("Quantity", "0")
        self.quantity_entry.insert(0, str(item["quantity"]))

        # Units taken out of service by a damaged return; set back to 0 once repaired.
        self.repair_entry = f.entry("Units Under Repair", "0")
        self.repair_entry.insert(0, str(item.get("under_repair") or 0))

        current = item["condition_status"]
        self.condition_var = ctk.StringVar(
            value=current if current in equipment_service.CONDITION_OPTIONS
            else equipment_service.CONDITION_OPTIONS[0])
        f.menu("Condition", equipment_service.CONDITION_OPTIONS, self.condition_var)
    
        f.title("Photo")
        row = f.place(ctk.CTkFrame(self, fg_color="transparent"))
        self.photo_label = label(row, "Current photo kept" if item["photo_path"] else "No photo",
                                 12, color=colors.TEXT_GRAY, width=210, anchor="w")
        self.photo_label.pack(side="left")
        soft_button(row, "Browse", self._choose_photo, w=80, h=28).pack(side="left", padx=(6, 0))

        self.footer("Save Changes", self.handle_submit)

    def _choose_photo(self):
        path = filedialog.askopenfilename(
            title="Select a photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")])
        if path:
            self.photo_path = path
            self.photo_label.configure(text=os.path.basename(path))

    def handle_submit(self):
        ok, message = equipment_service.update_equipment(
            self.item["id"], self.name_entry.get(), self.category_var.get(),
            self.quantity_entry.get(), self.condition_var.get(), self.photo_path,
            under_repair=self.repair_entry.get())
        self.result(ok, message, getattr(self.parent, "load_equipment", None))


class ManageCategoriesDialog(FormDialog):
    """Admin/Staff: add or delete equipment categories."""

    def __init__(self, parent):
        super().__init__(parent, "Manage Categories", "380x540")
        f = self.f

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=colors.BG_LIGHT, corner_radius=4, height=270)
        self.list_frame.pack(fill="x", padx=30, pady=(8, 0))

        f.title("Add Category")
        row = f.place(ctk.CTkFrame(self, fg_color="transparent"))
        self.new_entry = ctk.CTkEntry(row, placeholder_text="New category name", width=210, height=34,
                                      fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY,
                                      text_color=colors.TEXT_DARK)
        self.new_entry.pack(side="left")
        soft_button(row, "Add", self._add, w=80, h=34).pack(side="left", padx=(6, 0))

        self.status = label(self, "", 12, color=colors.ACCENT_RED, wraplength=300, justify="left")
        self.status.pack(anchor="w", padx=30, pady=(10, 0))
        soft_button(self, "Close", self.destroy, w=300, h=34).pack(anchor="w", padx=30, pady=(10, 0))
        self._render()

    def _render(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        for cat in equipment_service.get_categories():
            row = ctk.CTkFrame(self.list_frame, fg_color=colors.CARD_WHITE, corner_radius=3)
            row.pack(fill="x", pady=2, padx=2)
            label(row, cat["name"], 13, anchor="w").pack(side="left", padx=10, pady=6)
            button(row, "Delete", lambda c=cat: self._delete(c), w=64, h=26,
                   fg=colors.ACCENT_RED, hover="#b52a48").pack(side="right", padx=8)

    def _add(self):
        ok, message = equipment_service.add_category(self.new_entry.get())
        self.show(message, ok)
        if ok:
            self.new_entry.delete(0, "end")
            self._render()

    def _delete(self, cat):
        if messagebox.askyesno("Confirm Delete", f"Delete the category '{cat['name']}'?", parent=self):
            ok, message = equipment_service.delete_category(cat["id"])
            self.show(message, ok)
            self._render()
"""
Admin/Staff dialog for registering a new equipment item into the catalog.
"""
import os
from tkinter import filedialog
import customtkinter as ctk

from ui import colors
from ui.helpers import FormDialog, label, soft_button
import equipment_service


class AddEquipmentDialog(FormDialog):
    def __init__(self, parent, user):
        super().__init__(parent, "Register Equipment", "380x640")
        self.user, self.photo_path = user, None
        f = self.f
 
        # Category dropdown + "+ New" button
        categories = equipment_service.get_category_names()
        self.category_var = ctk.StringVar(value=categories[0] if categories else "")
        f.title("Category")
        row = f.place(ctk.CTkFrame(self, fg_color="transparent"))
        self.category_menu = ctk.CTkOptionMenu(
            row, values=categories or ["No categories yet"], variable=self.category_var,
            width=244, command=self._on_category_changed)
        self.category_menu.pack(side="left")
        soft_button(row, "+ New", self._open_add_category, w=48, h=28).pack(side="left", padx=(6, 0))
 
        # Equipment types depend on the selected category
        types = equipment_service.get_equipment_types(self.category_var.get())
        self.type_var = ctk.StringVar(value=types[0] if types else "")
        self.type_menu = f.menu("Equipment Type", types or ["No types available"], self.type_var)
 
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
 
    def _on_category_changed(self, category):
        """Refresh the Equipment Type dropdown to match the selected category."""
        types = equipment_service.get_equipment_types(category)
        self.type_menu.configure(values=types or ["No types available"])
        self.type_var.set(types[0] if types else "")
 
    def _open_add_category(self):
        name = ctk.CTkInputDialog(text="New category name:", title="Add Category").get_input()
        if not name:
            return
        ok, message = equipment_service.add_category(name)
        if ok:
            self.category_menu.configure(values=equipment_service.get_category_names())
            self.category_var.set(name.strip())
            self._on_category_changed(name.strip())
        self.show(message, ok)
 
    def handle_submit(self):
        name, category = self.type_var.get(), self.category_var.get()  # the type is saved as the item name
        if category == "No categories yet":
            return self.show("Please add a category first.")
        if name == "No types available":
            return self.show("Please select an equipment type.")
 
        ok, message = equipment_service.add_equipment(
            name, category, self.quantity_entry.get(), self.condition_var.get(), self.photo_path, self.user["id"])
        self.result(ok, message, getattr(self.parent, "load_equipment", None))
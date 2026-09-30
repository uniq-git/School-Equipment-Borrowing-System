"""
Admin/Staff dialog for registering a new equipment item into the catalog.
"""

from tkinter import filedialog

import customtkinter as ctk

from ui import colors

import equipment_service


class AddEquipmentDialog(ctk.CTkToplevel):

    def __init__(self, parent, user):
        super().__init__(parent)

        self.parent = parent
        self.user = user
        self.photo_path = None

        self.title("Register Equipment")
        self.geometry("380x640")
        self.resizable(False, False)
        self.configure(fg_color=colors.CARD_WHITE)
        self.transient(parent)
        self.grab_set()

        pad_x = 30

        ctk.CTkLabel(
            self, text="Register Equipment", font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors.TEXT_DARK,
        ).pack(anchor="w", padx=pad_x, pady=(20, 4))

        # Get the saved categories so they can be shown in the dropdown.
        ctk.CTkLabel(
            self, text="Category", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(14, 4))

        category_row = ctk.CTkFrame(self, fg_color="transparent")
        category_row.pack(anchor="w", padx=pad_x)

        categories = equipment_service.get_category_names()

        # Use the first category as the default choice if there are categories.
        self.category_var = ctk.StringVar(value=categories[0] if categories else "")

        self.category_menu = ctk.CTkOptionMenu(
            category_row, values=categories or ["No categories yet"],
            variable=self.category_var, width=244,
            command=self._on_category_changed,
        )
        self.category_menu.pack(side="left")

        ctk.CTkButton(
            category_row, text="+ New", width=48, height=28, fg_color=colors.ENTRY_BG,
            hover_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
            command=self._open_add_category,
        ).pack(side="left", padx=(6, 0))

        # Equipment Type dropdown - its options depend on whichever
        # Category is currently selected above.
        ctk.CTkLabel(
            self, text="Equipment Type", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(14, 4))

        initial_types = equipment_service.get_equipment_types(self.category_var.get())
        self.type_var = ctk.StringVar(value=initial_types[0] if initial_types else "")

        self.type_menu = ctk.CTkOptionMenu(
            self, values=initial_types or ["No types available"],
            variable=self.type_var, width=300,
        )
        self.type_menu.pack(anchor="w", padx=pad_x)

        self.quantity_entry = self._labeled_entry("Quantity", "0", pad_x)

        ctk.CTkLabel(
            self, text="Condition", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(14, 4))

        # Use the first condition as the default value in the dropdown.
        self.condition_var = ctk.StringVar(value=equipment_service.CONDITION_OPTIONS[0])

        ctk.CTkOptionMenu(
            self, values=equipment_service.CONDITION_OPTIONS, variable=self.condition_var, width=300,
        ).pack(anchor="w", padx=pad_x)

        ctk.CTkLabel(
            self, text="Photo", font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(14, 4))

        photo_row = ctk.CTkFrame(self, fg_color="transparent")
        photo_row.pack(anchor="w", padx=pad_x)

        self.photo_label = ctk.CTkLabel(
            photo_row, text="No photo selected", font=ctk.CTkFont(size=12),
            text_color=colors.TEXT_GRAY, width=210, anchor="w",
        )
        self.photo_label.pack(side="left")

        ctk.CTkButton(
            photo_row, text="Browse", width=80, height=28, fg_color=colors.ENTRY_BG,
            hover_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
            command=self._choose_photo,
        ).pack(side="left", padx=(6, 0))

        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color=colors.ACCENT_RED,
            wraplength=300, justify="left",
        )
        self.status_label.pack(anchor="w", padx=pad_x, pady=(12, 0))

        ctk.CTkButton(
            self, text="Register Equipment", height=40, width=300, fg_color=colors.BUTTON_BLUE,
            hover_color=colors.BUTTON_BLUE_HOVER, font=ctk.CTkFont(size=13, weight="bold"),
            command=self.handle_submit,
        ).pack(anchor="w", padx=pad_x, pady=(16, 6))

        ctk.CTkButton(
            self, text="Cancel", height=32, width=300, fg_color="transparent",
            hover_color=colors.BG_LIGHT, text_color=colors.TEXT_GRAY, command=self.destroy,
        ).pack(anchor="w", padx=pad_x)

    # This helper keeps the same label and entry design for the form fields.
    def _labeled_entry(self, label, placeholder, pad_x):
        ctk.CTkLabel(
            self, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=colors.TEXT_DARK
        ).pack(anchor="w", padx=pad_x, pady=(14, 4))

        entry = ctk.CTkEntry(
            self, placeholder_text=placeholder, height=34, width=300,
            fg_color=colors.ENTRY_BG, border_color=colors.BORDER_GRAY, text_color=colors.TEXT_DARK,
        )
        entry.pack(anchor="w", padx=pad_x)

        return entry

    def _choose_photo(self):
        # Open the file picker so the user can choose an equipment photo.
        path = filedialog.askopenfilename(
            title="Select a photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )

        if path:
            # Save the selected path so it can be sent when the equipment is registered.
            self.photo_path = path

            # Show only the file name instead of the full computer path.
            self.photo_label.configure(text=path.split("/")[-1].split("\\")[-1])

    def _on_category_changed(self, selected_category):
        """Refresh the Equipment Type dropdown to match the new Category."""
        types = equipment_service.get_equipment_types(selected_category)
        self.type_menu.configure(values=types or ["No types available"])
        self.type_var.set(types[0] if types else "")

    def _open_add_category(self):
        # Ask for a new category without closing the equipment dialog.
        dialog = ctk.CTkInputDialog(text="New category name:", title="Add Category")
        name = dialog.get_input()

        if not name:
            return

        # Save the new category before adding it to the dropdown.
        success, message = equipment_service.add_category(name)

        if not success:
            self.status_label.configure(text=message, text_color=colors.ACCENT_RED)
            return

        # Get the updated list so the new category appears right away.
        categories = equipment_service.get_category_names()
        self.category_menu.configure(values=categories)
        self.category_var.set(name.strip())

        # New categories won't have a predefined type list, so this will
        # fall back to the generic "General Item" option.
        self._on_category_changed(name.strip())

        self.status_label.configure(text=message, text_color=colors.SUCCESS_GREEN)

    def handle_submit(self):
        # The selected Equipment Type (e.g. "DSLR Camera") is what gets
        # saved as the equipment's name.
        name = self.type_var.get()
        category = self.category_var.get()
        quantity = self.quantity_entry.get()
        condition = self.condition_var.get()

        # Stop the registration if there is no category selected.
        if category == "No categories yet":
            self.status_label.configure(
                text="Please add a category first.", text_color=colors.ACCENT_RED
            )
            return

        if name == "No types available":
            self.status_label.configure(
                text="Please select an equipment type.", text_color=colors.ACCENT_RED
            )
            return

        # Send the form details to the service so the equipment can be saved.
        success, message = equipment_service.add_equipment(
            name, category, quantity, condition, self.photo_path, self.user["id"]
            
        )

        if success:
            self.status_label.configure(text=message, text_color=colors.SUCCESS_GREEN)

            # Refresh the equipment list in the main window after adding the item.
            if hasattr(self.parent, "load_equipment"):
                self.parent.load_equipment()

            # Close the dialog after showing the success message for a moment.
            self.after(1200, self.destroy)
        else:
            self.status_label.configure(text=message, text_color=colors.ACCENT_RED)
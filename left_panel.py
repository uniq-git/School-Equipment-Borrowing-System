import os
import customtkinter as ctk
from PIL import Image

from ui import colors


ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets"
)

def build_left_panel(parent, height=619):
    frame = ctk.CTkFrame(
        parent,
        fg_color=colors.NAVY_DARK,
        corner_radius=0,
        width=448
    )
    frame.grid_propagate(False)
    frame.configure(height=height)

    # Red bar on the left side.
    ctk.CTkFrame(
        frame,
        fg_color=colors.ACCENT_RED,
        width=4,
        height=110,
        corner_radius=0
    ).place(x=0, rely=0.42)

    content = ctk.CTkFrame(
        frame,
        fg_color="transparent"
    )
    content.place(
        relx=0.5,
        rely=0.45,
        anchor="center"
    )

    logo_path = os.path.join(ASSETS_DIR, "logo.png")

    if os.path.exists(logo_path):
        pil_img = Image.open(logo_path)
        logo_img = ctk.CTkImage(
            light_image=pil_img,
            dark_image=pil_img,
            size=(180, 180)
        )

        ctk.CTkLabel(
            content,
            image=logo_img,
            text=""
        ).pack(pady=(0, 22))

    ctk.CTkLabel(
        content,
        text="ICCT Colleges Foundation, Inc.",
        font=ctk.CTkFont(size=19, weight="bold"),
        text_color="white"
    ).pack()

    ctk.CTkLabel(
        content,
        text="School Equipment Borrowing System",
        font=ctk.CTkFont(size=13),
        text_color="#c7cede"
    ).pack(pady=(4, 14))

    ctk.CTkFrame(
        content,
        fg_color=colors.ACCENT_RED,
        width=60,
        height=3,
        corner_radius=2
    ).pack()

    return frame
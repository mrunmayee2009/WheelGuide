"""
GUI/home.py
------------
Simple welcome/splash screen shown briefly before the login screen.
"""
import customtkinter as ctk
import tkinter as tk
import math


class HomeFrame(ctk.CTkFrame):

    def __init__(self, parent, on_continue=None, **kwargs):

        self.on_continue = on_continue

        super().__init__(
            parent,
            fg_color="#F5F8FF",
            **kwargs
        )

        self.progress_value = 0
        self.spinner_angle = 0
        self.dot_count = 0

        self.create_home()

        self.animate_loading()
        self.animate_spinner()
        self.animate_floating_elements()

    # =====================================================
    # MAIN HOME SCREEN
    # =====================================================

    def create_home(self):

        self.main = ctk.CTkFrame(
            self,
            fg_color="#F5F8FF",
            corner_radius=0
        )

        self.main.pack(
            fill="both",
            expand=True
        )

        # =================================================
        # TOP HEADER
        # =================================================

        self.header = ctk.CTkFrame(
            self.main,
            fg_color="transparent"
        )

        self.header.pack(
            fill="x",
            padx=25,
            pady=(22, 0)
        )

        # Logo circle

        self.logo = ctk.CTkLabel(
            self.header,
            text="♿",
            width=55,
            height=55,
            corner_radius=18,
            fg_color="#1746C7",
            text_color="white",
            font=("Segoe UI Emoji", 27)
        )

        self.logo.pack(side="left")

        # Brand text

        brand_frame = ctk.CTkFrame(
            self.header,
            fg_color="transparent"
        )

        brand_frame.pack(
            side="left",
            padx=12
        )

        self.brand = ctk.CTkLabel(
            brand_frame,
            text="WheelGuide",
            font=("Segoe UI", 22, "bold"),
            text_color="#1746C7"
        )

        self.brand.pack(anchor="w")

        self.brand_small = ctk.CTkLabel(
            brand_frame,
            text="ACCESSIBILITY • GUIDANCE • CARE",
            font=("Segoe UI", 8, "bold"),
            text_color="#45B99A"
        )

        self.brand_small.pack(anchor="w")

        # =================================================
        # HERO AREA
        # =================================================

        self.hero = ctk.CTkFrame(
            self.main,
            fg_color="#EAF2FF",
            corner_radius=30
        )

        self.hero.pack(
            fill="x",
            padx=20,
            pady=(20, 10)
        )

        # Illustration canvas

        self.canvas = tk.Canvas(
            self.hero,
            width=380,
            height=275,
            bg="#EAF2FF",
            highlightthickness=0
        )

        self.canvas.pack(
            pady=(5, 0)
        )

        self.create_illustration()

        # =================================================
        # TITLE
        # =================================================

        self.title_label = ctk.CTkLabel(
            self.main,
            text="WheelGuide",
            font=("Segoe UI", 38, "bold"),
            text_color="#1746C7"
        )

        self.title_label.pack(
            pady=(8, 0)
        )

        # =================================================
        # SUBTITLE
        # =================================================

        self.subtitle = ctk.CTkLabel(
            self.main,
            text="Wheelchair Guidance &\nAssistance System",
            font=("Segoe UI", 15, "bold"),
            text_color="#253858",
            justify="center"
        )

        self.subtitle.pack(
            pady=(5, 0)
        )

        # =================================================
        # TAGLINE
        # =================================================

        self.tagline = ctk.CTkLabel(
            self.main,
            text="Navigate freely. Travel safely. Live independently.",
            font=("Segoe UI", 11),
            text_color="#64748B"
        )

        self.tagline.pack(
            pady=(10, 0)
        )

        # =================================================
        # FEATURES
        # =================================================

        self.feature_frame = ctk.CTkFrame(
            self.main,
            fg_color="transparent"
        )

        self.feature_frame.pack(
            pady=(13, 0)
        )

        self.create_feature(
            "📍",
            "Smart Routes"
        ).pack(
            side="left",
            padx=5
        )

        self.create_feature(
            "♿",
            "Accessible"
        ).pack(
            side="left",
            padx=5
        )

        self.create_feature(
            "🆘",
            "Emergency"
        ).pack(
            side="left",
            padx=5
        )

        # =================================================
        # LOADING AREA
        # =================================================

        self.loading_text = ctk.CTkLabel(
            self.main,
            text="Preparing WheelGuide...",
            font=("Segoe UI", 10, "bold"),
            text_color="#718096"
        )

        self.loading_text.pack(
            pady=(15, 7)
        )

        # Spinner

        self.spinner_canvas = tk.Canvas(
            self.main,
            width=60,
            height=60,
            bg="#F5F8FF",
            highlightthickness=0
        )

        self.spinner_canvas.pack(
            pady=(0, 5)
        )

        # =================================================
        # FOOTER
        # =================================================

        self.footer = ctk.CTkLabel(
            self.main,
            text="Made for easier journeys  •  Your journey starts here ♿",
            font=("Segoe UI", 9),
            text_color="#94A3B8"
        )

        self.footer.pack(
            pady=(2, 15)
        )

    # =====================================================
    # FEATURE CARD
    # =====================================================

    def create_feature(self, icon, text):

        frame = ctk.CTkFrame(
            self.feature_frame,
            fg_color="white",
            corner_radius=14,
            width=105,
            height=42
        )

        frame.pack_propagate(False)

        icon_label = ctk.CTkLabel(
            frame,
            text=icon,
            font=("Segoe UI Emoji", 14)
        )

        icon_label.pack(
            side="left",
            padx=(8, 3)
        )

        text_label = ctk.CTkLabel(
            frame,
            text=text,
            font=("Segoe UI", 9, "bold"),
            text_color="#334155"
        )

        text_label.pack(
            side="left"
        )

        return frame

    # =====================================================
    # ILLUSTRATION
    # =====================================================

    def create_illustration(self):

        c = self.canvas

        # -------------------------------------------------
        # Soft clouds
        # -------------------------------------------------

        c.create_oval(
            15, 35, 95, 100,
            fill="#D8E8FF",
            outline=""
        )

        c.create_oval(
            300, 30, 375, 90,
            fill="#D9F4EE",
            outline=""
        )

        # -------------------------------------------------
        # Sun
        # -------------------------------------------------

        c.create_oval(
            165, 10, 215, 60,
            fill="#FFD76A",
            outline=""
        )

        # -------------------------------------------------
        # Buildings
        # -------------------------------------------------

        buildings = [
            (25, 100, 65, 190),
            (70, 75, 110, 190),
            (115, 105, 150, 190),
            (250, 95, 290, 190),
            (295, 70, 335, 190),
            (340, 110, 375, 190)
        ]

        colors = [
            "#D6E5FA",
            "#CFE0F8",
            "#DDEBFA",
            "#D5E7FA",
            "#CFE2F7",
            "#DCEBFA"
        ]

        for building, color in zip(buildings, colors):

            c.create_rectangle(
                *building,
                fill=color,
                outline=""
            )

        # -------------------------------------------------
        # Windows
        # -------------------------------------------------

        for x in [34, 79, 124, 259, 304, 349]:

            for y in [112, 137, 162]:

                c.create_rectangle(
                    x,
                    y,
                    x + 8,
                    y + 9,
                    fill="#A9C7EC",
                    outline=""
                )

        # -------------------------------------------------
        # Trees
        # -------------------------------------------------

        self.draw_tree(c, 20, 185)
        self.draw_tree(c, 365, 185)

        # -------------------------------------------------
        # ROAD
        # -------------------------------------------------

        c.create_polygon(
            0, 255,
            75, 215,
            145, 235,
            215, 205,
            380, 245,
            380, 275,
            0, 275,
            fill="#CBD5E1",
            outline=""
        )

        # -------------------------------------------------
        # BLUE ROUTE
        # -------------------------------------------------

        c.create_line(
            15, 265,
            75, 235,
            135, 255,
            200, 225,
            270, 245,
            355, 215,
            fill="#3C7EF3",
            width=11,
            smooth=True
        )

        c.create_line(
            15, 265,
            75, 235,
            135, 255,
            200, 225,
            270, 245,
            355, 215,
            fill="white",
            width=3,
            smooth=True
        )

        # -------------------------------------------------
        # ACCESSIBLE GREEN ROUTE
        # -------------------------------------------------

        c.create_line(
            45, 270,
            105, 250,
            155, 265,
            215, 238,
            285, 258,
            340, 240,
            fill="#45B99A",
            width=6,
            smooth=True
        )

        # -------------------------------------------------
        # LOCATION PIN SHADOW
        # -------------------------------------------------

        c.create_oval(
            157, 222,
            223, 238,
            fill="#AEBFD4",
            outline=""
        )

        # -------------------------------------------------
        # LOCATION PIN
        # -------------------------------------------------

        c.create_oval(
            145, 95,
            235, 185,
            fill="#F04B3A",
            outline=""
        )

        c.create_polygon(
            165, 150,
            215, 150,
            190, 225,
            fill="#F04B3A",
            outline=""
        )

        # -------------------------------------------------
        # PIN CENTER
        # -------------------------------------------------

        c.create_oval(
            162, 112,
            218, 168,
            fill="#1746C7",
            outline=""
        )

        c.create_text(
            190,
            140,
            text="♿",
            font=("Segoe UI Emoji", 29),
            fill="white"
        )

        # -------------------------------------------------
        # SMALL LOCATION DOTS
        # -------------------------------------------------

        c.create_oval(
            75, 215,
            85, 225,
            fill="#45B99A",
            outline=""
        )

        c.create_oval(
            300, 215,
            310, 225,
            fill="#F04B3A",
            outline=""
        )

        # -------------------------------------------------
        # Floating accessibility badge
        # -------------------------------------------------

        c.create_oval(
            25, 205,
            75, 255,
            fill="white",
            outline=""
        )

        c.create_text(
            50,
            230,
            text="♿",
            font=("Segoe UI Emoji", 19),
            fill="#1746C7"
        )

        # -------------------------------------------------
        # Floating GPS badge
        # -------------------------------------------------

        c.create_oval(
            305, 180,
            355, 230,
            fill="white",
            outline=""
        )

        c.create_text(
            330,
            205,
            text="📍",
            font=("Segoe UI Emoji", 18)
        )

    # =====================================================
    # TREE
    # =====================================================

    def draw_tree(self, canvas, x, y):

        canvas.create_rectangle(
            x - 4,
            y + 10,
            x + 4,
            y + 38,
            fill="#8A6A50",
            outline=""
        )

        canvas.create_oval(
            x - 18,
            y - 10,
            x + 18,
            y + 25,
            fill="#75C8A7",
            outline=""
        )

        canvas.create_oval(
            x - 8,
            y - 25,
            x + 25,
            y + 15,
            fill="#5FBA98",
            outline=""
        )

    # =====================================================
    # SPINNER
    # =====================================================

    def animate_spinner(self):

        self.spinner_canvas.delete("spinner")

        center_x = 30
        center_y = 30
        radius = 20

        # Background ring

        self.spinner_canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            outline="#DCE5F2",
            width=5,
            tags="spinner"
        )

        # Blue arc

        self.spinner_canvas.create_arc(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            start=self.spinner_angle,
            extent=100,
            style="arc",
            outline="#1746C7",
            width=5,
            tags="spinner"
        )

        # Teal arc

        self.spinner_canvas.create_arc(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            start=self.spinner_angle + 180,
            extent=40,
            style="arc",
            outline="#45B99A",
            width=5,
            tags="spinner"
        )

        self.spinner_angle += 8

        self.after(
            35,
            self.animate_spinner
        )

    # =====================================================
    # LOADING ANIMATION
    # =====================================================

    def animate_loading(self):

        self.progress_value += 0.012

        if self.progress_value < 0.20:

            text = "Preparing WheelGuide"

        elif self.progress_value < 0.40:

            text = "Setting up accessibility"

        elif self.progress_value < 0.60:

            text = "Finding smarter routes"

        elif self.progress_value < 0.80:

            text = "Preparing your journey"

        elif self.progress_value < 1:

            text = "Almost ready"

        else:

            self.loading_text.configure(
                text="Welcome to WheelGuide! ♿"
            )

            self.after(
                700,
                self.open_login
            )

            return

        # Animated dots

        self.dot_count = (self.dot_count + 1) % 4

        dots = "." * self.dot_count

        self.loading_text.configure(
            text=text + dots
        )

        self.after(
            40,
            self.animate_loading
        )

    # =====================================================
    # FLOATING ANIMATION
    # =====================================================

    def animate_floating_elements(self):

        # Small breathing effect for the logo

        self.logo.configure(
            text="♿"
        )

        self.after(
            1200,
            self.animate_floating_elements
        )

    # =====================================================
    # OPEN LOGIN / SIGN UP
    # =====================================================

    def open_login(self):

        if self.on_continue is not None:

            self.on_continue()
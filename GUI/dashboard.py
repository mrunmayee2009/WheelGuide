"""
GUI/dashboard.py
----------------
WheelGuide - Main Dashboard

Provides:
- Home
- Search Destination / Route Planner
- Accessibility AI
- Offline Maps
- Staircase Detection
- Construction / Obstacle Reporting
- Hospitals & Wheelchair Repair
- Medical Reports
- Emergency / SOS
- Profile
- Notifications
- Quick Actions
- Services

Existing AI, Maps, Emergency and Database modules are preserved.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import webbrowser
import sys
import os
from datetime import datetime


# ================================================================
# PROJECT PATH
# ================================================================

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


# ================================================================
# EXISTING WHEELGUIDE MODULES
# ================================================================

from AI.accessibility import get_accessibility_score
from AI.medical_report import summarize_report

from AI.staircase import (
    detect_staircase_in_image,
    detect_staircase_from_webcam
)

from AI.construction import (
    detect_construction_in_image,
    report_construction_zone
)

from Maps.route import (
    build_demo_graph,
    compare_shortest_vs_accessible
)

from Maps.offline_maps import (
    cache_area_tiles,
    build_offline_map
)

from Emergency.sos import send_sos
from Emergency.voice_sos import VoiceSOSListener

from Emergency.offline_mode import (
    get_offline_emergency_card,
    play_local_alarm,
    retry_queued_sos
)

from Recommendation.hospitals import (
    find_nearby_hospitals,
    clear_cache as clear_hospital_cache,
)
from Recommendation.repairshop import find_nearby_repair_shops

from Database.database import (
    add_emergency_contact,
    save_medical_report,
    save_place_score
)


# ================================================================
# WHEELGUIDE THEME
# ================================================================

BG = "#F5F8FC"
WHITE = "#FFFFFF"

PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"

TEAL = "#16B8A6"
TEAL_DARK = "#0F9F8F"

PURPLE = "#7C3AED"
ORANGE = "#F59E0B"
RED = "#EF4444"

TEXT = "#172033"
TEXT_SECONDARY = "#64748B"
TEXT_LIGHT = "#94A3B8"

BORDER = "#E5EAF1"

BLUE_SOFT = "#EAF2FF"
TEAL_SOFT = "#E7FAF7"
PURPLE_SOFT = "#F2EDFF"
ORANGE_SOFT = "#FFF5E6"
RED_SOFT = "#FFECEC"
GREEN_SOFT = "#EAF9EF"


# ================================================================
# DASHBOARD
# ================================================================

class DashboardFrame(ctk.CTkFrame):

    def __init__(self, master, user, **kwargs):

        super().__init__(
            master,
            fg_color=BG,
            corner_radius=0,
            **kwargs
        )

        # --------------------------------------------------------
        # USER
        # --------------------------------------------------------

        if isinstance(user, dict):
            self.user = user
        else:
            self.user = {}

        # --------------------------------------------------------
        # DEFAULT LOCATION
        # --------------------------------------------------------

        self.current_location = (
            19.0760,
            72.8777
        )

        # --------------------------------------------------------
        # STATE
        # --------------------------------------------------------

        self.voice_listener = None

        self.drawer_open = False
        self.drawer_visible = False

        self.current_page = "Dashboard"

        self.nav_buttons = {}

        # Compatibility attributes
        self.bottom_nav = None
        self.plus_button = None
        self.drawer = None

        # --------------------------------------------------------
        # GRID
        # --------------------------------------------------------

        self.grid_rowconfigure(
            0,
            weight=1
        )

        self.grid_columnconfigure(
            0,
            weight=1
        )

        # --------------------------------------------------------
        # BUILD UI ONLY ONCE
        # --------------------------------------------------------

        self._build_ui()


    # ============================================================
    # GREETING
    # ============================================================

    def get_greeting(self):

        hour = datetime.now().hour

        if hour < 12:
            return "Good morning! Your accessible journey starts here."

        elif hour < 17:
            return "Good afternoon! Your accessible journey starts here."

        else:
            return "Good evening! Your accessible journey starts here."


    # ============================================================
    # MAIN UI
    # ============================================================

    def _build_ui(self):

        try:

            self.winfo_toplevel().geometry(
                "1180x760"
            )

            self.winfo_toplevel().minsize(
                980,
                650
            )

        except Exception:
            pass


        self.grid_rowconfigure(
            0,
            weight=1
        )

        self.grid_columnconfigure(
            0,
            weight=0
        )

        self.grid_columnconfigure(
            1,
            weight=1
        )


        # ========================================================
        # SIDEBAR
        # ========================================================

        self.sidebar = ctk.CTkFrame(
            self,
            width=228,
            fg_color=WHITE,
            corner_radius=0,
            border_width=1,
            border_color=BORDER
        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        self.sidebar.grid_propagate(False)


        # ========================================================
        # BRAND
        # ========================================================

        brand = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )

        brand.pack(
            fill="x",
            padx=18,
            pady=(24, 22)
        )


        ctk.CTkLabel(
            brand,
            text="♿",
            width=44,
            height=44,
            corner_radius=14,
            fg_color=BLUE_SOFT,
            text_color=PRIMARY,
            font=("Segoe UI Emoji", 24)
        ).pack(
            side="left"
        )


        brand_text = ctk.CTkFrame(
            brand,
            fg_color="transparent"
        )

        brand_text.pack(
            side="left",
            padx=10
        )


        ctk.CTkLabel(
            brand_text,
            text="WheelGuide",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w"
        )


        ctk.CTkLabel(
            brand_text,
            text="Accessible mobility",
            font=("Segoe UI", 9),
            text_color=TEXT_SECONDARY
        ).pack(
            anchor="w"
        )


        # ========================================================
        # NAVIGATION TITLE
        # ========================================================

        ctk.CTkLabel(
            self.sidebar,
            text="NAVIGATION",
            font=("Segoe UI", 9, "bold"),
            text_color=TEXT_LIGHT
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 8)
        )


        self.nav_buttons = {}


        self._sidebar_items = [

            (
                "⌂",
                "Home",
                self.show_dashboard_home
            ),

            (
                "⌕",
                "Search Destination",
                self.show_route_tab
            ),

            (
                "♿",
                "Accessibility AI",
                self.show_accessibility_tab
            ),

            (
                "▣",
                "Offline Maps",
                self.show_offline_maps_tab
            ),

            (
                "🚧",
                "Report Obstacle",
                self.show_construction_tab
            ),

            (
                "🏥",
                "Hospitals & Repair",
                self.show_recommendations_tab
            ),

            (
                "📄",
                "Medical Reports",
                self.show_medical_tab
            ),

        ]


        for icon, title, command in self._sidebar_items:

            self._create_sidebar_button(
                icon,
                title,
                command
            )


        # ========================================================
        # SAFETY
        # ========================================================

        ctk.CTkLabel(
            self.sidebar,
            text="SAFETY",
            font=("Segoe UI", 9, "bold"),
            text_color=TEXT_LIGHT
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 8)
        )


        self._create_sidebar_button(
            "🚨",
            "Emergency / SOS",
            self.show_emergency_tab,
            danger=True
        )


        # ========================================================
        # USER CARD
        # ========================================================

        self.sidebar_user = ctk.CTkFrame(
            self.sidebar,
            fg_color=BG,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )

        self.sidebar_user.pack(
            side="bottom",
            fill="x",
            padx=14,
            pady=14
        )


        name = (
            self.user.get("full_name")
            or self.user.get("username")
            or "User"
        )


        initials = name[:1].upper()


        ctk.CTkLabel(
            self.sidebar_user,
            text=initials,
            width=36,
            height=36,
            corner_radius=18,
            fg_color=PRIMARY,
            text_color="white",
            font=("Segoe UI", 13, "bold")
        ).pack(
            side="left",
            padx=9,
            pady=9
        )


        user_text = ctk.CTkFrame(
            self.sidebar_user,
            fg_color="transparent"
        )

        user_text.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5)
        )


        ctk.CTkLabel(
            user_text,
            text=name,
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT,
            anchor="w"
        ).pack(
            fill="x"
        )


        ctk.CTkLabel(
            user_text,
            text="View profile",
            font=("Segoe UI", 8),
            text_color=TEXT_SECONDARY,
            anchor="w"
        ).pack(
            fill="x"
        )


        self.sidebar_user.bind(
            "<Button-1>",
            lambda _e: self.show_profile()
        )


        for child in self.sidebar_user.winfo_children():

            child.bind(
                "<Button-1>",
                lambda _e: self.show_profile()
            )


        # ========================================================
        # MAIN AREA
        # ========================================================

        self.app_area = ctk.CTkFrame(
            self,
            fg_color=BG,
            corner_radius=0
        )

        self.app_area.grid(
            row=0,
            column=1,
            sticky="nsew"
        )


        self.app_area.grid_rowconfigure(
            1,
            weight=1
        )

        self.app_area.grid_columnconfigure(
            0,
            weight=1
        )


        # ========================================================
        # TOP BAR
        # ========================================================

        self.topbar = ctk.CTkFrame(
            self.app_area,
            fg_color="transparent",
            height=78
        )

        self.topbar.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=28,
            pady=(16, 0)
        )


        self.topbar.grid_columnconfigure(
            0,
            weight=1
        )


        greeting = ctk.CTkFrame(
            self.topbar,
            fg_color="transparent"
        )

        greeting.grid(
            row=0,
            column=0,
            sticky="w"
        )


        self.greeting_label = ctk.CTkLabel(
            greeting,
            text=f"Hello, {name} 👋",
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT
        )

        self.greeting_label.pack(
            anchor="w"
        )


        self.good_label = ctk.CTkLabel(
            greeting,
            text=self.get_greeting(),
            font=("Segoe UI", 11),
            text_color=TEXT_SECONDARY
        )

        self.good_label.pack(
            anchor="w",
            pady=(2, 0)
        )


        # ========================================================
        # TOP RIGHT ACTIONS
        # ========================================================

        actions = ctk.CTkFrame(
            self.topbar,
            fg_color="transparent"
        )

        actions.grid(
            row=0,
            column=1,
            sticky="e"
        )


        self.notification_button = ctk.CTkButton(
            actions,
            text="🔔",
            width=42,
            height=42,
            corner_radius=12,
            fg_color=WHITE,
            hover_color=BLUE_SOFT,
            text_color=TEXT,
            border_width=1,
            border_color=BORDER,
            font=("Segoe UI Emoji", 17),
            command=self.show_notifications
        )

        self.notification_button.pack(
            side="left",
            padx=(0, 8)
        )


        self.profile_button = ctk.CTkButton(
            actions,
            text=initials,
            width=42,
            height=42,
            corner_radius=21,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            text_color="white",
            font=("Segoe UI", 14, "bold"),
            command=self.show_profile
        )

        self.profile_button.pack(
            side="left"
        )


        # ========================================================
        # CONTENT
        # ========================================================

        self.content = ctk.CTkScrollableFrame(
            self.app_area,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#CBD5E1",
            scrollbar_button_hover_color="#94A3B8"
        )

        self.content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=28,
            pady=(0, 22)
        )


        # Compatibility
        self.bottom_nav = None
        self.plus_button = None
        self.drawer = None

        self.drawer_visible = False
        self.drawer_open = False


        # ========================================================
        # INITIAL HOME PAGE
        # ========================================================

        self.show_dashboard_home()


    # ============================================================
    # SIDEBAR BUTTON
    # ============================================================

    def _create_sidebar_button(
        self,
        icon,
        title,
        command,
        danger=False
    ):

        button = ctk.CTkButton(
            self.sidebar,
            text=f"{icon}   {title}",
            height=42,
            corner_radius=11,
            fg_color=RED_SOFT if danger else "transparent",
            hover_color="#FFDCDC" if danger else BLUE_SOFT,
            text_color=RED if danger else TEXT_SECONDARY,
            font=(
                "Segoe UI",
                10 if len(title) > 17 else 11,
                "bold" if danger else "normal"
            ),
            anchor="w",
            command=command
        )

        button.pack(
            fill="x",
            padx=14,
            pady=2
        )

        self.nav_buttons[title] = button


    # ============================================================
    # PAGE MANAGEMENT
    # ============================================================

    def set_page(self, title):

        self.current_page = title

        if hasattr(self, "good_label"):

            self.good_label.configure(
                text=self.get_greeting()
            )


        for key, button in self.nav_buttons.items():

            active = (

                key.lower() in title.lower()

                or (
                    title == "Dashboard"
                    and key == "Home"
                )

                or (
                    title == "Route Planner"
                    and key == "Search Destination"
                )

                or (
                    title == "Construction"
                    and key == "Report Obstacle"
                )

                or (
                    title == "Emergency"
                    and key == "Emergency / SOS"
                )

                or (
                    title == "Accessibility"
                    and key == "Accessibility AI"
                )

            )


            if active:

                button.configure(
                    fg_color=BLUE_SOFT,
                    text_color=PRIMARY
                )

            else:

                is_danger = (
                    key == "Emergency / SOS"
                )

                button.configure(
                    fg_color=(
                        RED_SOFT
                        if is_danger
                        else "transparent"
                    ),
                    text_color=(
                        RED
                        if is_danger
                        else TEXT_SECONDARY
                    )
                )


    # ============================================================
    # CLEAR CONTENT
    # ============================================================

    def _clear_content(self):

        for widget in self.content.winfo_children():

            widget.destroy()


    # ============================================================
    # HOME
    # ============================================================

    def show_dashboard_home(self):

        self._clear_content()

        self.set_page("Dashboard")


        # --------------------------------------------------------
        # HERO
        # --------------------------------------------------------

        hero = ctk.CTkFrame(
            self.content,
            fg_color=WHITE,
            corner_radius=22,
            border_width=1,
            border_color=BORDER
        )

        hero.pack(
            fill="x",
            pady=(2, 16)
        )


        hero.grid_columnconfigure(
            0,
            weight=1
        )


        left = ctk.CTkFrame(
            hero,
            fg_color="transparent"
        )

        left.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=24,
            pady=22
        )


        ctk.CTkLabel(
            left,
            text="Move with confidence.",
            font=("Segoe UI", 25, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w"
        )


        ctk.CTkLabel(
            left,
            text=(
                "Find accessible routes, understand obstacles "
                "and get help when you need it."
            ),
            font=("Segoe UI", 11),
            text_color=TEXT_SECONDARY,
            wraplength=600,
            justify="left"
        ).pack(
            anchor="w",
            pady=(5, 16)
        )


        # --------------------------------------------------------
        # SEARCH
        # --------------------------------------------------------

        search = ctk.CTkFrame(
            left,
            fg_color=BG,
            corner_radius=13,
            border_width=1,
            border_color=BORDER,
            height=52
        )

        search.pack(
            fill="x"
        )

        search.pack_propagate(False)


        ctk.CTkLabel(
            search,
            text="⌕",
            font=("Segoe UI", 23),
            text_color=TEXT_SECONDARY
        ).pack(
            side="left",
            padx=(15, 6)
        )


        destination_entry = ctk.CTkEntry(
            search,
            placeholder_text="Search a destination...",
            border_width=0,
            fg_color="transparent",
            font=("Segoe UI", 12),
            text_color=TEXT
        )

        destination_entry.pack(
            side="left",
            fill="both",
            expand=True
        )


        def open_route():

            destination = (
                destination_entry.get().strip()
            )

            self.show_route_tab()

            if destination:

                # Route planner currently uses the
                # existing demo graph.
                pass


        ctk.CTkButton(
            search,
            text="Search",
            width=88,
            height=38,
            corner_radius=10,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            font=("Segoe UI", 11, "bold"),
            command=open_route
        ).pack(
            side="right",
            padx=6
        )


        # --------------------------------------------------------
        # EMERGENCY
        # --------------------------------------------------------

        ctk.CTkButton(
            hero,
            text="🚨\nEmergency",
            width=112,
            height=100,
            corner_radius=18,
            fg_color=RED_SOFT,
            hover_color="#FFDCDC",
            text_color=RED,
            font=("Segoe UI Emoji", 12, "bold"),
            command=self.show_emergency_tab
        ).grid(
            row=0,
            column=1,
            padx=(0, 22),
            pady=22
        )


        # --------------------------------------------------------
        # TOOLKIT
        # --------------------------------------------------------

        ctk.CTkLabel(
            self.content,
            text="Your accessibility toolkit",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            pady=(0, 9)
        )


        cards = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        cards.pack(
            fill="x",
            pady=(0, 18)
        )


        for i in range(3):

            cards.grid_columnconfigure(
                i,
                weight=1
            )


        self._home_feature_card(
            cards,
            0,
            "🧭",
            "Accessible Routes",
            "Compare routes with accessibility in mind.",
            BLUE_SOFT,
            PRIMARY,
            self.show_route_tab
        )


        self._home_feature_card(
            cards,
            1,
            "🤖",
            "Accessibility AI",
            "Analyze accessibility information with AI.",
            PURPLE_SOFT,
            PURPLE,
            self.show_accessibility_tab
        )


        self._home_feature_card(
            cards,
            2,
            "🚧",
            "Report an Obstacle",
            "Report construction or obstacles around you.",
            ORANGE_SOFT,
            ORANGE,
            self.show_construction_tab
        )


        # --------------------------------------------------------
        # LOWER SECTION
        # --------------------------------------------------------

        lower = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        lower.pack(
            fill="x"
        )


        lower.grid_columnconfigure(
            0,
            weight=3
        )

        lower.grid_columnconfigure(
            1,
            weight=2
        )


        # --------------------------------------------------------
        # GET STARTED
        # --------------------------------------------------------

        guide = ctk.CTkFrame(
            lower,
            fg_color=WHITE,
            corner_radius=20,
            border_width=1,
            border_color=BORDER
        )

        guide.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8)
        )


        ctk.CTkLabel(
            guide,
            text="Get started",
            font=("Segoe UI", 17, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 3)
        )


        ctk.CTkLabel(
            guide,
            text="Choose what you need right now.",
            font=("Segoe UI", 10),
            text_color=TEXT_SECONDARY
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 12)
        )


        self._home_action_row(
            guide,
            "🗺",
            "Plan an accessible route",
            "Open Route Planner",
            self.show_route_tab
        )


        self._home_action_row(
            guide,
            "🏥",
            "Find useful nearby services",
            "Hospitals & Repair",
            self.show_recommendations_tab
        )


        self._home_action_row(
            guide,
            "📄",
            "Review a medical document",
            "Medical Reports",
            self.show_medical_tab
        )


        # --------------------------------------------------------
        # ACCESSIBILITY STATUS
        # --------------------------------------------------------

        status = ctk.CTkFrame(
            lower,
            fg_color=TEAL_SOFT,
            corner_radius=20,
            border_width=1,
            border_color="#C8EEE8"
        )

        status.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(8, 0)
        )


        ctk.CTkLabel(
            status,
            text="♿",
            font=("Segoe UI Emoji", 32),
            text_color=TEAL_DARK
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 4)
        )


        ctk.CTkLabel(
            status,
            text="Accessibility first",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=20
        )


        ctk.CTkLabel(
            status,
            text=(
                "WheelGuide keeps accessibility, safety "
                "and clear navigation at the center."
            ),
            font=("Segoe UI", 10),
            text_color=TEXT_SECONDARY,
            wraplength=260,
            justify="left"
        ).pack(
            anchor="w",
            padx=20,
            pady=(5, 16)
        )


        ctk.CTkButton(
            status,
            text="Open Accessibility AI →",
            height=40,
            corner_radius=11,
            fg_color=TEAL,
            hover_color=TEAL_DARK,
            font=("Segoe UI", 10, "bold"),
            command=self.show_accessibility_tab
        ).pack(
            fill="x",
            padx=20,
            pady=(0, 20)
        )


    # ============================================================
    # HOME FEATURE CARD
    # ============================================================

    def _home_feature_card(
        self,
        parent,
        column,
        icon,
        title,
        description,
        icon_bg,
        accent,
        command
    ):

        card = ctk.CTkFrame(
            parent,
            fg_color=WHITE,
            corner_radius=17,
            border_width=1,
            border_color=BORDER
        )

        card.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=4
        )


        ctk.CTkLabel(
            card,
            text=icon,
            width=44,
            height=44,
            corner_radius=13,
            fg_color=icon_bg,
            text_color=accent,
            font=("Segoe UI Emoji", 22)
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 10)
        )


        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=15
        )


        ctk.CTkLabel(
            card,
            text=description,
            font=("Segoe UI", 9),
            text_color=TEXT_SECONDARY,
            wraplength=190,
            justify="left"
        ).pack(
            anchor="w",
            padx=15,
            pady=(4, 13)
        )


        ctk.CTkButton(
            card,
            text="Open →",
            height=34,
            corner_radius=9,
            fg_color="transparent",
            hover_color=icon_bg,
            text_color=accent,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            command=command
        ).pack(
            fill="x",
            padx=10,
            pady=(0, 10)
        )


    # ============================================================
    # HOME ACTION ROW
    # ============================================================

    def _home_action_row(
        self,
        parent,
        icon,
        title,
        action,
        command
    ):

        row = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            height=48
        )

        row.pack(
            fill="x",
            padx=12,
            pady=2
        )


        ctk.CTkLabel(
            row,
            text=icon,
            width=34,
            height=34,
            corner_radius=10,
            fg_color=BG,
            font=("Segoe UI Emoji", 16)
        ).pack(
            side="left",
            padx=(4, 9)
        )


        text = ctk.CTkFrame(
            row,
            fg_color="transparent"
        )

        text.pack(
            side="left",
            fill="x",
            expand=True
        )


        ctk.CTkLabel(
            text,
            text=title,
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w"
        )


        ctk.CTkLabel(
            text,
            text=action,
            font=("Segoe UI", 8),
            text_color=TEXT_SECONDARY
        ).pack(
            anchor="w"
        )


        ctk.CTkButton(
            row,
            text="→",
            width=32,
            height=32,
            corner_radius=9,
            fg_color="transparent",
            hover_color=BLUE_SOFT,
            text_color=PRIMARY,
            font=("Segoe UI", 16, "bold"),
            command=command
        ).pack(
            side="right"
        )


    # ============================================================
    # SIMPLE HEADER
    # ============================================================

    def simple_header(
        self,
        title,
        subtitle
    ):

        ctk.CTkLabel(
            self.content,
            text=title,
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            pady=(5, 3)
        )


        ctk.CTkLabel(
            self.content,
            text=subtitle,
            font=("Segoe UI", 11),
            text_color=TEXT_SECONDARY,
            wraplength=650
        ).pack(
            anchor="w",
            pady=(0, 18)
        )


    # ============================================================
    # SIMPLE CARD
    # ============================================================

    def create_simple_card(self):

        card = ctk.CTkFrame(
            self.content,
            fg_color=WHITE,
            corner_radius=18,
            border_width=1,
            border_color=BORDER
        )

        card.pack(
            fill="both",
            expand=True,
            pady=5
        )

        return card


    # ============================================================
    # ACCESSIBILITY AI
    # ============================================================

    def show_accessibility_tab(self):

        self._clear_content()

        self.set_page("Accessibility")


        self.simple_header(
            "♿ Accessibility Score",
            "Check how wheelchair-friendly a place is using AI."
        )


        card = self.create_simple_card()


        ctk.CTkLabel(
            card,
            text="📍 Place Information",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=22,
            pady=(20, 12)
        )


        place_entry = ctk.CTkEntry(
            card,
            placeholder_text="Enter place name",
            height=45,
            corner_radius=12
        )

        place_entry.pack(
            fill="x",
            padx=22,
            pady=6
        )


        desc_box = ctk.CTkTextbox(
            card,
            height=130,
            corner_radius=12
        )

        desc_box.pack(
            fill="x",
            padx=22,
            pady=8
        )


        desc_box.insert(
            "1.0",
            "Enter reviews or details about ramps, "
            "elevators, stairs, toilets, entrances..."
        )


        result_card = ctk.CTkFrame(
            card,
            fg_color="#F8FAFC",
            corner_radius=14
        )

        result_card.pack(
            fill="x",
            padx=22,
            pady=10
        )


        result_label = ctk.CTkLabel(
            result_card,
            text="Your accessibility score will appear here.",
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY,
            justify="left",
            wraplength=600
        )

        result_label.pack(
            anchor="w",
            padx=18,
            pady=18
        )


        def run_score():

            name = place_entry.get().strip()

            if not name:

                result_label.configure(
                    text="⚠ Please enter a place name."
                )

                return


            desc = desc_box.get(
                "1.0",
                "end"
            ).strip()


            result_label.configure(
                text="🔄 AI is analyzing..."
            )


            def worker():

                try:

                    result = get_accessibility_score(
                        name,
                        desc
                    )


                    save_place_score(
                        name,
                        "",
                        self.current_location[0],
                        self.current_location[1],
                        "general",
                        result["score"],
                        result["reasoning"],
                        bool(
                            result.get("has_ramp")
                        ),
                        bool(
                            result.get("has_elevator")
                        ),
                        bool(
                            result.get(
                                "has_accessible_toilet"
                            )
                        )
                    )


                    text = (
                        f"♿ Accessibility Score: "
                        f"{result['score']}/10\n\n"

                        f"Ramp: "
                        f"{'✓ Yes' if result.get('has_ramp') else '✗ No'}\n"

                        f"Elevator: "
                        f"{'✓ Yes' if result.get('has_elevator') else '✗ No'}\n"

                        f"Accessible Toilet: "
                        f"{'✓ Yes' if result.get('has_accessible_toilet') else '✗ No'}\n\n"

                        f"{result['reasoning']}"
                    )


                except Exception as e:

                    text = f"⚠ Error: {e}"


                self.after(
                    0,
                    lambda: result_label.configure(
                        text=text,
                        text_color=TEXT
                    )
                )


            threading.Thread(
                target=worker,
                daemon=True
            ).start()


        ctk.CTkButton(
            card,
            text="✨ Analyze Accessibility",
            height=47,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            font=("Segoe UI", 13, "bold"),
            command=run_score
        ).pack(
            fill="x",
            padx=22,
            pady=(5, 22)
        )


    # ============================================================
    # CONSTRUCTION / OBSTACLE REPORTING
    # ============================================================

    def show_construction_tab(self):
        """
        Report Obstacle / Construction Zone.

        Restored method: this callback is wired to the sidebar
        ("Report Obstacle") and to quick-action buttons elsewhere in
        this file, but the implementation was missing from the class
        entirely, which is exactly the
        "'DashboardFrame' object has no attribute 'show_construction_tab'"
        crash described in the project brief. This implementation
        follows the same pattern as show_accessibility_tab: an upload
        + AI analysis flow, run off the GUI thread, with an honest
        "unknown"/error fallback rather than fabricated results.

        NOTE: AI/construction.py was not provided with this request,
        so detect_construction_in_image() and report_construction_zone()
        are called defensively (try/except, tolerant of either a dict
        or plain-text return). Please verify their exact signatures
        against your real AI/construction.py and adjust the two worker
        functions below if the parameter names differ.
        """

        self._clear_content()

        self.set_page("Report Obstacle")


        self.simple_header(
            "🚧 Report Obstacle / Construction Zone",
            "Help other wheelchair users by reporting blocked or "
            "under-construction paths."
        )


        card = self.create_simple_card()


        ctk.CTkLabel(
            card,
            text="📷 Obstacle Photo",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=22,
            pady=(20, 12)
        )


        selected_image_path = {"path": None}

        image_status_label = ctk.CTkLabel(
            card,
            text="No image selected.",
            font=("Segoe UI", 11),
            text_color=TEXT_SECONDARY
        )

        image_status_label.pack(
            anchor="w",
            padx=22,
            pady=(0, 6)
        )


        def choose_image():

            path = filedialog.askopenfilename(
                title="Select obstacle photo",
                filetypes=[
                    ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                    ("All files", "*.*")
                ]
            )

            if not path:
                return

            selected_image_path["path"] = path

            image_status_label.configure(
                text=f"Selected: {os.path.basename(path)}",
                text_color=TEXT
            )


        ctk.CTkButton(
            card,
            text="📁 Choose Photo",
            height=42,
            corner_radius=12,
            fg_color=ORANGE,
            hover_color="#D97706",
            font=("Segoe UI", 12, "bold"),
            command=choose_image
        ).pack(
            fill="x",
            padx=22,
            pady=(0, 10)
        )


        ctk.CTkLabel(
            card,
            text="📝 Description",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=22,
            pady=(10, 12)
        )


        desc_box = ctk.CTkTextbox(
            card,
            height=110,
            corner_radius=12
        )

        desc_box.pack(
            fill="x",
            padx=22,
            pady=(0, 10)
        )

        desc_box.insert(
            "1.0",
            "Describe the obstacle (e.g. blocked ramp, construction "
            "debris, no accessible path)..."
        )


        result_card = ctk.CTkFrame(
            card,
            fg_color="#F8FAFC",
            corner_radius=14
        )

        result_card.pack(
            fill="x",
            padx=22,
            pady=10
        )


        result_label = ctk.CTkLabel(
            result_card,
            text="Detection and report status will appear here.",
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY,
            justify="left",
            wraplength=600
        )

        result_label.pack(
            anchor="w",
            padx=18,
            pady=18
        )


        def submit_report():

            desc = desc_box.get(
                "1.0",
                "end"
            ).strip()

            image_path = selected_image_path["path"]

            if not image_path and not desc:

                result_label.configure(
                    text="⚠ Please add a photo, a description, or both.",
                    text_color=TEXT
                )

                return


            result_label.configure(
                text="🔄 Analyzing and submitting report...",
                text_color=TEXT_SECONDARY
            )


            def worker():

                detection_text = ""

                # ------------------------------------------------------
                # AI image detection (optional, best-effort)
                # ------------------------------------------------------

                if image_path:

                    try:

                        detection = detect_construction_in_image(
                            image_path
                        )

                        if isinstance(detection, dict):

                            detected = detection.get(
                                "detected",
                                "unknown"
                            )

                            confidence = detection.get(
                                "confidence",
                                "unknown"
                            )

                            detection_text = (
                                f"AI detection: {detected} "
                                f"(confidence: {confidence})\n\n"
                            )

                        else:

                            detection_text = (
                                f"AI detection: {detection}\n\n"
                            )

                    except Exception as e:

                        detection_text = (
                            "AI image detection unavailable "
                            f"({e}).\n\n"
                        )

                # ------------------------------------------------------
                # Submit the report to the existing backend
                # ------------------------------------------------------

                try:

                    report_construction_zone(
                        self.current_location[0],
                        self.current_location[1],
                        desc,
                        image_path
                    )

                    status_text = (
                        detection_text
                        + "✓ Report submitted. Thank you for helping "
                        "keep routes accessible."
                    )

                except Exception as e:

                    status_text = (
                        detection_text
                        + f"⚠ Could not submit report: {e}"
                    )

                self.after(
                    0,
                    lambda: result_label.configure(
                        text=status_text,
                        text_color=TEXT
                    )
                )

            threading.Thread(
                target=worker,
                daemon=True
            ).start()


        ctk.CTkButton(
            card,
            text="🚧 Submit Obstacle Report",
            height=47,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            font=("Segoe UI", 13, "bold"),
            command=submit_report
        ).pack(
            fill="x",
            padx=22,
            pady=(5, 22)
        )


    # ============================================================
    # STAIRCASE DETECTION
    # ============================================================

    def show_staircase_tab(self):
        """
        Staircase Detection.

        Restored method: referenced from the Services quick-action
        card ("Staircase Detection") but was missing from the class,
        the same class of bug as show_construction_tab above. Uses
        the already-imported AI.staircase functions
        (detect_staircase_in_image, detect_staircase_from_webcam).

        NOTE: AI/staircase.py was not provided with this request, so
        both calls are wrapped defensively. Verify their exact
        signatures against your real AI/staircase.py.
        """

        self._clear_content()

        self.set_page("Staircase Detection")


        self.simple_header(
            "📷 Staircase Detection",
            "Use AI to detect stairs from a photo or your webcam."
        )


        card = self.create_simple_card()


        result_card = ctk.CTkFrame(
            card,
            fg_color="#F8FAFC",
            corner_radius=14
        )

        result_card.pack(
            fill="x",
            padx=22,
            pady=(20, 10)
        )


        result_label = ctk.CTkLabel(
            result_card,
            text="Detection results will appear here.",
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY,
            justify="left",
            wraplength=600
        )

        result_label.pack(
            anchor="w",
            padx=18,
            pady=18
        )


        def format_result(result):

            if isinstance(result, dict):

                detected = result.get(
                    "detected",
                    "unknown"
                )

                confidence = result.get(
                    "confidence",
                    "unknown"
                )

                return (
                    f"Staircase detected: {detected}\n"
                    f"Confidence: {confidence}"
                )

            return str(result)


        def run_from_image():

            path = filedialog.askopenfilename(
                title="Select a photo",
                filetypes=[
                    ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                    ("All files", "*.*")
                ]
            )

            if not path:
                return

            result_label.configure(
                text="🔄 Analyzing photo...",
                text_color=TEXT_SECONDARY
            )


            def worker():

                try:

                    result = detect_staircase_in_image(
                        path
                    )

                    text = format_result(
                        result
                    )

                except Exception as e:

                    text = f"⚠ Error: {e}"

                self.after(
                    0,
                    lambda: result_label.configure(
                        text=text,
                        text_color=TEXT
                    )
                )

            threading.Thread(
                target=worker,
                daemon=True
            ).start()


        def run_from_webcam():

            result_label.configure(
                text="🔄 Analyzing webcam feed...",
                text_color=TEXT_SECONDARY
            )


            def worker():

                try:

                    result = detect_staircase_from_webcam()

                    text = format_result(
                        result
                    )

                except Exception as e:

                    text = f"⚠ Error: {e}"

                self.after(
                    0,
                    lambda: result_label.configure(
                        text=text,
                        text_color=TEXT
                    )
                )

            threading.Thread(
                target=worker,
                daemon=True
            ).start()


        ctk.CTkButton(
            card,
            text="📁 Detect from Photo",
            height=47,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            font=("Segoe UI", 13, "bold"),
            command=run_from_image
        ).pack(
            fill="x",
            padx=22,
            pady=(0, 10)
        )


        ctk.CTkButton(
            card,
            text="🎥 Detect from Webcam",
            height=47,
            corner_radius=12,
            fg_color=PURPLE,
            hover_color="#6D28D9",
            font=("Segoe UI", 13, "bold"),
            command=run_from_webcam
        ).pack(
            fill="x",
            padx=22,
            pady=(0, 22)
        )


    # ============================================================
    # ROUTE PLANNER
    # ============================================================

    def show_route_tab(self):

        self._clear_content()

        self.set_page("Route Planner")


        self.simple_header(
            "🗺 Accessible Route Planner",
            "Find routes that prioritize accessibility and avoid stairs."
        )


        card = self.create_simple_card()


        result_box = ctk.CTkTextbox(
            card,
            height=220,
            corner_radius=12
        )

        result_box.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )


        result_box.insert(
            "1.0",
            "Enter a destination above or compare the "
            "available demo routes below."
        )


        def run_route():

            try:

                graph = build_demo_graph()

                comparison = compare_shortest_vs_accessible(
                    graph,
                    "A_Start",
                    "E_Destination"
                )


                result_box.delete(
                    "1.0",
                    "end"
                )


                result_box.insert(
                    "end",
                    "🚗 SHORTEST ROUTE\n\n"
                )


                result_box.insert(
                    "end",
                    f"{comparison['shortest_route']}\n\n"
                )


                result_box.insert(
                    "end",
                    "♿ ACCESSIBLE ROUTE\n\n"
                )


                result_box.insert(
                    "end",
                    f"{comparison['accessible_route']}"
                )


            except Exception as e:

                result_box.delete(
                    "1.0",
                    "end"
                )

                result_box.insert(
                    "end",
                    f"⚠ Error: {e}"
                )


        ctk.CTkButton(
            card,
            text="🧭 Compare Routes",
            height=47,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            command=run_route
        ).pack(
            fill="x",
            padx=20,
            pady=(0, 20)
        )


    # ============================================================
    # OFFLINE MAPS
    # ============================================================

    def show_offline_maps_tab(self):

        self._clear_content()

        self.set_page("Offline Maps")


        self.simple_header(
            "📍 Offline Maps",
            "Save your area so important map information remains available."
        )


        card = self.create_simple_card()


        status_label = ctk.CTkLabel(
            card,
            text="Ready to cache your current area.",
            font=("Segoe UI", 13),
            text_color=TEXT_SECONDARY
        )

        status_label.pack(
            anchor="w",
            padx=20,
            pady=20
        )


        def do_cache():

            status_label.configure(
                text="🔄 Downloading map tiles..."
            )


            def worker():

                try:

                    result = cache_area_tiles(
                        *self.current_location
                    )


                    text = (
                        f"✓ Cached "
                        f"{result['downloaded']} tiles "
                        f"({result['failed']} failed)."
                    )


                except Exception as e:

                    text = f"⚠ Error: {e}"


                self.after(
                    0,
                    lambda: status_label.configure(
                        text=text
                    )
                )


            threading.Thread(
                target=worker,
                daemon=True
            ).start()


        def open_offline_map():

            try:

                path = build_offline_map(
                    self.current_location
                )


                webbrowser.open(
                    f"file://{os.path.abspath(path)}"
                )


            except Exception as e:

                messagebox.showerror(
                    "Offline Map",
                    str(e)
                )


        ctk.CTkButton(
            card,
            text="⬇ Cache My Area",
            height=47,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            command=do_cache
        ).pack(
            fill="x",
            padx=20,
            pady=8
        )


        ctk.CTkButton(
            card,
            text="🗺 Open Offline Map",
            height=47,
            corner_radius=12,
            fg_color=TEAL,
            hover_color=TEAL_DARK,
            command=open_offline_map
        ).pack(
            fill="x",
            padx=20,
            pady=(0, 20)
        )


    # ============================================================
    # STAIRCASE DETECTION
    # ============================================================
    def show_recommendations_tab(self):
        """
        WheelGuide AI Services Center
        --------------------------------
        Modern nearby healthcare + wheelchair repair discovery page.

        Features:
            - Modern card-based UI
            - Hospitals / Repair Shops tabs
            - Real-time background loading
            - Refresh
            - Current location display
            - Accessibility information
            - Emergency information
            - Phone button
            - Google Maps directions
            - Save-style action
            - No giant textbox
            - Safe UNKNOWN handling
            - Offline results supported by backend
        """

        self._clear_content()
        self.set_page("Hospitals & Repair")

        # --------------------------------------------------------------
        # PAGE CONTAINER
        # --------------------------------------------------------------

        page = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        page.pack(
            fill="both",
            expand=True
        )

        # --------------------------------------------------------------
        # HERO HEADER
        # --------------------------------------------------------------

        hero = ctk.CTkFrame(
            page,
            fg_color="#0F172A",
            corner_radius=24
        )
        hero.pack(
            fill="x",
            pady=(0, 14)
        )

        hero.grid_columnconfigure(
            0,
            weight=1
        )

        hero_left = ctk.CTkFrame(
            hero,
            fg_color="transparent"
        )
        hero_left.grid(
            row=0,
            column=0,
            sticky="w",
            padx=25,
            pady=22
        )

        ctk.CTkLabel(
            hero_left,
            text="Healthcare & Mobility",
            font=("Segoe UI", 24, "bold"),
            text_color="#FFFFFF"
        ).pack(
            anchor="w"
        )

        ctk.CTkLabel(
            hero_left,
            text=(
                "Find nearby hospitals and wheelchair services "
                "with accessibility information."
            ),
            font=("Segoe UI", 10),
            text_color="#CBD5E1",
            wraplength=600,
            justify="left"
        ).pack(
            anchor="w",
            pady=(5, 12)
        )

        # --------------------------------------------------------------
        # LOCATION PILL
        # --------------------------------------------------------------

        location_frame = ctk.CTkFrame(
            hero_left,
            fg_color="#1E293B",
            corner_radius=12
        )
        location_frame.pack(
            anchor="w"
        )

        ctk.CTkLabel(
            location_frame,
            text="●",
            text_color="#22C55E",
            font=("Segoe UI", 12, "bold")
        ).pack(
            side="left",
            padx=(12, 5),
            pady=8
        )

        location_text = ctk.CTkLabel(
            location_frame,
            text=(
                f"Current location  "
                f"{self.current_location[0]:.5f}, "
                f"{self.current_location[1]:.5f}"
            ),
            font=("Segoe UI", 9, "bold"),
            text_color="#E2E8F0"
        )
        location_text.pack(
            side="left",
            padx=(0, 12)
        )

        # --------------------------------------------------------------
        # REFRESH BUTTON
        # --------------------------------------------------------------

        refresh_btn = ctk.CTkButton(
            hero,
            text="↻",
            width=45,
            height=45,
            corner_radius=14,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            font=("Segoe UI", 22, "bold")
        )
        refresh_btn.grid(
            row=0,
            column=1,
            padx=22,
            pady=22,
            sticky="ne"
        )

        # --------------------------------------------------------------
        # QUICK STATS
        # --------------------------------------------------------------

        stats = ctk.CTkFrame(
            page,
            fg_color="transparent"
        )
        stats.pack(
            fill="x",
            pady=(0, 14)
        )

        for i in range(3):
            stats.grid_columnconfigure(
                i,
                weight=1
            )

        stat_hospitals = self._service_stat_card(
            stats,
            0,
            "🏥",
            "Hospitals",
            "Searching...",
            "#EAF2FF",
            PRIMARY
        )

        stat_repair = self._service_stat_card(
            stats,
            1,
            "♿",
            "Repair Services",
            "Searching...",
            "#E7FAF7",
            TEAL
        )

        stat_accessible = self._service_stat_card(
            stats,
            2,
            "✓",
            "Accessibility",
            "Checking...",
            "#F2EDFF",
            PURPLE
        )

        # --------------------------------------------------------------
        # TABS
        # --------------------------------------------------------------

        tab_bar = ctk.CTkFrame(
            page,
            fg_color=WHITE,
            corner_radius=16,
            border_width=1,
            border_color=BORDER
        )
        tab_bar.pack(
            fill="x",
            pady=(0, 10)
        )

        tab_bar.grid_columnconfigure(
            0,
            weight=1
        )

        tab_bar.grid_columnconfigure(
            1,
            weight=1
        )

        self._service_active_tab = "hospitals"

        hospitals_tab = ctk.CTkButton(
            tab_bar,
            text="🏥  Hospitals",
            height=45,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            font=("Segoe UI", 11, "bold"),
            command=lambda: show_tab("hospitals")
        )
        hospitals_tab.grid(
            row=0,
            column=0,
            padx=7,
            pady=7,
            sticky="ew"
        )

        repair_tab = ctk.CTkButton(
            tab_bar,
            text="♿  Wheelchair Repair",
            height=45,
            corner_radius=12,
            fg_color="transparent",
            hover_color=BG,
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 11, "bold"),
            command=lambda: show_tab("repair")
        )
        repair_tab.grid(
            row=0,
            column=1,
            padx=7,
            pady=7,
            sticky="ew"
        )

        last_updated_label = ctk.CTkLabel(
            page,
            text="",
            font=("Segoe UI", 9),
            text_color=TEXT_LIGHT
        )
        last_updated_label.pack(
            anchor="e",
            pady=(0, 6)
        )

        # --------------------------------------------------------------
        # SEARCH / FILTER / SORT TOOLBAR
        # --------------------------------------------------------------

        toolbar = ctk.CTkFrame(
            page,
            fg_color=WHITE,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )
        toolbar.pack(
            fill="x",
            pady=(0, 10)
        )

        toolbar.grid_columnconfigure(
            0,
            weight=1
        )

        search_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="🔎 Search by name or address...",
            height=38,
            corner_radius=10,
            border_width=0,
            fg_color="#F1F5F9"
        )
        search_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(12, 8),
            pady=10
        )

        sort_menu = ctk.CTkOptionMenu(
            toolbar,
            values=[
                "Nearest first",
                "Name A-Z"
            ],
            width=140,
            height=38,
            corner_radius=10,
            fg_color="#F1F5F9",
            button_color="#E2E8F0",
            button_hover_color="#CBD5E1",
            text_color=TEXT,
            dropdown_fg_color=WHITE
        )
        sort_menu.set("Nearest first")
        sort_menu.grid(
            row=0,
            column=1,
            padx=(0, 8),
            pady=10
        )

        accessible_only_var = ctk.BooleanVar(
            value=False
        )

        accessible_only_check = ctk.CTkCheckBox(
            toolbar,
            text="♿ Accessible only",
            variable=accessible_only_var,
            font=("Segoe UI", 10, "bold"),
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=5
        )
        accessible_only_check.grid(
            row=0,
            column=2,
            padx=(0, 12),
            pady=10
        )

        # --------------------------------------------------------------
        # RESULTS AREA
        # --------------------------------------------------------------

        results_container = ctk.CTkFrame(
            page,
            fg_color="transparent"
        )
        results_container.pack(
            fill="both",
            expand=True
        )

        results_count_label = ctk.CTkLabel(
            results_container,
            text="",
            font=("Segoe UI", 9),
            text_color=TEXT_SECONDARY
        )
        results_count_label.pack(
            anchor="w",
            padx=4,
            pady=(0, 4)
        )

        results_scroll = ctk.CTkScrollableFrame(
            results_container,
            fg_color="transparent",
            corner_radius=0
        )
        results_scroll.pack(
            fill="both",
            expand=True
        )

        # --------------------------------------------------------------
        # STATE
        # --------------------------------------------------------------

        services_data = {
            "hospitals": [],
            "repair": []
        }

        fetch_errors = {
            "hospitals": None,
            "repair": None
        }

        loading_label = None

        # --------------------------------------------------------------
        # OPEN GOOGLE MAPS
        # --------------------------------------------------------------

        def open_directions(item):

            try:

                lat = item.get("lat")
                lon = item.get("lon")

                if lat is None or lon is None:
                    messagebox.showwarning(
                        "Location unavailable",
                        "This place does not have valid map coordinates."
                    )
                    return

                url = (
                    "https://www.google.com/maps/dir/?api=1"
                    f"&destination={lat},{lon}"
                )

                webbrowser.open(
                    url
                )

            except Exception as e:

                messagebox.showerror(
                    "Maps Error",
                    str(e)
                )

        # --------------------------------------------------------------
        # OPEN PLACE SEARCH
        # --------------------------------------------------------------

        def open_place_search(item):

            try:

                name = item.get(
                    "name",
                    "hospital"
                )

                lat = item.get(
                    "lat"
                )

                lon = item.get(
                    "lon"
                )

                if lat is not None and lon is not None:

                    url = (
                        "https://www.google.com/maps/search/"
                        f"?api=1&query={lat},{lon}"
                    )

                else:

                    from urllib.parse import quote

                    url = (
                        "https://www.google.com/maps/search/"
                        f"?api=1&query={quote(name)}"
                    )

                webbrowser.open(
                    url
                )

            except Exception as e:

                messagebox.showerror(
                    "Maps Error",
                    str(e)
                )

        # --------------------------------------------------------------
        # PHONE
        # --------------------------------------------------------------

        def call_place(item):

            phone = str(
                item.get(
                    "phone",
                    ""
                )
            ).strip()

            if not phone or phone.upper() == "N/A":

                messagebox.showinfo(
                    "Phone unavailable",
                    "No phone number is available for this location."
                )

                return

            try:

                webbrowser.open(
                    f"tel:{phone}"
                )

            except Exception:

                messagebox.showinfo(
                    "Phone number",
                    phone
                )

        # --------------------------------------------------------------
        # CLEAR RESULTS
        # --------------------------------------------------------------

        def page_is_alive():
            """
            Returns False once the user has navigated away from this
            page and its widgets have been destroyed. Guards against
            the self.after()-delayed callbacks below (_initial_render,
            update_ui) firing after the page no longer exists, which
            previously raised:
            _tkinter.TclError: bad window path name
            """

            try:
                return bool(results_scroll.winfo_exists())
            except Exception:
                return False

        def clear_results():

            if not page_is_alive():
                return

            for widget in results_scroll.winfo_children():

                widget.destroy()

        # --------------------------------------------------------------
        # LOADING UI
        # --------------------------------------------------------------

        def show_loading():

            clear_results()

            loading_card = ctk.CTkFrame(
                results_scroll,
                fg_color=WHITE,
                corner_radius=20,
                border_width=1,
                border_color=BORDER
            )
            loading_card.pack(
                fill="x",
                padx=4,
                pady=8
            )

            ctk.CTkLabel(
                loading_card,
                text="◌",
                font=("Segoe UI", 38),
                text_color=PRIMARY
            ).pack(
                pady=(28, 5)
            )

            ctk.CTkLabel(
                loading_card,
                text="Finding nearby places...",
                font=("Segoe UI", 15, "bold"),
                text_color=TEXT
            ).pack()

            ctk.CTkLabel(
                loading_card,
                text=(
                    "Checking available location and accessibility "
                    "information."
                ),
                font=("Segoe UI", 10),
                text_color=TEXT_SECONDARY
            ).pack(
                pady=(4, 28)
            )

        # --------------------------------------------------------------
        # ACCESSIBILITY BADGE
        # --------------------------------------------------------------

        def accessibility_badge(parent, value):

            value = str(
                value or "unknown"
            ).lower()

            if value == "yes":

                return ctk.CTkLabel(
                    parent,
                    text="♿ Accessible",
                    fg_color="#DCFCE7",
                    text_color="#15803D",
                    corner_radius=9,
                    font=("Segoe UI", 9, "bold"),
                    padx=9,
                    pady=4
                )

            if value == "limited":

                return ctk.CTkLabel(
                    parent,
                    text="♿ Limited",
                    fg_color="#FEF3C7",
                    text_color="#B45309",
                    corner_radius=9,
                    font=("Segoe UI", 9, "bold"),
                    padx=9,
                    pady=4
                )

            if value == "no":

                return ctk.CTkLabel(
                    parent,
                    text="♿ Not accessible",
                    fg_color="#FEE2E2",
                    text_color="#B91C1C",
                    corner_radius=9,
                    font=("Segoe UI", 9, "bold"),
                    padx=9,
                    pady=4
                )

            return ctk.CTkLabel(
                parent,
                text="♿ Accessibility unknown",
                fg_color="#F1F5F9",
                text_color="#64748B",
                corner_radius=9,
                font=("Segoe UI", 9, "bold"),
                padx=9,
                pady=4
            )

        # --------------------------------------------------------------
        # SERVICE CARD
        # --------------------------------------------------------------

        def create_service_card(
            parent,
            item,
            service_type
        ):

            card = ctk.CTkFrame(
                parent,
                fg_color=WHITE,
                corner_radius=20,
                border_width=1,
                border_color=BORDER
            )
            card.pack(
                fill="x",
                padx=4,
                pady=7
            )

            # ----------------------------------------------------------
            # HEADER
            # ----------------------------------------------------------

            header = ctk.CTkFrame(
                card,
                fg_color="transparent"
            )
            header.pack(
                fill="x",
                padx=17,
                pady=(16, 5)
            )

            icon_bg = (
                BLUE_SOFT
                if service_type == "hospital"
                else TEAL_SOFT
            )

            icon_color = (
                PRIMARY
                if service_type == "hospital"
                else TEAL_DARK
            )

            icon = (
                "🏥"
                if service_type == "hospital"
                else "♿"
            )

            ctk.CTkLabel(
                header,
                text=icon,
                width=50,
                height=50,
                corner_radius=15,
                fg_color=icon_bg,
                text_color=icon_color,
                font=("Segoe UI Emoji", 23)
            ).pack(
                side="left"
            )

            title_frame = ctk.CTkFrame(
                header,
                fg_color="transparent"
            )
            title_frame.pack(
                side="left",
                fill="x",
                expand=True,
                padx=12
            )

            name = str(
                item.get(
                    "name",
                    "Unnamed place"
                )
            )

            ctk.CTkLabel(
                title_frame,
                text=name,
                font=("Segoe UI", 13, "bold"),
                text_color=TEXT,
                anchor="w"
            ).pack(
                anchor="w"
            )

            distance = item.get(
                "distance_km",
                "?"
            )

            ctk.CTkLabel(
                title_frame,
                text=f"📍 {distance} km away",
                font=("Segoe UI", 9),
                text_color=TEXT_SECONDARY
            ).pack(
                anchor="w",
                pady=(2, 0)
            )

            # ----------------------------------------------------------
            # ACCESSIBILITY
            # ----------------------------------------------------------

            badge_row = ctk.CTkFrame(
                card,
                fg_color="transparent"
            )
            badge_row.pack(
                fill="x",
                padx=17,
                pady=(6, 8)
            )

            if service_type == "hospital":

                badge = accessibility_badge(
                    badge_row,
                    item.get(
                        "wheelchair",
                        "unknown"
                    )
                )
                badge.pack(
                    side="left"
                )

                emergency = str(
                    item.get(
                        "emergency",
                        "unknown"
                    )
                ).lower()

                if emergency == "yes":

                    ctk.CTkLabel(
                        badge_row,
                        text="🚑 Emergency",
                        fg_color="#FEE2E2",
                        text_color="#B91C1C",
                        corner_radius=9,
                        font=("Segoe UI", 9, "bold"),
                        padx=9,
                        pady=4
                    ).pack(
                        side="left",
                        padx=6
                    )

                elif emergency == "unknown":

                    ctk.CTkLabel(
                        badge_row,
                        text="Emergency info unknown",
                        fg_color="#F1F5F9",
                        text_color="#64748B",
                        corner_radius=9,
                        font=("Segoe UI", 9),
                        padx=8,
                        pady=4
                    ).pack(
                        side="left",
                        padx=6
                    )

            else:

                ctk.CTkLabel(
                    badge_row,
                    text="🛠 Mobility repair service",
                    fg_color=TEAL_SOFT,
                    text_color=TEAL_DARK,
                    corner_radius=9,
                    font=("Segoe UI", 9, "bold"),
                    padx=9,
                    pady=4
                ).pack(
                    side="left"
                )

            # ----------------------------------------------------------
            # INFORMATION GRID
            # ----------------------------------------------------------

            info = ctk.CTkFrame(
                card,
                fg_color="#F8FAFC",
                corner_radius=14
            )
            info.pack(
                fill="x",
                padx=17,
                pady=(2, 10)
            )

            address = str(
                item.get(
                    "address",
                    "N/A"
                )
            )

            if not address or address == "N/A":

                address = "Address information unavailable"

            ctk.CTkLabel(
                info,
                text=f"📍 {address}",
                font=("Segoe UI", 9),
                text_color=TEXT_SECONDARY,
                wraplength=600,
                justify="left"
            ).pack(
                anchor="w",
                padx=12,
                pady=(10, 4)
            )

            phone = str(
                item.get(
                    "phone",
                    "N/A"
                )
            )

            has_extra_rows = bool(
                item.get("opening_hours")
            ) or bool(
                item.get("website")
            )

            ctk.CTkLabel(
                info,
                text=f"📞 {phone}",
                font=("Segoe UI", 9),
                text_color=TEXT_SECONDARY
            ).pack(
                anchor="w",
                padx=12,
                pady=(0, 10 if not has_extra_rows else 4)
            )

            hours = item.get("opening_hours")

            if hours and str(hours).strip().upper() not in (
                "N/A",
                "UNKNOWN"
            ):

                ctk.CTkLabel(
                    info,
                    text=f"🕐 {hours}",
                    font=("Segoe UI", 9),
                    text_color=TEXT_SECONDARY,
                    wraplength=600,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=12,
                    pady=(0, 4)
                )

            website = item.get("website")

            if website and str(website).strip().upper() not in (
                "N/A",
                "UNKNOWN"
            ):

                ctk.CTkLabel(
                    info,
                    text=f"🌐 {website}",
                    font=("Segoe UI", 9),
                    text_color=PRIMARY,
                    wraplength=600,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=12,
                    pady=(0, 10)
                )

            # ----------------------------------------------------------
            # BUTTONS
            # ----------------------------------------------------------

            actions = ctk.CTkFrame(
                card,
                fg_color="transparent"
            )
            actions.pack(
                fill="x",
                padx=17,
                pady=(0, 16)
            )

            ctk.CTkButton(
                actions,
                text="🧭 Directions",
                height=39,
                corner_radius=11,
                fg_color=PRIMARY,
                hover_color=PRIMARY_DARK,
                font=("Segoe UI", 9, "bold"),
                command=lambda x=item: open_directions(x)
            ).pack(
                side="left",
                fill="x",
                expand=True
            )

            ctk.CTkButton(
                actions,
                text="🗺 Maps",
                width=95,
                height=39,
                corner_radius=11,
                fg_color=BLUE_SOFT,
                hover_color="#DCE9FF",
                text_color=PRIMARY,
                font=("Segoe UI", 9, "bold"),
                command=lambda x=item: open_place_search(x)
            ).pack(
                side="left",
                padx=6
            )

            ctk.CTkButton(
                actions,
                text="📞",
                width=48,
                height=39,
                corner_radius=11,
                fg_color="#F1F5F9",
                hover_color="#E2E8F0",
                text_color=TEXT,
                font=("Segoe UI Emoji", 14),
                command=lambda x=item: call_place(x)
            ).pack(
                side="right"
            )

        # --------------------------------------------------------------
        # EMPTY STATE
        # --------------------------------------------------------------

        def show_empty(service_type):

            clear_results()

            card = ctk.CTkFrame(
                results_scroll,
                fg_color=WHITE,
                corner_radius=20,
                border_width=1,
                border_color=BORDER
            )
            card.pack(
                fill="x",
                padx=4,
                pady=8
            )

            icon = (
                "🏥"
                if service_type == "hospitals"
                else "♿"
            )

            title = (
                "No hospitals found nearby"
                if service_type == "hospitals"
                else "No wheelchair repair services found nearby"
            )

            ctk.CTkLabel(
                card,
                text=icon,
                font=("Segoe UI Emoji", 40)
            ).pack(
                pady=(30, 8)
            )

            ctk.CTkLabel(
                card,
                text=title,
                font=("Segoe UI", 15, "bold"),
                text_color=TEXT
            ).pack()

            ctk.CTkLabel(
                card,
                text=(
                    "Try refreshing or increasing the search radius."
                ),
                font=("Segoe UI", 10),
                text_color=TEXT_SECONDARY
            ).pack(
                pady=(4, 30)
            )

        # --------------------------------------------------------------
        # ERROR STATE
        # --------------------------------------------------------------

        def show_error(service_type, error_text):

            clear_results()

            card = ctk.CTkFrame(
                results_scroll,
                fg_color="#FFF5F5",
                corner_radius=20,
                border_width=1,
                border_color="#FCA5A5"
            )
            card.pack(
                fill="x",
                padx=4,
                pady=8
            )

            ctk.CTkLabel(
                card,
                text="⚠",
                font=("Segoe UI Emoji", 34),
                text_color=RED
            ).pack(
                pady=(26, 6)
            )

            ctk.CTkLabel(
                card,
                text="Couldn't reach the service right now",
                font=("Segoe UI", 14, "bold"),
                text_color=TEXT
            ).pack()

            ctk.CTkLabel(
                card,
                text=(
                    f"{error_text}\n"
                    "Showing offline/demo results if available. "
                    "Try Refresh once you're back online."
                ),
                font=("Segoe UI", 10),
                text_color=TEXT_SECONDARY,
                wraplength=560,
                justify="center"
            ).pack(
                pady=(4, 26)
            )

        # --------------------------------------------------------------
        # FILTER + SORT
        # --------------------------------------------------------------

        def filter_and_sort(items, service_type):

            query = search_entry.get().strip().lower()

            filtered = []

            for item in items:

                if query:

                    haystack = (
                        str(
                            item.get("name", "")
                        )
                        + " "
                        + str(
                            item.get("address", "")
                        )
                    ).lower()

                    if query not in haystack:
                        continue

                if (
                    accessible_only_var.get()
                    and service_type == "hospitals"
                ):

                    wheelchair = str(
                        item.get(
                            "wheelchair",
                            "unknown"
                        )
                    ).lower()

                    if wheelchair != "yes":
                        continue

                filtered.append(item)

            def distance_key(entry):

                try:
                    return float(
                        entry.get(
                            "distance_km",
                            float("inf")
                        )
                    )
                except (TypeError, ValueError):
                    return float("inf")

            if sort_menu.get() == "Name A-Z":

                filtered.sort(
                    key=lambda entry: str(
                        entry.get(
                            "name",
                            ""
                        )
                    ).lower()
                )

            else:

                filtered.sort(
                    key=distance_key
                )

            return filtered

        # --------------------------------------------------------------
        # RENDER
        # --------------------------------------------------------------

        def render_results(service_type):

            clear_results()

            error_text = fetch_errors.get(
                service_type
            )

            raw_items = services_data.get(
                service_type,
                []
            )

            if not raw_items and error_text:

                results_count_label.configure(
                    text=""
                )

                show_error(
                    service_type,
                    error_text
                )

                return

            items = filter_and_sort(
                raw_items,
                service_type
            )

            if not items:

                results_count_label.configure(
                    text=""
                )

                show_empty(
                    service_type
                )

                return

            noun = (
                "hospital"
                if service_type == "hospitals"
                else "repair service"
            )

            results_count_label.configure(
                text=(
                    f"{len(items)} {noun}"
                    f"{'s' if len(items) != 1 else ''} found"
                )
            )

            for item in items:

                create_service_card(
                    results_scroll,
                    item,
                    "hospital"
                    if service_type == "hospitals"
                    else "repair"
                )

        def on_filters_changed(*_args):

            render_results(
                self._service_active_tab
            )

        search_entry.bind(
            "<KeyRelease>",
            on_filters_changed
        )

        sort_menu.configure(
            command=on_filters_changed
        )

        accessible_only_var.trace_add(
            "write",
            on_filters_changed
        )

        # --------------------------------------------------------------
        # UPDATE TABS
        # --------------------------------------------------------------

        def show_tab(tab):

            self._service_active_tab = tab

            if tab == "hospitals":

                hospitals_tab.configure(
                    fg_color=PRIMARY,
                    text_color="#FFFFFF"
                )

                repair_tab.configure(
                    fg_color="transparent",
                    text_color=TEXT_SECONDARY
                )

                render_results(
                    "hospitals"
                )

            else:

                repair_tab.configure(
                    fg_color=TEAL,
                    text_color="#FFFFFF"
                )

                hospitals_tab.configure(
                    fg_color="transparent",
                    text_color=TEXT_SECONDARY
                )

                render_results(
                    "repair"
                )

        # --------------------------------------------------------------
        # LOAD DATA
        # --------------------------------------------------------------

        def load_recommendations():

            show_loading()

            refresh_btn.configure(
                state="disabled",
                text="⏳"
            )

            stat_hospitals.configure(
                text="Searching..."
            )

            stat_repair.configure(
                text="Searching..."
            )

            stat_accessible.configure(
                text="Checking..."
            )

            def worker():

                hospitals = []
                shops = []

                hospital_error = None
                repair_error = None

                try:

                    # --------------------------------------------------
                    # Hospital search
                    # --------------------------------------------------

                    hospitals = find_nearby_hospitals(
                        *self.current_location,
                        radius_m=10000,
                        limit=20,
                        prioritize_accessibility=True
                    )

                except Exception as e:

                    hospital_error = str(e)

                    print(
                        f"[Dashboard] Hospital search failed: {e}"
                    )

                try:

                    # --------------------------------------------------
                    # Repair search
                    # --------------------------------------------------

                    shops = find_nearby_repair_shops(
                        *self.current_location
                    )

                except Exception as e:

                    repair_error = str(e)

                    print(
                        f"[Dashboard] Repair search failed: {e}"
                    )

                def update_ui():

                    if not page_is_alive():
                        return

                    services_data["hospitals"] = (
                        hospitals
                    )

                    services_data["repair"] = (
                        shops
                    )

                    fetch_errors["hospitals"] = (
                        hospital_error
                    )

                    fetch_errors["repair"] = (
                        repair_error
                    )

                    # --------------------------------------------------
                    # Statistics
                    # --------------------------------------------------

                    stat_hospitals.configure(
                        text=str(
                            len(hospitals)
                        )
                    )

                    stat_repair.configure(
                        text=str(
                            len(shops)
                        )
                    )

                    accessible_count = 0

                    for hospital in hospitals:

                        if str(
                            hospital.get(
                                "wheelchair",
                                "unknown"
                            )
                        ).lower() == "yes":

                            accessible_count += 1

                    stat_accessible.configure(
                        text=(
                            f"{accessible_count} confirmed"
                            if accessible_count
                            else "Unknown"
                        )
                    )

                    last_updated_label.configure(
                        text=(
                            "Last updated "
                            + datetime.now().strftime("%I:%M %p")
                        )
                    )

                    refresh_btn.configure(
                        state="normal",
                        text="↻"
                    )

                    render_results(
                        self._service_active_tab
                    )

                self.after(
                    0,
                    update_ui
                )

            threading.Thread(
                target=worker,
                daemon=True
            ).start()

        # --------------------------------------------------------------
        # REFRESH
        # --------------------------------------------------------------

        def refresh_services():

            if not page_is_alive():
                return

            try:

                clear_hospital_cache()

            except Exception:

                pass

            load_recommendations()

        refresh_btn.configure(
            command=refresh_services
        )

        # --------------------------------------------------------------
        # STAT INITIALIZATION
        # --------------------------------------------------------------

        def _initial_render():

            if not page_is_alive():
                return

            show_loading()

            load_recommendations()

        # --------------------------------------------------------------
        # INITIAL TAB
        # --------------------------------------------------------------

        show_tab(
            "hospitals"
        )

        self.after(
            150,
            _initial_render
        )

    # ============================================================
    # MEDICAL REPORT
    # ============================================================

    def show_medical_tab(self):

        self._clear_content()

        self.set_page("Medical Reports")


        self.simple_header(
            "📄 AI Medical Report Summary",
            "Convert complicated medical text into an easier summary."
        )


        card = self.create_simple_card()


        ctk.CTkLabel(
            card,
            text=(
                "⚠ For informational purposes only. "
                "Not medical advice."
            ),
            text_color="#D97706",
            font=("Segoe UI", 11, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )


        input_box = ctk.CTkTextbox(
            card,
            height=150,
            corner_radius=12
        )

        input_box.pack(
            fill="x",
            padx=20,
            pady=10
        )


        output_box = ctk.CTkTextbox(
            card,
            height=180,
            corner_radius=12
        )

        output_box.pack(
            fill="x",
            padx=20,
            pady=10
        )


        def run_summary():

            text = input_box.get(
                "1.0",
                "end"
            ).strip()


            if not text:

                output_box.delete(
                    "1.0",
                    "end"
                )

                output_box.insert(
                    "end",
                    "Please enter report text."
                )

                return


            output_box.delete(
                "1.0",
                "end"
            )


            output_box.insert(
                "end",
                "🔄 Creating summary..."
            )


            def worker():

                try:

                    summary = summarize_report(
                        text
                    )


                    user_id = self.user.get("id")

                    if user_id is not None:

                        save_medical_report(
                            user_id,
                            "pasted_text",
                            summary
                        )


                except Exception as e:

                    summary = f"⚠ Error: {e}"


                def update():

                    output_box.delete(
                        "1.0",
                        "end"
                    )

                    output_box.insert(
                        "end",
                        summary
                    )


                self.after(
                    0,
                    update
                )


            threading.Thread(
                target=worker,
                daemon=True
            ).start()


        ctk.CTkButton(
            card,
            text="✨ Summarize Report",
            height=47,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            command=run_summary
        ).pack(
            fill="x",
            padx=20,
            pady=(5, 20)
        )


    # ============================================================
    # EMERGENCY
    # ============================================================

    def show_emergency_tab(self):

        self._clear_content()

        self.set_page("Emergency")


        ctk.CTkLabel(
            self.content,
            text="🚨 Emergency Assistance",
            font=("Segoe UI", 25, "bold"),
            text_color=RED
        ).pack(
            anchor="w",
            pady=(5, 3)
        )


        ctk.CTkLabel(
            self.content,
            text="Get help quickly when you need it.",
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY
        ).pack(
            anchor="w",
            pady=(0, 18)
        )


        card = ctk.CTkFrame(
            self.content,
            fg_color=WHITE,
            corner_radius=20,
            border_width=1,
            border_color="#FECACA"
        )

        card.pack(
            fill="x"
        )


        status_label = ctk.CTkLabel(
            card,
            text="Emergency services are ready.",
            font=("Segoe UI", 13),
            text_color=TEXT_SECONDARY,
            wraplength=600
        )

        status_label.pack(
            pady=20,
            padx=20
        )


        # --------------------------------------------------------
        # SOS
        # --------------------------------------------------------

        def trigger_sos():

            user_id = self.user.get("id")

            username = (
                self.user.get("full_name")
                or self.user.get("username")
                or "User"
            )


            if user_id is None:

                messagebox.showerror(
                    "Emergency",
                    "User information is missing."
                )

                return


            status_label.configure(
                text="🚨 Sending SOS..."
            )


            def worker():

                try:

                    result = send_sos(
                        user_id,
                        *self.current_location,
                        username
                    )


                    text = str(result)


                except Exception as e:

                    text = f"⚠ Error: {e}"


                self.after(
                    0,
                    lambda: status_label.configure(
                        text=text
                    )
                )


            threading.Thread(
                target=worker,
                daemon=True
            ).start()


        # --------------------------------------------------------
        # VOICE SOS
        # --------------------------------------------------------

        def toggle_voice_sos():

            user_id = self.user.get("id")

            username = (
                self.user.get("full_name")
                or self.user.get("username")
                or "User"
            )


            if user_id is None:

                messagebox.showerror(
                    "Voice SOS",
                    "User information is missing."
                )

                return


            if self.voice_listener is None:

                self.voice_listener = VoiceSOSListener(
                    user_id=user_id,

                    get_location_fn=lambda:
                        self.current_location,

                    user_name=username,

                    on_trigger=lambda r:
                        self.after(
                            0,
                            lambda:
                            status_label.configure(
                                text=str(r)
                            )
                        )
                )


                self.voice_listener.start()


                voice_button.configure(
                    text="⏹ Stop Voice SOS"
                )


                status_label.configure(
                    text=(
                        "🎙 Listening for emergency "
                        "voice commands..."
                    )
                )


            else:

                try:

                    self.voice_listener.stop()

                except Exception:
                    pass


                self.voice_listener = None


                voice_button.configure(
                    text="🎙 Start Voice SOS"
                )


                status_label.configure(
                    text="Voice SOS stopped."
                )


        # --------------------------------------------------------
        # OFFLINE CARD
        # --------------------------------------------------------

        def show_offline_card():

            user_id = self.user.get("id")

            if user_id is None:

                status_label.configure(
                    text="⚠ User information is missing."
                )

                return


            try:

                card_data = get_offline_emergency_card(
                    user_id
                )


                if card_data["emergency_contacts"]:

                    text = (
                        "Emergency Contacts:\n\n"
                    )


                    text += "\n".join(
                        f"• {c['name']}: {c['phone']}"
                        for c in card_data[
                            "emergency_contacts"
                        ]
                    )

                else:

                    text = (
                        "No emergency contacts "
                        "saved yet."
                    )


                status_label.configure(
                    text=(
                        text
                        + "\n\n"
                        + card_data["instructions"]
                    )
                )


            except Exception as e:

                status_label.configure(
                    text=f"⚠ {e}"
                )


        # --------------------------------------------------------
        # LOCAL ALARM
        # --------------------------------------------------------

        def sound_alarm():

            threading.Thread(
                target=play_local_alarm,
                daemon=True
            ).start()


        # --------------------------------------------------------
        # ADD CONTACT
        # --------------------------------------------------------

        def add_contact():

            user_id = self.user.get("id")

            if user_id is None:

                messagebox.showerror(
                    "Emergency Contact",
                    "User information is missing."
                )

                return


            dialog = ctk.CTkInputDialog(
                text="Contact name:",
                title="Add Emergency Contact"
            )


            name = dialog.get_input()


            if not name:
                return


            dialog2 = ctk.CTkInputDialog(
                text="Contact phone:",
                title="Add Emergency Contact"
            )


            phone = dialog2.get_input()


            if not phone:
                return


            try:

                add_emergency_contact(
                    user_id,
                    name,
                    phone
                )


                messagebox.showinfo(
                    "Saved",
                    f"Added {name} as an emergency contact."
                )


            except Exception as e:

                messagebox.showerror(
                    "Error",
                    str(e)
                )


        # ========================================================
        # EMERGENCY BUTTONS
        # ========================================================

        ctk.CTkButton(
            card,
            text="🚨 SEND SOS NOW",
            height=60,
            corner_radius=15,
            fg_color=RED,
            hover_color="#DC2626",
            font=("Segoe UI", 16, "bold"),
            command=trigger_sos
        ).pack(
            fill="x",
            padx=25,
            pady=10
        )


        voice_button = ctk.CTkButton(
            card,
            text="🎙 Start Voice SOS",
            height=47,
            corner_radius=12,
            command=toggle_voice_sos
        )

        voice_button.pack(
            fill="x",
            padx=25,
            pady=5
        )


        ctk.CTkButton(
            card,
            text="📋 Show Offline Emergency Card",
            height=47,
            corner_radius=12,
            command=show_offline_card
        ).pack(
            fill="x",
            padx=25,
            pady=5
        )


        ctk.CTkButton(
            card,
            text="🔔 Sound Local Alarm",
            height=47,
            corner_radius=12,
            command=sound_alarm
        ).pack(
            fill="x",
            padx=25,
            pady=5
        )


        ctk.CTkButton(
            card,
            text="👤 Add Emergency Contact",
            height=47,
            corner_radius=12,
            command=add_contact
        ).pack(
            fill="x",
            padx=25,
            pady=5
        )


        ctk.CTkButton(
            card,
            text="🔄 Retry Queued SOS",
            height=47,
            corner_radius=12,
            command=lambda:
                status_label.configure(
                    text=str(
                        retry_queued_sos()
                    )
                )
        ).pack(
            fill="x",
            padx=25,
            pady=(5, 25)
        )


    # ============================================================
    # PROFILE
    # ============================================================

    def show_profile(self):

        self._clear_content()

        self.set_page("Profile")


        name = (
            self.user.get("full_name")
            or self.user.get("username")
            or "User"
        )


        self.simple_header(
            "👤 My Profile",
            "Manage your WheelGuide account."
        )


        card = ctk.CTkFrame(
            self.content,
            fg_color=WHITE,
            corner_radius=20,
            border_width=1,
            border_color=BORDER
        )

        card.pack(
            fill="x",
            pady=5
        )


        ctk.CTkLabel(
            card,
            text=name[:1].upper(),
            width=75,
            height=75,
            corner_radius=38,
            fg_color=PRIMARY,
            text_color="white",
            font=("Segoe UI", 28, "bold")
        ).pack(
            pady=(25, 10)
        )


        ctk.CTkLabel(
            card,
            text=name,
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT
        ).pack()


        username = self.user.get(
            "username",
            ""
        )


        ctk.CTkLabel(
            card,
            text=username,
            font=("Segoe UI", 11),
            text_color=TEXT_SECONDARY
        ).pack(
            pady=(3, 25)
        )


        emergency_card = ctk.CTkFrame(
            self.content,
            fg_color=WHITE,
            corner_radius=18,
            border_width=1,
            border_color=BORDER
        )

        emergency_card.pack(
            fill="x",
            pady=10
        )


        ctk.CTkLabel(
            emergency_card,
            text="🚨",
            font=("Segoe UI Emoji", 26)
        ).pack(
            side="left",
            padx=18,
            pady=18
        )


        profile_text = ctk.CTkFrame(
            emergency_card,
            fg_color="transparent"
        )

        profile_text.pack(
            side="left",
            fill="x",
            expand=True,
            pady=15
        )


        ctk.CTkLabel(
            profile_text,
            text="Emergency Contacts",
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w"
        )


        ctk.CTkLabel(
            profile_text,
            text="Manage emergency contacts.",
            font=("Segoe UI", 9),
            text_color=TEXT_SECONDARY
        ).pack(
            anchor="w"
        )


        ctk.CTkButton(
            emergency_card,
            text="Open →",
            width=90,
            height=36,
            corner_radius=10,
            fg_color=RED,
            hover_color="#DC2626",
            command=self.show_emergency_tab
        ).pack(
            side="right",
            padx=15
        )


    # ============================================================
    # NOTIFICATIONS
    # ============================================================

    def show_notifications(self):

        messagebox.showinfo(
            "Notifications",
            "🔔 No new notifications.\n\n"
            "WheelGuide is ready to assist you."
        )


    # ============================================================
    # QUICK ACTIONS
    # ============================================================

    def show_quick_actions(self):

        self._clear_content()

        self.set_page("Quick Actions")


        self.simple_header(
            "⚡ Quick Actions",
            "Access important WheelGuide features quickly."
        )


        self.modern_action_card(
            "🧭",
            "Accessible Route",
            "Find a route that prioritizes wheelchair accessibility.",
            PRIMARY,
            self.show_route_tab
        )


        self.modern_action_card(
            "🚧",
            "Report Construction",
            "Report construction or obstacles around you.",
            ORANGE,
            self.show_construction_tab
        )


        self.modern_action_card(
            "♿",
            "Accessibility Score",
            "Check how wheelchair-friendly a location is.",
            TEAL,
            self.show_accessibility_tab
        )


        self.modern_action_card(
            "🚨",
            "Emergency SOS",
            "Send an emergency assistance request.",
            RED,
            self.show_emergency_tab
        )


    # ============================================================
    # SERVICES
    # ============================================================

    def show_services(self):

        self._clear_content()

        self.set_page("Services")


        self.simple_header(
            "♿ WheelGuide Services",
            "Everything you need for safer and more accessible travel."
        )


        self.modern_action_card(
            "🏥",
            "Hospitals & Repair",
            "Find nearby hospitals and wheelchair repair services.",
            PRIMARY,
            self.show_recommendations_tab
        )


        self.modern_action_card(
            "📷",
            "Staircase Detection",
            "Use AI to detect stairs from an image or webcam.",
            PURPLE,
            self.show_staircase_tab
        )


        self.modern_action_card(
            "📄",
            "Medical Reports",
            "Get a simple AI-generated explanation of medical text.",
            TEAL,
            self.show_medical_tab
        )


        self.modern_action_card(
            "🗺",
            "Offline Maps",
            "Keep important map information available offline.",
            ORANGE,
            self.show_offline_maps_tab
        )


    # ============================================================
    # MODERN ACTION CARD
    # ============================================================

    def modern_action_card(
        self,
        icon,
        title,
        description,
        color,
        command
    ):

        card = ctk.CTkFrame(
            self.content,
            fg_color=WHITE,
            corner_radius=18,
            border_width=1,
            border_color=BORDER
        )

        card.pack(
            fill="x",
            pady=6
        )


        icon_box = ctk.CTkLabel(
            card,
            text=icon,
            font=("Segoe UI Emoji", 25),
            fg_color=BLUE_SOFT,
            corner_radius=14,
            width=55,
            height=55
        )

        icon_box.pack(
            side="left",
            padx=15,
            pady=15
        )


        text_frame = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )

        text_frame.pack(
            side="left",
            fill="x",
            expand=True,
            pady=12
        )


        ctk.CTkLabel(
            text_frame,
            text=title,
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w"
        )


        ctk.CTkLabel(
            text_frame,
            text=description,
            font=("Segoe UI", 10),
            text_color=TEXT_SECONDARY,
            wraplength=360,
            justify="left"
        ).pack(
            anchor="w",
            pady=(3, 0)
        )


        ctk.CTkButton(
            card,
            text="›",
            width=38,
            height=38,
            corner_radius=19,
            fg_color=color,
            hover_color=color,
            font=("Segoe UI", 20),
            command=command
        ).pack(
            side="right",
            padx=15
        )


    # ============================================================
    # COMPATIBILITY HELPERS
    # ============================================================

    def create_bottom_button(
        self,
        column,
        icon,
        text,
        command
    ):

        if self.bottom_nav is None:
            return


        button = ctk.CTkButton(
            self.bottom_nav,
            text=f"{icon}\n{text}",
            width=65,
            height=55,
            corner_radius=12,
            fg_color="transparent",
            hover_color=BLUE_SOFT,
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 10),
            command=command
        )


        button.grid(
            row=0,
            column=column,
            padx=4,
            pady=5
        )


        self.nav_buttons[text] = button


    def create_drawer(self):

        self.drawer_visible = False


    def create_drawer_button(
        self,
        icon,
        title,
        command
    ):

        self._create_sidebar_button(
            icon,
            title,
            command
        )


    def toggle_drawer(self):

        return


    # ============================================================
    # OLD DASHBOARD HELPERS
    # ============================================================

    def small_info_card(
        self,
        parent,
        column,
        icon,
        title,
        value,
        bg_color,
        command=None
    ):

        card = ctk.CTkFrame(
            parent,
            fg_color=WHITE,
            corner_radius=15,
            border_width=1,
            border_color=BORDER
        )


        card.grid(
            row=0,
            column=column,
            padx=4,
            sticky="ew"
        )


        ctk.CTkLabel(
            card,
            text=icon,
            width=42,
            height=42,
            corner_radius=11,
            fg_color=bg_color,
            font=("Segoe UI Emoji", 21)
        ).pack(
            pady=(10, 6)
        )


        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_SECONDARY
        ).pack()


        ctk.CTkLabel(
            card,
            text=value,
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            pady=(2, 10)
        )


    def quick_action(
        self,
        parent,
        column,
        icon,
        title,
        color,
        command
    ):

        frame = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )


        frame.grid(
            row=0,
            column=column,
            padx=4
        )


        ctk.CTkButton(
            frame,
            text=icon,
            width=58,
            height=58,
            corner_radius=17,
            fg_color=color,
            hover_color=color,
            font=("Segoe UI Emoji", 24),
            command=command
        ).pack()


        ctk.CTkLabel(
            frame,
            text=title,
            font=("Segoe UI", 9, "bold"),
            text_color=TEXT_SECONDARY
        ).pack(
            pady=(5, 0)
        )


    def activity_card(
        self,
        icon,
        title,
        subtitle
    ):

        card = ctk.CTkFrame(
            self.content,
            fg_color=WHITE,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )


        card.pack(
            fill="x",
            pady=3
        )


        ctk.CTkLabel(
            card,
            text=icon,
            width=40,
            height=40,
            corner_radius=11,
            fg_color=BLUE_SOFT,
            font=("Segoe UI Emoji", 19)
        ).pack(
            side="left",
            padx=10,
            pady=8
        )


        text = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )


        text.pack(
            side="left",
            fill="x",
            expand=True
        )


        ctk.CTkLabel(
            text,
            text=title,
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w"
        )


        ctk.CTkLabel(
            text,
            text=subtitle,
            font=("Segoe UI", 9),
            text_color=TEXT_SECONDARY
        ).pack(
            anchor="w"
        )

    def _service_stat_card(
        self,
        parent,
        column,
        icon,
        title,
        value,
        icon_bg,
        accent
    ):
        """
        Compact statistics card used by the Healthcare & Mobility page.
        """

        card = ctk.CTkFrame(
            parent,
            fg_color=WHITE,
            corner_radius=16,
            border_width=1,
            border_color=BORDER
        )

        card.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=5
        )

        icon_box = ctk.CTkLabel(
            card,
            text=icon,
            width=38,
            height=38,
            corner_radius=11,
            fg_color=icon_bg,
            text_color=accent,
            font=("Segoe UI Emoji", 18)
        )

        icon_box.pack(
            side="left",
            padx=(12, 8),
            pady=11
        )

        text = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )

        text.pack(
            side="left",
            fill="x",
            expand=True,
            pady=9
        )

        ctk.CTkLabel(
            text,
            text=title,
            font=("Segoe UI", 8),
            text_color=TEXT_SECONDARY
        ).pack(
            anchor="w"
        )

        value_label = ctk.CTkLabel(
            text,
            text=value,
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT
        )

        value_label.pack(
            anchor="w"
        )

        return value_label
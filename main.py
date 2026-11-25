"""
main.py
--------
WheelGuide - AI-powered wheelchair accessibility & emergency assistant app.

Entry point:
Home -> Login -> Dashboard
"""

import os
import sys
import customtkinter as ctk

# Make project root available to Python
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import APP_NAME, THEME_COLOR
from Database.database import init_db
from GUI.home import HomeFrame
from GUI.login import LoginFrame
from GUI.dashboard import DashboardFrame


class WheelGuideApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)

        # Start with a proper desktop-sized window
        self.geometry("1180x760")
        self.minsize(980, 650)

        # Appearance
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme(THEME_COLOR)

        self.current_frame = None

        self.show_home()

    def _switch_frame(self, frame_class, **kwargs):
        """Safely switch between application screens."""

        if self.current_frame is not None:
            try:
                self.current_frame.destroy()
            except Exception:
                pass

            self.current_frame = None

        try:
            self.current_frame = frame_class(self, **kwargs)
            self.current_frame.pack(
                fill="both",
                expand=True
            )

            self.current_frame.tkraise()

        except Exception as error:
            # Prevent a completely blank screen if a frame crashes.
            error_frame = ctk.CTkFrame(
                self,
                fg_color="#F5F8FC"
            )
            error_frame.pack(
                fill="both",
                expand=True
            )

            ctk.CTkLabel(
                error_frame,
                text="WheelGuide",
                font=("Segoe UI", 28, "bold"),
                text_color="#172033"
            ).pack(pady=(100, 10))

            ctk.CTkLabel(
                error_frame,
                text="Something went wrong while opening this page.",
                font=("Segoe UI", 14),
                text_color="#64748B"
            ).pack(pady=5)

            ctk.CTkLabel(
                error_frame,
                text=str(error),
                font=("Consolas", 10),
                text_color="#EF4444",
                wraplength=800,
                justify="left"
            ).pack(
                padx=40,
                pady=20
            )

            ctk.CTkButton(
                error_frame,
                text="Return to Login",
                width=180,
                height=42,
                corner_radius=10,
                command=self.show_login
            ).pack(pady=10)

            self.current_frame = error_frame

    def show_home(self):
        self._switch_frame(
            HomeFrame,
            on_continue=self.show_login
        )

    def show_login(self):
        self._switch_frame(
            LoginFrame,
            on_login_success=self.show_dashboard
        )

    def show_dashboard(self, user):
        self._switch_frame(
            DashboardFrame,
            user=user
        )


if __name__ == "__main__":

    try:
        init_db()
    except Exception as error:
        print("Database initialization error:", error)

    app = WheelGuideApp()
    app.mainloop()
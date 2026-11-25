"""
GUI/login.py
-------------
Login and sign-up screen. On success, calls on_login_success(user_dict)
which main.py wires up to open the dashboard.
"""
import customtkinter as ctk
import sys
import os

# =====================================================
# DATABASE IMPORT
# =====================================================

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from Database.database import verify_user, create_user


class LoginFrame(ctk.CTkFrame):

    def __init__(self, master, on_login_success, **kwargs):

        super().__init__(
            master,
            fg_color="#F5F8FF",
            corner_radius=0,
            **kwargs
        )

        self.on_login_success = on_login_success

        # login / signup
        self.mode = "login"

        self._build_ui()

    # =====================================================
    # BUILD UI
    # =====================================================

    def _build_ui(self):

        # Remove old widgets
        for widget in self.winfo_children():
            widget.destroy()

        # =================================================
        # MAIN BACKGROUND
        # =================================================

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
        # TOP LOGO
        # =================================================

        self.logo = ctk.CTkLabel(
            self.main,
            text="♿",
            width=65,
            height=65,
            corner_radius=22,
            fg_color="#1746C7",
            text_color="white",
            font=("Segoe UI Emoji", 30)
        )

        self.logo.pack(
            pady=(20, 7)
        )

        # =================================================
        # APP NAME
        # =================================================

        self.title = ctk.CTkLabel(
            self.main,
            text="WheelGuide",
            font=("Segoe UI", 30, "bold"),
            text_color="#1746C7"
        )

        self.title.pack(
            pady=(0, 2)
        )

        # =================================================
        # SCREEN TITLE
        # =================================================

        if self.mode == "login":

            screen_title = "Welcome Back! 👋"
            description = "Sign in to continue your accessible journey"

        else:

            screen_title = "Join WheelGuide ♿"
            description = "Create your account for smarter journeys"

        self.screen_title = ctk.CTkLabel(
            self.main,
            text=screen_title,
            font=("Segoe UI", 18, "bold"),
            text_color="#253858"
        )

        self.screen_title.pack(
            pady=(3, 2)
        )

        # =================================================
        # DESCRIPTION
        # =================================================

        self.description = ctk.CTkLabel(
            self.main,
            text=description,
            font=("Segoe UI", 10),
            text_color="#718096"
        )

        self.description.pack(
            pady=(0, 12)
        )

        # =================================================
        # WHITE FORM CARD
        # =================================================

        self.card = ctk.CTkFrame(
            self.main,
            fg_color="white",
            corner_radius=25
        )

        self.card.pack(
            padx=20,
            pady=(3, 8),
            fill="x"
        )

        # =================================================
        # FORM TITLE
        # =================================================

        form_title = (
            "Sign in to your account"
            if self.mode == "login"
            else "Create your account"
        )

        self.form_title = ctk.CTkLabel(
            self.card,
            text=form_title,
            font=("Segoe UI", 16, "bold"),
            text_color="#253858"
        )

        self.form_title.pack(
            pady=(18, 10)
        )

        # =================================================
        # USERNAME
        # =================================================

        self.username_entry = ctk.CTkEntry(
            self.card,
            placeholder_text="👤  Username",
            width=290,
            height=44,
            corner_radius=13,
            border_width=1,
            border_color="#D8E2F0",
            fg_color="#F8FAFD",
            text_color="#253858",
            placeholder_text_color="#8A98AA"
        )

        self.username_entry.pack(
            pady=5
        )

        # =================================================
        # PASSWORD
        # =================================================

        self.password_entry = ctk.CTkEntry(
            self.card,
            placeholder_text="🔒  Password",
            width=290,
            height=44,
            corner_radius=13,
            border_width=1,
            border_color="#D8E2F0",
            fg_color="#F8FAFD",
            text_color="#253858",
            placeholder_text_color="#8A98AA",
            show="*"
        )

        self.password_entry.pack(
            pady=5
        )

        # =================================================
        # SIGNUP EXTRA FIELDS
        # =================================================

        if self.mode == "signup":

            self.fullname_entry = self._create_entry(
                "👤  Full name"
            )

            self.phone_entry = self._create_entry(
                "📱  Phone number"
            )

            self.contact_name_entry = self._create_entry(
                "🆘  Emergency contact name"
            )

            self.contact_phone_entry = self._create_entry(
                "📞  Emergency contact phone"
            )

        # =================================================
        # ERROR MESSAGE
        # =================================================

        self.error_label = ctk.CTkLabel(
            self.card,
            text="",
            text_color="#E5484D",
            font=("Segoe UI", 10),
            wraplength=280
        )

        self.error_label.pack(
            pady=(4, 0)
        )

        # =================================================
        # MAIN LOGIN / SIGNUP BUTTON
        # =================================================

        if self.mode == "login":

            button_text = "LOGIN"

        else:

            button_text = "CREATE ACCOUNT"

        self.action_button = ctk.CTkButton(
            self.card,
            text=button_text,
            width=290,
            height=46,
            corner_radius=14,
            fg_color="#1746C7",
            hover_color="#1239A5",
            text_color="white",
            font=("Segoe UI", 13, "bold"),
            command=self._handle_submit
        )

        self.action_button.pack(
            pady=(10, 7)
        )

        # =================================================
        # LOGIN / SIGNUP SWITCH
        # =================================================

        self.switch_frame = ctk.CTkFrame(
            self.card,
            fg_color="transparent"
        )

        self.switch_frame.pack(
            pady=(2, 17)
        )

        # -------------------------------------------------
        # LOGIN SCREEN
        # -------------------------------------------------

        if self.mode == "login":

            self.question_label = ctk.CTkLabel(
                self.switch_frame,
                text="Don't have an account?",
                font=("Segoe UI", 10),
                text_color="#718096"
            )

            self.question_label.pack(
                side="left"
            )

            self.signup_button = ctk.CTkButton(
                self.switch_frame,
                text="Sign Up",
                width=65,
                height=27,
                fg_color="transparent",
                hover_color="#EAF2FF",
                text_color="#1746C7",
                font=("Segoe UI", 10, "bold"),
                command=self._switch_mode
            )

            self.signup_button.pack(
                side="left",
                padx=(3, 0)
            )

        # -------------------------------------------------
        # SIGNUP SCREEN
        # -------------------------------------------------

        else:

            self.question_label = ctk.CTkLabel(
                self.switch_frame,
                text="Already have an account?",
                font=("Segoe UI", 10),
                text_color="#718096"
            )

            self.question_label.pack(
                side="left"
            )

            self.login_button = ctk.CTkButton(
                self.switch_frame,
                text="Login",
                width=50,
                height=27,
                fg_color="transparent",
                hover_color="#EAF2FF",
                text_color="#1746C7",
                font=("Segoe UI", 10, "bold"),
                command=self._switch_mode
            )

            self.login_button.pack(
                side="left",
                padx=(3, 0)
            )

        # =================================================
        # SECURITY MESSAGE
        # =================================================

        security = ctk.CTkLabel(
            self.main,
            text="🔐  Your information is kept secure",
            font=("Segoe UI", 9),
            text_color="#94A3B8"
        )

        security.pack(
            pady=(2, 2)
        )

        # =================================================
        # FOOTER
        # =================================================

        footer = ctk.CTkLabel(
            self.main,
            text="Safe  •  Smart  •  Accessible",
            font=("Segoe UI", 9, "bold"),
            text_color="#45B99A"
        )

        footer.pack(
            pady=(0, 8)
        )

        # =================================================
        # AUTO FOCUS
        # =================================================

        self.after(
            150,
            self.username_entry.focus
        )

        # Press Enter to submit

        self.username_entry.bind(
            "<Return>",
            lambda event: self._handle_submit()
        )

        self.password_entry.bind(
            "<Return>",
            lambda event: self._handle_submit()
        )

    # =====================================================
    # CREATE ENTRY
    # =====================================================

    def _create_entry(self, placeholder):

        entry = ctk.CTkEntry(
            self.card,
            placeholder_text=placeholder,
            width=290,
            height=40,
            corner_radius=13,
            border_width=1,
            border_color="#D8E2F0",
            fg_color="#F8FAFD",
            text_color="#253858",
            placeholder_text_color="#8A98AA"
        )

        entry.pack(
            pady=4
        )

        return entry

    # =====================================================
    # SWITCH LOGIN / SIGNUP
    # =====================================================

    def _switch_mode(self):

        if self.mode == "login":

            self.mode = "signup"

        else:

            self.mode = "login"

        self._build_ui()

    # =====================================================
    # HANDLE SUBMIT
    # =====================================================

    def _handle_submit(self):

        # =================================================
        # GET USERNAME AND PASSWORD
        # =================================================

        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        # =================================================
        # BASIC VALIDATION
        # =================================================

        if not username:

            self.error_label.configure(
                text="Please enter your username."
            )

            self.username_entry.focus()

            return

        if not password:

            self.error_label.configure(
                text="Please enter your password."
            )

            self.password_entry.focus()

            return

        # =================================================
        # LOGIN
        # =================================================

        if self.mode == "login":

            user = verify_user(
                username,
                password
            )

            if user:

                self.error_label.configure(
                    text=""
                )

                self.action_button.configure(
                    text="WELCOME ✓",
                    fg_color="#45B99A"
                )

                self.after(
                    400,
                    lambda: self.on_login_success(user)
                )

            else:

                self.error_label.configure(
                    text="Invalid username or password."
                )

        # =================================================
        # SIGN UP
        # =================================================

        else:

            full_name = self.fullname_entry.get().strip()
            phone = self.phone_entry.get().strip()
            contact_name = self.contact_name_entry.get().strip()
            contact_phone = self.contact_phone_entry.get().strip()

            # -------------------------------------------------
            # VALIDATE FULL NAME
            # -------------------------------------------------

            if not full_name:

                self.error_label.configure(
                    text="Please enter your full name."
                )

                self.fullname_entry.focus()

                return

            # -------------------------------------------------
            # VALIDATE PHONE
            # -------------------------------------------------

            if not phone:

                self.error_label.configure(
                    text="Please enter your phone number."
                )

                self.phone_entry.focus()

                return

            # -------------------------------------------------
            # VALIDATE EMERGENCY CONTACT
            # -------------------------------------------------

            if not contact_name:

                self.error_label.configure(
                    text="Please enter an emergency contact name."
                )

                self.contact_name_entry.focus()

                return

            if not contact_phone:

                self.error_label.configure(
                    text="Please enter an emergency contact phone."
                )

                self.contact_phone_entry.focus()

                return

            # =================================================
            # CREATE USER
            # =================================================

            success, message = create_user(
                username,
                password,
                full_name,
                phone,
                contact_name,
                contact_phone
            )

            if success:

                # Get newly created user

                user = verify_user(
                    username,
                    password
                )

                self.error_label.configure(
                    text=""
                )

                self.action_button.configure(
                    text="ACCOUNT CREATED ✓",
                    fg_color="#45B99A"
                )

                self.after(
                    500,
                    lambda: self.on_login_success(user)
                )

            else:

                self.error_label.configure(
                    text=message
                )
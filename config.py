"""
config.py
---------
Central place for API keys and app-wide constants.
NEVER commit real API keys to GitHub — use environment variables in a real
deployment. For a diploma project/demo, you can paste keys directly below.
"""

import os

# ---------------- Google Gemini (used for accessibility scoring & medical
# report summarization) ----------------
# Get a free key from https://aistudio.google.com/app/apikey
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_GEMINI_API_KEY_HERE")

# ---------------- Twilio (used for SOS SMS / calls) ----------------
# Get these from https://www.twilio.com/console
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "PASTE_TWILIO_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "PASTE_TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "+1XXXXXXXXXX")

# ---------------- Database ----------------
DB_PATH = os.path.join(os.path.dirname(__file__), "Database", "wheelguide.db")

# ---------------- Offline map tile cache ----------------
TILE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "Maps", "tile_cache")

# ---------------- YOLO model paths ----------------
# yolov8n.pt (general object detector, auto-downloaded by ultralytics on first
# run) is used as a stand-in for staircase/construction detection since a
# custom-trained model needs your own labeled dataset. See AI/staircase.py
# and AI/construction.py for notes on training a custom model later.
YOLO_GENERAL_MODEL = "yolov8n.pt"

# App-wide theme
APP_NAME = "WheelGuide"
THEME_COLOR = "dark-blue"

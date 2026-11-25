"""
Emergency/sos.py
----------------
WheelGuide Emergency SOS System

Features
--------
1. Manual SOS support
2. Voice SOS support
3. Emergency contact retrieval
4. Twilio SMS notification
5. Google Maps location link
6. Reverse-geocoded address
7. SOS database logging
8. Offline SOS queue support
9. Safe Twilio/API failure handling
10. Multiple emergency contacts
11. Duplicate-send protection
12. Human-readable SOS result
13. Works even when Twilio is unavailable

Public API
----------
send_sos(...)
build_sos_message(...)
is_sos_configured()
"""

import os
import sys
import time
from datetime import datetime

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


# ============================================================
# CONFIGURATION
# ============================================================

try:
    from config import (
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN,
        TWILIO_FROM_NUMBER,
    )

except ImportError:

    TWILIO_ACCOUNT_SID = os.getenv(
        "TWILIO_ACCOUNT_SID",
        ""
    )

    TWILIO_AUTH_TOKEN = os.getenv(
        "TWILIO_AUTH_TOKEN",
        ""
    )

    TWILIO_FROM_NUMBER = os.getenv(
        "TWILIO_FROM_NUMBER",
        ""
    )


# ============================================================
# DATABASE
# ============================================================

try:

    from Database.database import (
        get_emergency_contacts,
        log_sos,
    )

    DATABASE_AVAILABLE = True

except ImportError as exc:

    print(
        f"[WheelGuide SOS] Database import failed: {exc}"
    )

    DATABASE_AVAILABLE = False


# ============================================================
# MAPS
# ============================================================

try:

    from Maps.maps import reverse_geocode

    MAPS_AVAILABLE = True

except ImportError as exc:

    print(
        f"[WheelGuide SOS] Maps module unavailable: {exc}"
    )

    MAPS_AVAILABLE = False

    def reverse_geocode(lat, lon):
        return f"{lat}, {lon}"


# ============================================================
# TWILIO
# ============================================================

try:

    from twilio.rest import Client

    TWILIO_AVAILABLE = True

except ImportError:

    Client = None
    TWILIO_AVAILABLE = False


# ============================================================
# CONSTANTS
# ============================================================

GOOGLE_MAPS_URL = (
    "https://www.google.com/maps?q={lat},{lon}"
)

MAX_CONTACTS = 10

SMS_TIMEOUT_SECONDS = 15

# Prevent accidental repeated SOS messages
DUPLICATE_SOS_WINDOW = 30

_last_sos_time = {}


# ============================================================
# TWILIO CONFIGURATION
# ============================================================

def is_sos_configured():
    """
    Check whether Twilio is properly configured.

    Returns
    -------
    bool
        True when Twilio can potentially send SMS.
    """

    if not TWILIO_AVAILABLE:
        return False

    if not TWILIO_ACCOUNT_SID:
        return False

    if not TWILIO_AUTH_TOKEN:
        return False

    if not TWILIO_FROM_NUMBER:
        return False

    invalid_values = [
        "PASTE",
        "YOUR_",
        "YOUR-TWILIO",
        "ACCOUNT_SID",
        "AUTH_TOKEN",
    ]

    values = [
        str(TWILIO_ACCOUNT_SID),
        str(TWILIO_AUTH_TOKEN),
        str(TWILIO_FROM_NUMBER),
    ]

    for value in values:

        upper_value = value.upper()

        for invalid in invalid_values:

            if invalid.upper() in upper_value:
                return False

    return True


# ============================================================
# SAFE TEXT
# ============================================================

def _clean_text(value):
    """
    Convert any value to clean text.
    """

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# LOCATION VALIDATION
# ============================================================

def _valid_coordinates(lat, lon):
    """
    Validate latitude and longitude.
    """

    try:

        lat = float(lat)
        lon = float(lon)

    except (TypeError, ValueError):

        return False

    if not -90 <= lat <= 90:
        return False

    if not -180 <= lon <= 180:
        return False

    return True


# ============================================================
# ADDRESS
# ============================================================

def get_location_address(lat, lon):
    """
    Convert coordinates into a readable address.

    Falls back to coordinates when reverse geocoding fails.
    """

    if not _valid_coordinates(lat, lon):

        return "Location unavailable"

    try:

        if MAPS_AVAILABLE:

            address = reverse_geocode(
                lat,
                lon
            )

            if address:
                return str(address)

    except Exception as exc:

        print(
            f"[WheelGuide SOS] "
            f"Reverse geocoding failed: {exc}"
        )

    return f"{lat}, {lon}"


# ============================================================
# GOOGLE MAPS LINK
# ============================================================

def get_maps_link(lat, lon):
    """
    Generate a Google Maps location URL.
    """

    if not _valid_coordinates(lat, lon):

        return ""

    return GOOGLE_MAPS_URL.format(
        lat=lat,
        lon=lon
    )


# ============================================================
# SOS MESSAGE
# ============================================================

def build_sos_message(
    lat,
    lon,
    user_name="A WheelGuide user"
):
    """
    Create the emergency SMS message.
    """

    user_name = (
        _clean_text(user_name)
        or "A WheelGuide user"
    )

    address = get_location_address(
        lat,
        lon
    )

    maps_link = get_maps_link(
        lat,
        lon
    )

    message = (
        "🚨 WHEELGUIDE EMERGENCY SOS\n\n"
        f"{user_name} may need urgent assistance.\n\n"
        f"📍 Location:\n{address}\n\n"
        f"🗺️ Open location:\n{maps_link}\n\n"
        "This emergency alert was sent through "
        "WheelGuide."
    )

    return message


# ============================================================
# DUPLICATE PROTECTION
# ============================================================

def _is_duplicate_sos(user_id):
    """
    Prevent accidental repeated SOS messages within a short period.
    """

    now = time.time()

    previous = _last_sos_time.get(
        user_id
    )

    if previous is not None:

        if now - previous < DUPLICATE_SOS_WINDOW:

            return True

    _last_sos_time[user_id] = now

    return False


# ============================================================
# DATABASE LOGGING
# ============================================================

def _safe_log_sos(
    user_id,
    lat,
    lon,
    message,
    triggered_by,
    sent_online
):
    """
    Safely log SOS without allowing a database failure
    to crash the emergency process.
    """

    if not DATABASE_AVAILABLE:
        return False

    try:

        return log_sos(
            user_id,
            lat,
            lon,
            message,
            triggered_by,
            sent_online=sent_online
        )

    except Exception as exc:

        print(
            f"[WheelGuide SOS] "
            f"SOS logging failed: {exc}"
        )

        return False


# ============================================================
# OFFLINE QUEUE
# ============================================================

def _queue_offline_sos(
    user_id,
    lat,
    lon,
    message,
    triggered_by
):
    """
    Save SOS locally using the existing offline module.
    """

    try:

        from Emergency.offline_mode import (
            queue_offline_sos
        )

        queue_offline_sos(
            user_id,
            lat,
            lon,
            message,
            triggered_by
        )

        return True

    except Exception as exc:

        print(
            f"[WheelGuide SOS] "
            f"Offline queue failed: {exc}"
        )

        return False


# ============================================================
# SEND SMS
# ============================================================

def _send_sms(
    phone,
    message
):
    """
    Send one SMS through Twilio.

    Returns
    -------
    tuple
        (success, error_message)
    """

    if not is_sos_configured():

        return (
            False,
            "Twilio is not configured."
        )

    phone = _clean_text(phone)

    if not phone:

        return (
            False,
            "Phone number is empty."
        )

    try:

        client = Client(
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN
        )

        client.messages.create(
            body=message,
            from_=TWILIO_FROM_NUMBER,
            to=phone
        )

        return (
            True,
            ""
        )

    except Exception as exc:

        return (
            False,
            str(exc)
        )


# ============================================================
# SEND SOS
# ============================================================

def send_sos(
    user_id,
    lat,
    lon,
    user_name="A WheelGuide user",
    triggered_by="manual_button"
):
    """
    Main WheelGuide SOS function.

    Parameters
    ----------
    user_id:
        Logged-in user's database ID.

    lat:
        Current latitude.

    lon:
        Current longitude.

    user_name:
        User's display name.

    triggered_by:
        manual_button / voice_command / other.

    Returns
    -------
    dict
        Detailed SOS result.
    """

    # --------------------------------------------------------
    # BASIC RESULT
    # --------------------------------------------------------

    result = {
        "success": False,
        "sent_online": False,
        "offline_queued": False,
        "contacts_notified": [],
        "contacts_failed": [],
        "message": "",
        "address": "",
        "maps_link": "",
        "triggered_by": triggered_by,
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "error": None,
    }

    # --------------------------------------------------------
    # VALIDATE USER
    # --------------------------------------------------------

    if user_id is None:

        result["error"] = (
            "User ID is required."
        )

        return result

    # --------------------------------------------------------
    # VALIDATE LOCATION
    # --------------------------------------------------------

    if not _valid_coordinates(
        lat,
        lon
    ):

        result["error"] = (
            "Current location is unavailable."
        )

        message = (
            "WheelGuide SOS was triggered, "
            "but the current location could "
            "not be determined."
        )

        result["message"] = message

        _safe_log_sos(
            user_id,
            None,
            None,
            message,
            triggered_by,
            False
        )

        return result

    # --------------------------------------------------------
    # DUPLICATE PROTECTION
    # --------------------------------------------------------

    if _is_duplicate_sos(user_id):

        result["error"] = (
            "SOS was already triggered recently."
        )

        result["message"] = (
            "An SOS was already triggered recently. "
            "Please wait before triggering another."
        )

        return result

    # --------------------------------------------------------
    # BUILD MESSAGE
    # --------------------------------------------------------

    message = build_sos_message(
        lat,
        lon,
        user_name
    )

    result["message"] = message

    result["address"] = (
        get_location_address(
            lat,
            lon
        )
    )

    result["maps_link"] = (
        get_maps_link(
            lat,
            lon
        )
    )

    # --------------------------------------------------------
    # GET CONTACTS
    # --------------------------------------------------------

    if not DATABASE_AVAILABLE:

        result["error"] = (
            "Database is unavailable."
        )

        result["offline_queued"] = (
            _queue_offline_sos(
                user_id,
                lat,
                lon,
                message,
                triggered_by
            )
        )

        _safe_log_sos(
            user_id,
            lat,
            lon,
            message,
            triggered_by,
            False
        )

        return result

    try:

        contacts = get_emergency_contacts(
            user_id
        )

    except Exception as exc:

        print(
            f"[WheelGuide SOS] "
            f"Could not retrieve contacts: {exc}"
        )

        contacts = []

    # --------------------------------------------------------
    # NO CONTACTS
    # --------------------------------------------------------

    if not contacts:

        result["error"] = (
            "No emergency contacts saved. "
            "Add an emergency contact from the dashboard."
        )

        result["offline_queued"] = (
            _queue_offline_sos(
                user_id,
                lat,
                lon,
                message,
                triggered_by
            )
        )

        _safe_log_sos(
            user_id,
            lat,
            lon,
            message,
            triggered_by,
            False
        )

        return result

    # --------------------------------------------------------
    # LIMIT CONTACTS
    # --------------------------------------------------------

    contacts = contacts[:MAX_CONTACTS]

    # --------------------------------------------------------
    # TWILIO ONLINE MODE
    # --------------------------------------------------------

    if is_sos_configured():

        for contact in contacts:

            phone = _clean_text(
                contact.get("phone")
            )

            name = _clean_text(
                contact.get(
                    "name",
                    "Emergency contact"
                )
            )

            if not phone:

                result["contacts_failed"].append({
                    "name": name,
                    "phone": "",
                    "error": "Phone number missing"
                })

                continue

            success, error = _send_sms(
                phone,
                message
            )

            if success:

                result[
                    "contacts_notified"
                ].append(phone)

            else:

                result[
                    "contacts_failed"
                ].append({
                    "name": name,
                    "phone": phone,
                    "error": error
                })

        # ----------------------------------------------------
        # AT LEAST ONE SENT
        # ----------------------------------------------------

        if result["contacts_notified"]:

            result["success"] = True
            result["sent_online"] = True

            _safe_log_sos(
                user_id,
                lat,
                lon,
                message,
                triggered_by,
                True
            )

            # If some contacts failed, still preserve their
            # information in the result.

            if result["contacts_failed"]:

                result["error"] = (
                    "SOS sent successfully to some "
                    "contacts, but some notifications failed."
                )

            return result

        # ----------------------------------------------------
        # ALL SMS FAILED
        # ----------------------------------------------------

        result["error"] = (
            "SOS could not be delivered through Twilio."
        )

    # --------------------------------------------------------
    # OFFLINE / TWILIO FAILURE FALLBACK
    # --------------------------------------------------------

    queued = _queue_offline_sos(
        user_id,
        lat,
        lon,
        message,
        triggered_by
    )

    result["offline_queued"] = queued

    _safe_log_sos(
        user_id,
        lat,
        lon,
        message,
        triggered_by,
        False
    )

    if queued:

        result["success"] = True

        result["error"] = (
            "Internet/Twilio unavailable. "
            "SOS has been saved locally."
        )

    else:

        result["success"] = False

        if not result["error"]:

            result["error"] = (
                "SOS could not be sent or saved."
            )

    return result


# ============================================================
# SIMPLE STATUS
# ============================================================

def get_sos_status(result):
    """
    Convert an SOS result into a GUI-friendly status.
    """

    if not result:

        return "SOS status unavailable."

    if result.get("sent_online"):

        count = len(
            result.get(
                "contacts_notified",
                []
            )
        )

        return (
            f"🚨 SOS SENT — "
            f"{count} emergency contact(s) notified."
        )

    if result.get("offline_queued"):

        return (
            "⚠️ SOS SAVED OFFLINE — "
            "It will be processed when connectivity "
            "is available."
        )

    if result.get("error"):

        return (
            f"❌ SOS FAILED — "
            f"{result['error']}"
        )

    return "SOS was triggered."


# ============================================================
# DEMO / TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("WHEELGUIDE SOS TEST")
    print("=" * 60)

    print(
        "Twilio configured:",
        is_sos_configured()
    )

    test_result = send_sos(
        user_id=1,
        lat=19.0760,
        lon=72.8777,
        user_name="Test User",
        triggered_by="test"
    )

    print()
    print("Status:")
    print(
        get_sos_status(
            test_result
        )
    )

    print()
    print("Result:")
    print(test_result)

    print("=" * 60)
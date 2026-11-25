"""
Emergency/offline_mode.py
-------------------------
Feature 3: Offline emergency mode.

When there is no internet connection, WheelGuide:

    1. Queues the SOS message locally.
    2. Stores the SOS in a JSON file.
    3. Shows emergency contacts offline.
    4. Allows the emergency system to retry queued SOS messages.
    5. Plays a local alarm.
    6. Works with the local SQLite database.
"""

import os
import sys
import json
import time
import platform


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(
        0,
        PROJECT_ROOT
    )


# ============================================================
# DATABASE
# ============================================================

from Database.database import (
    get_emergency_contacts
)


# ============================================================
# OFFLINE SOS QUEUE
# ============================================================

QUEUE_PATH = os.path.join(
    PROJECT_ROOT,
    "Database",
    "offline_sos_queue.json"
)


# ============================================================
# ENSURE QUEUE FILE EXISTS
# ============================================================

def _ensure_queue_file():
    """
    Make sure the offline SOS queue file exists.
    """

    database_folder = os.path.dirname(
        QUEUE_PATH
    )

    os.makedirs(
        database_folder,
        exist_ok=True
    )

    if not os.path.exists(QUEUE_PATH):

        try:

            with open(
                QUEUE_PATH,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    [],
                    file,
                    indent=2
                )

        except Exception as exc:

            print(
                "[offline_mode.py] "
                f"Could not create queue file: {exc}"
            )


# ============================================================
# LOAD QUEUE
# ============================================================

def _load_queue():
    """
    Safely load queued SOS messages.
    """

    _ensure_queue_file()

    try:

        with open(
            QUEUE_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):

            return data

        return []

    except (
        json.JSONDecodeError,
        FileNotFoundError
    ):

        return []

    except Exception as exc:

        print(
            "[offline_mode.py] "
            f"Could not load queue: {exc}"
        )

        return []


# ============================================================
# SAVE QUEUE
# ============================================================

def _save_queue(queue):
    """
    Safely save SOS queue.
    """

    _ensure_queue_file()

    try:

        temporary_path = QUEUE_PATH + ".tmp"

        with open(
            temporary_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                queue,
                file,
                indent=2
            )

        os.replace(
            temporary_path,
            QUEUE_PATH
        )

        return True

    except Exception as exc:

        print(
            "[offline_mode.py] "
            f"Could not save queue: {exc}"
        )

        return False


# ============================================================
# QUEUE OFFLINE SOS
# ============================================================

def queue_offline_sos(
    user_id,
    lat,
    lon,
    message,
    triggered_by
):
    """
    Save an SOS to a local queue file.

    The message can later be sent when internet/Twilio
    connectivity returns.
    """

    queue = _load_queue()

    queue.append(
        {
            "user_id": user_id,

            "lat": lat,

            "lon": lon,

            "message": str(message),

            "triggered_by": str(triggered_by),

            "queued_at": time.time(),

            "sent": False
        }
    )

    success = _save_queue(
        queue
    )

    return success


# ============================================================
# RETRY QUEUED SOS
# ============================================================

def retry_queued_sos():
    """
    Retry all unsent offline SOS messages.

    This function requires Twilio to be configured.
    """

    if not os.path.exists(
        QUEUE_PATH
    ):

        return {
            "flushed": 0
        }

    queue = _load_queue()

    if not queue:

        return {
            "flushed": 0
        }

    # --------------------------------------------------------
    # Import Twilio configuration safely
    # --------------------------------------------------------

    try:

        from Emergency.sos import (
            _twilio_configured
        )

    except Exception as exc:

        return {
            "flushed": 0,
            "reason":
                f"Could not load SOS module: {exc}"
        }

    try:

        from config import (
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN,
            TWILIO_FROM_NUMBER
        )

    except Exception as exc:

        return {
            "flushed": 0,
            "reason":
                f"Twilio configuration unavailable: {exc}"
        }

    # --------------------------------------------------------
    # Check Twilio
    # --------------------------------------------------------

    try:

        if not _twilio_configured():

            return {
                "flushed": 0,
                "reason":
                    "Still offline / Twilio not configured."
            }

    except Exception as exc:

        return {
            "flushed": 0,
            "reason":
                f"Twilio configuration error: {exc}"
        }

    # --------------------------------------------------------
    # Import Twilio client
    # --------------------------------------------------------

    try:

        from twilio.rest import Client

    except ImportError:

        return {
            "flushed": 0,
            "reason":
                "Twilio package is not available."
        }

    try:

        client = Client(
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN
        )

    except Exception as exc:

        return {
            "flushed": 0,
            "reason":
                f"Could not initialize Twilio: {exc}"
        }

    # --------------------------------------------------------
    # Send queued SOS
    # --------------------------------------------------------

    flushed = 0

    for item in queue:

        if item.get(
            "sent",
            False
        ):

            continue

        user_id = item.get(
            "user_id"
        )

        message = item.get(
            "message",
            "WheelGuide Emergency SOS"
        )

        contacts = get_emergency_contacts(
            user_id
        )

        if not contacts:

            print(
                "[offline_mode.py] "
                f"No emergency contacts found for user {user_id}."
            )

            continue

        successful_sends = 0

        for contact in contacts:

            phone = contact.get(
                "phone"
            )

            if not phone:

                continue

            try:

                client.messages.create(
                    body=message,
                    from_=TWILIO_FROM_NUMBER,
                    to=phone
                )

                successful_sends += 1

                print(
                    "[offline_mode.py] "
                    f"Queued SOS sent to {phone}"
                )

            except Exception as exc:

                print(
                    "[offline_mode.py] "
                    f"Retry send failed for {phone}: {exc}"
                )

        # Only mark as sent if at least one contact
        # successfully received the message.

        if successful_sends > 0:

            item["sent"] = True

            item["sent_at"] = time.time()

            flushed += 1

    _save_queue(
        queue
    )

    return {
        "flushed": flushed
    }


# ============================================================
# GET OFFLINE EMERGENCY CARD
# ============================================================

def get_offline_emergency_card(
    user_id
):
    """
    Return emergency information completely offline.

    Returns:

        {
            "emergency_contacts": [...],
            "instructions": "..."
        }
    """

    contacts = get_emergency_contacts(
        user_id
    )

    return {
        "emergency_contacts": [
            {
                "name": contact.get(
                    "name",
                    "Emergency Contact"
                ),

                "phone": contact.get(
                    "phone",
                    ""
                ),

                "relationship": contact.get(
                    "relationship",
                    "Emergency Contact"
                )
            }

            for contact in contacts
        ],

        "instructions": (
            "If you are a bystander, please call one "
            "of the emergency contact numbers immediately "
            "or contact your local emergency service."
        )
    }


# ============================================================
# GET QUEUED SOS COUNT
# ============================================================

def get_queued_sos_count():
    """
    Return the number of SOS messages waiting to be sent.
    """

    queue = _load_queue()

    return sum(
        1
        for item in queue
        if not item.get(
            "sent",
            False
        )
    )


# ============================================================
# CLEAR SENT SOS
# ============================================================

def clear_sent_sos():
    """
    Remove SOS messages that have already been sent.
    """

    queue = _load_queue()

    pending = [
        item
        for item in queue
        if not item.get(
            "sent",
            False
        )
    ]

    success = _save_queue(
        pending
    )

    return success


# ============================================================
# PLAY LOCAL ALARM
# ============================================================

def play_local_alarm():
    """
    Play a loud local alarm.

    Windows:
        Uses winsound.Beep.

    Other systems:
        Uses terminal bell as fallback.
    """

    system = platform.system()

    try:

        if system == "Windows":

            import winsound

            for _ in range(5):

                winsound.Beep(
                    1000,
                    400
                )

                time.sleep(
                    0.1
                )

        else:

            for _ in range(5):

                print(
                    "\a",
                    end="",
                    flush=True
                )

                time.sleep(
                    0.4
                )

    except Exception as exc:

        print(
            "[offline_mode.py] "
            f"Could not play alarm: {exc}"
        )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("WHEELGUIDE OFFLINE EMERGENCY MODE TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # Initialize database
    # --------------------------------------------------------

    try:

        from Database.database import init_db

        init_db()

    except Exception as exc:

        print(
            f"Database initialization failed: {exc}"
        )

    # --------------------------------------------------------
    # Test queue
    # --------------------------------------------------------

    test_result = queue_offline_sos(
        user_id=1,
        lat=19.0760,
        lon=72.8777,
        message="Test offline SOS message",
        triggered_by="manual_test"
    )

    print()
    print(
        f"SOS queued: {test_result}"
    )

    # --------------------------------------------------------
    # Show queue
    # --------------------------------------------------------

    print()
    print("Current offline SOS queue:")

    queue = _load_queue()

    print(
        json.dumps(
            queue,
            indent=2
        )
    )

    # --------------------------------------------------------
    # Show emergency contacts
    # --------------------------------------------------------

    print()
    print("Emergency card:")

    try:

        card = get_offline_emergency_card(
            1
        )

        print(
            json.dumps(
                card,
                indent=2
            )
        )

    except Exception as exc:

        print(
            f"Could not load emergency card: {exc}"
        )

    print()
    print(
        f"Pending SOS count: {get_queued_sos_count()}"
    )

    print()
    print("Offline mode test completed.")
"""
Emergency/voice_sos.py
----------------------
WheelGuide Voice-Controlled Emergency SOS

Features
--------
1. Voice activation
2. Trigger phrases:
   - "help"
   - "help me"
   - "emergency"
   - "SOS"
   - "I need help"
3. Background listening thread
4. Text-to-speech confirmation
5. Current location retrieval
6. Integration with Emergency/sos.py
7. Safe microphone error handling
8. Safe speech-recognition error handling
9. Start / stop controls
10. Prevents repeated triggering
11. GUI callback support
12. Works with offline SOS fallback
"""

import os
import sys
import threading
import time

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


# ============================================================
# SPEECH RECOGNITION
# ============================================================

try:

    import speech_recognition as sr

    SPEECH_AVAILABLE = True

except ImportError:

    sr = None
    SPEECH_AVAILABLE = False


# ============================================================
# TEXT TO SPEECH
# ============================================================

try:

    import pyttsx3

    TTS_AVAILABLE = True

except ImportError:

    pyttsx3 = None
    TTS_AVAILABLE = False


# ============================================================
# SOS
# ============================================================

try:

    from Emergency.sos import send_sos

    SOS_AVAILABLE = True

except ImportError as exc:

    print(
        f"[WheelGuide Voice SOS] "
        f"SOS module unavailable: {exc}"
    )

    send_sos = None
    SOS_AVAILABLE = False


# ============================================================
# DEFAULT TRIGGER PHRASES
# ============================================================

TRIGGER_PHRASES = [
    "help me",
    "help",
    "emergency",
    "sos",
    "i need help",
    "please help",
    "call for help",
]


# ============================================================
# GLOBAL TTS ENGINE
# ============================================================

_tts_engine = None
_tts_lock = threading.Lock()


# ============================================================
# GET TTS ENGINE
# ============================================================

def _get_tts_engine():
    """
    Create the TTS engine only when needed.
    """

    global _tts_engine

    if not TTS_AVAILABLE:
        return None

    with _tts_lock:

        if _tts_engine is None:

            try:

                _tts_engine = pyttsx3.init()

                _tts_engine.setProperty(
                    "rate",
                    165
                )

                _tts_engine.setProperty(
                    "volume",
                    1.0
                )

            except Exception as exc:

                print(
                    f"[Voice SOS] "
                    f"TTS initialization failed: {exc}"
                )

                _tts_engine = None

    return _tts_engine


# ============================================================
# SPEAK
# ============================================================

def speak(text):
    """
    Speak a message through the computer speakers.

    If TTS is unavailable, the message is printed instead.
    """

    text = str(text).strip()

    if not text:
        return

    print(
        f"[WheelGuide Voice SOS] {text}"
    )

    engine = _get_tts_engine()

    if engine is None:
        return

    try:

        with _tts_lock:

            engine.say(text)
            engine.runAndWait()

    except Exception as exc:

        print(
            f"[Voice SOS] "
            f"TTS failed: {exc}"
        )


# ============================================================
# VOICE SOS LISTENER
# ============================================================

class VoiceSOSListener:
    """
    Background voice SOS listener.

    Example
    -------
    listener = VoiceSOSListener(
        user_id=1,
        get_location_fn=get_current_location,
        user_name="Tanvi",
        on_trigger=handle_result
    )

    listener.start()

    listener.stop()
    """

    def __init__(
        self,
        user_id,
        get_location_fn,
        user_name="WheelGuide user",
        on_trigger=None,
        phrases=None
    ):

        self.user_id = user_id

        self.get_location_fn = (
            get_location_fn
        )

        self.user_name = (
            user_name
            or "WheelGuide user"
        )

        self.on_trigger = on_trigger

        self.phrases = [
            phrase.lower().strip()
            for phrase in (
                phrases
                or TRIGGER_PHRASES
            )
            if phrase
        ]

        self._running = False

        self._thread = None

        self._microphone = None

        self._last_trigger_time = 0

        self.trigger_cooldown = 30

        if SPEECH_AVAILABLE:

            self.recognizer = (
                sr.Recognizer()
            )

            # Make recognition slightly more tolerant
            self.recognizer.energy_threshold = 300

            self.recognizer.dynamic_energy_threshold = True

            self.recognizer.pause_threshold = 0.8

            self.recognizer.phrase_threshold = 0.3

            self.recognizer.non_speaking_duration = 0.5

        else:

            self.recognizer = None


    # ========================================================
    # STATUS
    # ========================================================

    @property
    def is_running(self):
        """
        Returns True when voice listening is active.
        """

        return self._running


    # ========================================================
    # START
    # ========================================================

    def start(self):
        """
        Start the voice listener in a background thread.
        """

        if self._running:

            print(
                "[Voice SOS] Already running."
            )

            return False

        if not SPEECH_AVAILABLE:

            print(
                "[Voice SOS] "
                "SpeechRecognition is not installed."
            )

            speak(
                "Voice emergency feature is unavailable."
            )

            return False

        if not SOS_AVAILABLE:

            print(
                "[Voice SOS] "
                "SOS module is unavailable."
            )

            speak(
                "Emergency system is unavailable."
            )

            return False

        self._running = True

        self._thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name="WheelGuide-Voice-SOS"
        )

        self._thread.start()

        print(
            "[Voice SOS] Listener started."
        )

        return True


    # ========================================================
    # STOP
    # ========================================================

    def stop(self):
        """
        Stop voice listening.
        """

        self._running = False

        print(
            "[Voice SOS] Listener stopped."
        )


    # ========================================================
    # TOGGLE
    # ========================================================

    def toggle(self):
        """
        Toggle voice SOS on/off.
        """

        if self._running:

            self.stop()

            return False

        return self.start()


    # ========================================================
    # LISTEN LOOP
    # ========================================================

    def _listen_loop(self):
        """
        Main background microphone loop.
        """

        try:

            self._microphone = sr.Microphone()

        except Exception as exc:

            print(
                f"[Voice SOS] "
                f"Microphone unavailable: {exc}"
            )

            self._running = False

            self._notify_error(
                "Microphone is not available."
            )

            return

        # ----------------------------------------------------
        # CALIBRATE MICROPHONE
        # ----------------------------------------------------

        try:

            with self._microphone as source:

                print(
                    "[Voice SOS] "
                    "Calibrating microphone..."
                )

                self.recognizer.adjust_for_ambient_noise(
                    source,
                    duration=1
                )

        except Exception as exc:

            print(
                f"[Voice SOS] "
                f"Microphone calibration failed: {exc}"
            )

        # ----------------------------------------------------
        # READY
        # ----------------------------------------------------

        print(
            "[Voice SOS] "
            "Listening for emergency phrases..."
        )

        # ----------------------------------------------------
        # CONTINUOUS LISTENING
        # ----------------------------------------------------

        while self._running:

            try:

                with self._microphone as source:

                    audio = (
                        self.recognizer.listen(
                            source,
                            timeout=5,
                            phrase_time_limit=5
                        )
                    )

                if not self._running:
                    break

                # ------------------------------------------------
                # GOOGLE SPEECH RECOGNITION
                # ------------------------------------------------

                text = (
                    self.recognizer
                    .recognize_google(
                        audio
                    )
                    .lower()
                    .strip()
                )

                print(
                    f"[Voice SOS] Heard: {text}"
                )

                # ------------------------------------------------
                # CHECK TRIGGER
                # ------------------------------------------------

                if self._contains_trigger(text):

                    self._trigger_sos()

            except sr.WaitTimeoutError:

                continue

            except sr.UnknownValueError:

                # Speech couldn't be understood.
                continue

            except sr.RequestError as exc:

                print(
                    f"[Voice SOS] "
                    f"Speech service error: {exc}"
                )

                time.sleep(2)

            except OSError as exc:

                print(
                    f"[Voice SOS] "
                    f"Microphone error: {exc}"
                )

                time.sleep(2)

            except Exception as exc:

                print(
                    f"[Voice SOS] "
                    f"Listener error: {exc}"
                )

                time.sleep(1)

        print(
            "[Voice SOS] "
            "Listening loop ended."
        )


    # ========================================================
    # TRIGGER DETECTION
    # ========================================================

    def _contains_trigger(self, text):
        """
        Check whether recognized speech contains
        an emergency trigger phrase.
        """

        text = text.lower().strip()

        for phrase in self.phrases:

            if phrase in text:

                print(
                    f"[Voice SOS] "
                    f"Trigger detected: {phrase}"
                )

                return True

        return False


    # ========================================================
    # TRIGGER SOS
    # ========================================================

    def _trigger_sos(self):
        """
        Trigger the main SOS system.
        """

        # ----------------------------------------------------
        # COOLDOWN
        # ----------------------------------------------------

        now = time.time()

        if (
            now - self._last_trigger_time
            < self.trigger_cooldown
        ):

            print(
                "[Voice SOS] "
                "Trigger ignored because cooldown is active."
            )

            return

        self._last_trigger_time = now

        # ----------------------------------------------------
        # SPEAK WARNING
        # ----------------------------------------------------

        speak(
            "Emergency detected. "
            "Sending your location to your emergency contacts."
        )

        # ----------------------------------------------------
        # GET LOCATION
        # ----------------------------------------------------

        try:

            location = (
                self.get_location_fn()
            )

            if not location:

                raise ValueError(
                    "Location function returned no data."
                )

            lat, lon = location

        except Exception as exc:

            print(
                f"[Voice SOS] "
                f"Location error: {exc}"
            )

            speak(
                "I could not determine your current location."
            )

            result = {
                "success": False,
                "sent_online": False,
                "offline_queued": False,
                "contacts_notified": [],
                "contacts_failed": [],
                "message": "",
                "error": (
                    "Current location unavailable."
                ),
                "triggered_by": "voice_command",
            }

            self._notify_result(
                result
            )

            return

        # ----------------------------------------------------
        # SEND SOS
        # ----------------------------------------------------

        try:

            result = send_sos(
                user_id=self.user_id,
                lat=lat,
                lon=lon,
                user_name=self.user_name,
                triggered_by="voice_command"
            )

        except Exception as exc:

            print(
                f"[Voice SOS] "
                f"SOS failed: {exc}"
            )

            result = {
                "success": False,
                "sent_online": False,
                "offline_queued": False,
                "contacts_notified": [],
                "contacts_failed": [],
                "message": "",
                "error": str(exc),
                "triggered_by": "voice_command",
            }

        # ----------------------------------------------------
        # USER FEEDBACK
        # ----------------------------------------------------

        self._announce_result(
            result
        )

        # ----------------------------------------------------
        # GUI CALLBACK
        # ----------------------------------------------------

        self._notify_result(
            result
        )


    # ========================================================
    # ANNOUNCE RESULT
    # ========================================================

    def _announce_result(self, result):
        """
        Give spoken feedback after SOS.
        """

        if not result:

            speak(
                "Emergency system returned no response."
            )

            return

        if result.get(
            "sent_online"
        ):

            count = len(
                result.get(
                    "contacts_notified",
                    []
                )
            )

            if count == 1:

                speak(
                    "Emergency alert sent. "
                    "Your emergency contact has been notified."
                )

            else:

                speak(
                    "Emergency alert sent. "
                    f"{count} emergency contacts have been notified."
                )

            return

        if result.get(
            "offline_queued"
        ):

            speak(
                "There is no internet connection. "
                "Your emergency alert has been saved locally."
            )

            return

        error = result.get(
            "error"
        )

        if error:

            speak(
                "The emergency alert could not be sent. "
                "Please try the emergency button if possible."
            )

            return

        speak(
            "Emergency alert processing is complete."
        )


    # ========================================================
    # CALLBACK
    # ========================================================

    def _notify_result(self, result):
        """
        Safely notify the GUI/application.
        """

        if not self.on_trigger:
            return

        try:

            self.on_trigger(
                result
            )

        except Exception as exc:

            print(
                f"[Voice SOS] "
                f"Callback failed: {exc}"
            )


    # ========================================================
    # ERROR CALLBACK
    # ========================================================

    def _notify_error(self, message):
        """
        Send a simple error to the GUI callback.
        """

        result = {
            "success": False,
            "sent_online": False,
            "offline_queued": False,
            "contacts_notified": [],
            "contacts_failed": [],
            "message": "",
            "error": message,
            "triggered_by": "voice_command",
        }

        self._notify_result(
            result
        )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def create_voice_sos_listener(
    user_id,
    get_location_fn,
    user_name="WheelGuide user",
    on_trigger=None
):
    """
    Create a ready-to-use VoiceSOSListener.
    """

    return VoiceSOSListener(
        user_id=user_id,
        get_location_fn=get_location_fn,
        user_name=user_name,
        on_trigger=on_trigger
    )


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("WHEELGUIDE VOICE SOS TEST")
    print("=" * 60)

    if not SPEECH_AVAILABLE:

        print(
            "SpeechRecognition is unavailable."
        )

        sys.exit(1)


    def dummy_location():

        # Mumbai test coordinates
        return (
            19.0760,
            72.8777
        )


    def on_sos(result):

        print()
        print(
            "SOS CALLBACK RESULT:"
        )

        print(
            result
        )


    listener = VoiceSOSListener(
        user_id=1,
        get_location_fn=dummy_location,
        user_name="Test User",
        on_trigger=on_sos
    )

    if listener.start():

        print()
        print(
            "Listening..."
        )

        print(
            "Say: 'help me', 'emergency', "
            "'SOS', or 'I need help'."
        )

        print(
            "Press Ctrl+C to stop."
        )

        try:

            while listener.is_running:

                time.sleep(1)

        except KeyboardInterrupt:

            print(
                "\nStopping..."
            )

            listener.stop()

    print(
        "=" * 60
    )
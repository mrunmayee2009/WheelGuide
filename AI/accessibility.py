"""
AI/accessibility.py
-------------------

WheelGuide - AI-Powered Wheelchair Accessibility Analyzer

Features
--------
1. Gemini AI accessibility analysis.
2. Offline keyword-based fallback.
3. Structured accessibility information.
4. Accessibility score from 0-10.
5. Ramp, elevator/lift, accessible toilet and parking detection.
6. Step-free entrance and doorway analysis.
7. Confidence estimation.
8. Safe JSON parsing and validation.
9. Works even when Gemini/API key/internet is unavailable.

Public API
----------
get_accessibility_score(place_name, description_text="")

The existing WheelGuide GUI can continue using:

    result = get_accessibility_score(
        "City Mall",
        "Mall has a ramp and elevator..."
    )
"""

import os
import sys
import re
import json
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# PROJECT ROOT
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


# ---------------------------------------------------------------------------
# GEMINI CONFIGURATION
# ---------------------------------------------------------------------------

try:
    from config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# ---------------------------------------------------------------------------
# GEMINI SDK
# ---------------------------------------------------------------------------

try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True

except ImportError:
    genai = None
    GEMINI_AVAILABLE = False


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

MIN_SCORE = 0.0
MAX_SCORE = 10.0

MAX_DESCRIPTION_LENGTH = 12000

DEFAULT_GEMINI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash",
]


# ---------------------------------------------------------------------------
# KEYWORDS
# ---------------------------------------------------------------------------

POSITIVE_KEYWORDS = {
    "ramp": [
        "ramp",
        "wheelchair ramp",
        "accessible ramp",
        "sloped entrance",
    ],

    "elevator": [
        "elevator",
        "lift",
        "wheelchair lift",
        "accessible elevator",
    ],

    "accessible_toilet": [
        "accessible toilet",
        "accessible restroom",
        "accessible bathroom",
        "wheelchair toilet",
        "disabled toilet",
        "accessible washroom",
    ],

    "accessible_parking": [
        "accessible parking",
        "disabled parking",
        "wheelchair parking",
        "handicap parking",
        "reserved accessible parking",
    ],

    "step_free": [
        "step-free",
        "step free",
        "no steps",
        "level entrance",
        "level access",
        "ground floor access",
        "barrier free",
        "barrier-free",
    ],

    "wide_entrance": [
        "wide entrance",
        "wide doorway",
        "wide door",
        "wheelchair friendly entrance",
        "wheelchair-friendly entrance",
    ],

    "accessible_seating": [
        "accessible seating",
        "wheelchair seating",
        "wheelchair space",
        "accessible seats",
    ],
}


NEGATIVE_KEYWORDS = {
    "stairs": [
        "stairs only",
        "staircase only",
        "only stairs",
        "stairs",
        "multiple stairs",
        "many stairs",
    ],

    "no_ramp": [
        "no ramp",
        "without ramp",
        "no wheelchair ramp",
        "ramp unavailable",
    ],

    "no_elevator": [
        "no elevator",
        "no lift",
        "without elevator",
        "without lift",
        "elevator unavailable",
        "lift unavailable",
    ],

    "narrow_entrance": [
        "narrow entrance",
        "narrow doorway",
        "narrow door",
        "too narrow",
    ],

    "not_accessible": [
        "not accessible",
        "not wheelchair accessible",
        "wheelchair inaccessible",
        "inaccessible",
        "not suitable for wheelchair",
    ],

    "no_accessible_toilet": [
        "no accessible toilet",
        "no accessible restroom",
        "no accessible bathroom",
        "accessible toilet unavailable",
    ],

    "no_accessible_parking": [
        "no accessible parking",
        "no disabled parking",
        "no wheelchair parking",
        "accessible parking unavailable",
    ],
}


# ---------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------------------------

def _clean_text(value: Any) -> str:
    """
    Convert any input into clean text.
    """
    if value is None:
        return ""

    text = str(value)

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _clamp_score(score: Any) -> float:
    """
    Safely convert a score to a number between 0 and 10.
    """

    try:
        score = float(score)
    except (TypeError, ValueError):
        return 5.0

    score = max(MIN_SCORE, min(MAX_SCORE, score))

    return round(score, 1)


def _find_keyword_matches(text: str, keyword_groups: Dict[str, list]) -> Dict[str, list]:
    """
    Find matching keywords for each accessibility category.
    """

    text = text.lower()

    matches = {}

    for category, keywords in keyword_groups.items():

        found = []

        for keyword in keywords:

            if keyword.lower() in text:
                found.append(keyword)

        matches[category] = found

    return matches


def _contains_any(text: str, keywords: list) -> bool:
    """
    Return True when any keyword is present.
    """

    text = text.lower()

    return any(keyword.lower() in text for keyword in keywords)


# ---------------------------------------------------------------------------
# GEMINI SETUP
# ---------------------------------------------------------------------------

def _has_valid_api_key() -> bool:
    """
    Check whether a usable Gemini API key exists.
    """

    if not GEMINI_API_KEY:
        return False

    key = str(GEMINI_API_KEY).strip()

    if not key:
        return False

    invalid_values = [
        "PASTE_YOUR_API_KEY_HERE",
        "PASTE_YOUR_GEMINI_API_KEY_HERE",
        "YOUR_API_KEY",
        "YOUR_GEMINI_API_KEY",
    ]

    if key in invalid_values:
        return False

    return True


def _configure_gemini() -> bool:
    """
    Configure Gemini safely.

    Returns
    -------
    bool
        True when Gemini can be configured.
    """

    if not GEMINI_AVAILABLE:
        return False

    if not _has_valid_api_key():
        return False

    try:

        genai.configure(
            api_key=str(GEMINI_API_KEY).strip()
        )

        return True

    except Exception as exc:

        print(
            f"[WheelGuide Accessibility] "
            f"Gemini configuration failed: {exc}"
        )

        return False


# ---------------------------------------------------------------------------
# GEMINI RESPONSE PARSING
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from a Gemini response.

    Handles:
        {...}

    and:

        ```json
        {...}
        ```
    """

    if not text:
        return None

    text = text.strip()

    # Remove markdown fences
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    # Direct JSON
    try:

        data = json.loads(text)

        if isinstance(data, dict):
            return data

    except json.JSONDecodeError:
        pass

    # Try to locate JSON object inside additional text
    match = re.search(
        r"\{.*\}",
        text,
        flags=re.DOTALL
    )

    if not match:
        return None

    json_text = match.group(0)

    try:

        data = json.loads(json_text)

        if isinstance(data, dict):
            return data

    except json.JSONDecodeError:
        return None

    return None


# ---------------------------------------------------------------------------
# BOOLEAN NORMALIZATION
# ---------------------------------------------------------------------------

def _normalize_bool(value: Any) -> Optional[bool]:
    """
    Convert Gemini's boolean-like output into:
        True
        False
        None
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):

        if value == 1:
            return True

        if value == 0:
            return False

    text = str(value).strip().lower()

    if text in {
        "true",
        "yes",
        "available",
        "present",
        "accessible",
    }:
        return True

    if text in {
        "false",
        "no",
        "unavailable",
        "absent",
        "not available",
        "not accessible",
    }:
        return False

    return None


# ---------------------------------------------------------------------------
# RESULT VALIDATION
# ---------------------------------------------------------------------------

def _normalize_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and validate an AI result.
    """

    result = {
        "score": _clamp_score(data.get("score", 5)),
        "has_ramp": _normalize_bool(data.get("has_ramp")),
        "has_elevator": _normalize_bool(
            data.get("has_elevator")
        ),
        "has_accessible_toilet": _normalize_bool(
            data.get("has_accessible_toilet")
        ),
        "has_accessible_parking": _normalize_bool(
            data.get("has_accessible_parking")
        ),
        "step_free_entrance": _normalize_bool(
            data.get("step_free_entrance")
        ),
        "wide_entrance": _normalize_bool(
            data.get("wide_entrance")
        ),
        "accessible_seating": _normalize_bool(
            data.get("accessible_seating")
        ),
        "reasoning": _clean_text(
            data.get("reasoning", "")
        ),
        "confidence": _clamp_score(
            data.get("confidence", 5)
        ),
    }

    if not result["reasoning"]:

        result["reasoning"] = (
            "Accessibility information was analyzed from "
            "the available description."
        )

    return result


# ---------------------------------------------------------------------------
# GEMINI SCORING
# ---------------------------------------------------------------------------

def score_with_gemini(
    place_name: str,
    description_text: str
) -> Optional[Dict[str, Any]]:
    """
    Ask Gemini to analyze wheelchair accessibility.

    Returns
    -------
    dict or None

    None means Gemini could not be used and the caller
    should use the offline fallback.
    """

    if not _configure_gemini():
        return None

    place_name = _clean_text(place_name)
    description_text = _clean_text(description_text)

    # Prevent unnecessarily huge requests
    description_text = description_text[:MAX_DESCRIPTION_LENGTH]

    prompt = f"""
You are the accessibility analysis engine for an application
called WheelGuide.

WheelGuide helps wheelchair users understand the accessibility
of real-world places.

IMPORTANT RULES:

1. Use ONLY the information supplied below.
2. Do NOT invent accessibility features.
3. If information is not available, use null.
4. Do not assume that a place is accessible simply because it
   is a modern building.
5. A positive statement is required before marking a feature true.
6. A negative statement is required before marking a feature false.
7. Give a score from 0 to 10.
8. 10 means the supplied information indicates excellent
   wheelchair accessibility.
9. 0 means the supplied information indicates extremely poor
   accessibility.
10. If there is insufficient information, keep the score close
    to 5 and reduce confidence.

PLACE:
{place_name}

AVAILABLE INFORMATION:
{description_text}

Return STRICT JSON only.

Required format:

{{
    "score": 0,
    "has_ramp": null,
    "has_elevator": null,
    "has_accessible_toilet": null,
    "has_accessible_parking": null,
    "step_free_entrance": null,
    "wide_entrance": null,
    "accessible_seating": null,
    "confidence": 0,
    "reasoning": "Short explanation based only on the supplied information."
}}
"""

    # Try several model names for compatibility
    for model_name in DEFAULT_GEMINI_MODELS:

        try:

            model = genai.GenerativeModel(
                model_name
            )

            response = model.generate_content(
                prompt
            )

            response_text = getattr(
                response,
                "text",
                ""
            )

            data = _extract_json(
                response_text
            )

            if not data:
                continue

            result = _normalize_result(data)

            result["source"] = "gemini_ai"

            return result

        except Exception as exc:

            print(
                f"[WheelGuide Accessibility] "
                f"Gemini model {model_name} failed: {exc}"
            )

            continue

    return None


# ---------------------------------------------------------------------------
# OFFLINE HEURISTIC
# ---------------------------------------------------------------------------

def score_with_heuristic(
    description_text: str
) -> Dict[str, Any]:
    """
    Offline accessibility scoring.

    This is deliberately conservative and only uses information
    contained in the supplied text.
    """

    text = _clean_text(
        description_text
    ).lower()

    positive_matches = _find_keyword_matches(
        text,
        POSITIVE_KEYWORDS
    )

    negative_matches = _find_keyword_matches(
        text,
        NEGATIVE_KEYWORDS
    )

    positive_count = sum(
        len(values)
        for values in positive_matches.values()
    )

    negative_count = sum(
        len(values)
        for values in negative_matches.values()
    )

    # -------------------------------------------------------
    # Feature detection
    # -------------------------------------------------------

    has_ramp = None
    has_elevator = None
    has_accessible_toilet = None
    has_accessible_parking = None
    step_free_entrance = None
    wide_entrance = None
    accessible_seating = None

    # Ramp
    if _contains_any(
        text,
        POSITIVE_KEYWORDS["ramp"]
    ):
        has_ramp = True

    elif _contains_any(
        text,
        NEGATIVE_KEYWORDS["no_ramp"]
    ):
        has_ramp = False

    # Elevator
    if _contains_any(
        text,
        POSITIVE_KEYWORDS["elevator"]
    ):
        has_elevator = True

    elif _contains_any(
        text,
        NEGATIVE_KEYWORDS["no_elevator"]
    ):
        has_elevator = False

    # Accessible toilet
    if _contains_any(
        text,
        POSITIVE_KEYWORDS["accessible_toilet"]
    ):
        has_accessible_toilet = True

    elif _contains_any(
        text,
        NEGATIVE_KEYWORDS["no_accessible_toilet"]
    ):
        has_accessible_toilet = False

    # Accessible parking
    if _contains_any(
        text,
        POSITIVE_KEYWORDS["accessible_parking"]
    ):
        has_accessible_parking = True

    elif _contains_any(
        text,
        NEGATIVE_KEYWORDS["no_accessible_parking"]
    ):
        has_accessible_parking = False

    # Step-free
    if _contains_any(
        text,
        POSITIVE_KEYWORDS["step_free"]
    ):
        step_free_entrance = True

    elif _contains_any(
        text,
        NEGATIVE_KEYWORDS["stairs"]
    ):
        step_free_entrance = False

    # Wide entrance
    if _contains_any(
        text,
        POSITIVE_KEYWORDS["wide_entrance"]
    ):
        wide_entrance = True

    elif _contains_any(
        text,
        NEGATIVE_KEYWORDS["narrow_entrance"]
    ):
        wide_entrance = False

    # Accessible seating
    if _contains_any(
        text,
        POSITIVE_KEYWORDS["accessible_seating"]
    ):
        accessible_seating = True

    # -------------------------------------------------------
    # Score
    # -------------------------------------------------------

    # Start from neutral
    score = 5.0

    # Positive evidence
    score += positive_count * 0.7

    # Negative evidence
    score -= negative_count * 1.2

    # Strong negative accessibility statements
    if _contains_any(
        text,
        NEGATIVE_KEYWORDS["not_accessible"]
    ):
        score -= 3.0

    # Strong positive combination
    positive_features = [
        has_ramp,
        has_elevator,
        has_accessible_toilet,
        has_accessible_parking,
        step_free_entrance,
        wide_entrance,
        accessible_seating,
    ]

    confirmed_positive = sum(
        feature is True
        for feature in positive_features
    )

    confirmed_negative = sum(
        feature is False
        for feature in positive_features
    )

    # Small bonus for multiple confirmed features
    if confirmed_positive >= 3:
        score += 0.8

    if confirmed_positive >= 5:
        score += 0.7

    # Penalty for several confirmed barriers
    if confirmed_negative >= 2:
        score -= 0.8

    score = _clamp_score(score)

    # -------------------------------------------------------
    # Confidence
    # -------------------------------------------------------

    total_evidence = (
        positive_count +
        negative_count
    )

    if total_evidence == 0:
        confidence = 2.0

    elif total_evidence == 1:
        confidence = 3.5

    elif total_evidence <= 3:
        confidence = 5.5

    elif total_evidence <= 6:
        confidence = 7.0

    else:
        confidence = 8.0

    # -------------------------------------------------------
    # Reasoning
    # -------------------------------------------------------

    if positive_count == 0 and negative_count == 0:

        reasoning = (
            "The supplied information does not contain clear "
            "wheelchair accessibility details. The score is "
            "therefore neutral and should not be treated as "
            "confirmation of accessibility."
        )

    else:

        reasoning = (
            f"Offline analysis found {positive_count} positive "
            f"accessibility indicator(s) and {negative_count} "
            f"potential barrier indicator(s) in the supplied text."
        )

    return {
        "score": score,

        "has_ramp": has_ramp,

        "has_elevator": has_elevator,

        "has_accessible_toilet":
            has_accessible_toilet,

        "has_accessible_parking":
            has_accessible_parking,

        "step_free_entrance":
            step_free_entrance,

        "wide_entrance":
            wide_entrance,

        "accessible_seating":
            accessible_seating,

        "confidence": confidence,

        "reasoning": reasoning,

        "source": "offline_heuristic",
    }


# ---------------------------------------------------------------------------
# ACCESSIBILITY LEVEL
# ---------------------------------------------------------------------------

def get_accessibility_level(
    score: Any
) -> str:
    """
    Convert numerical score into a readable category.
    """

    score = _clamp_score(score)

    if score >= 8.5:
        return "Excellent"

    if score >= 7:
        return "Good"

    if score >= 5:
        return "Moderate"

    if score >= 3:
        return "Limited"

    return "Poor"


# ---------------------------------------------------------------------------
# USER-FRIENDLY SUMMARY
# ---------------------------------------------------------------------------

def get_accessibility_summary(
    result: Dict[str, Any]
) -> str:
    """
    Create a short GUI-friendly accessibility summary.
    """

    if not result:
        return "Accessibility information unavailable."

    score = _clamp_score(
        result.get("score", 5)
    )

    level = get_accessibility_level(
        score
    )

    return (
        f"Accessibility Score: {score}/10 "
        f"({level}). "
        f"{_clean_text(result.get('reasoning', ''))}"
    )


# ---------------------------------------------------------------------------
# MAIN PUBLIC FUNCTION
# ---------------------------------------------------------------------------

def get_accessibility_score(
    place_name: str,
    description_text: str = ""
) -> Dict[str, Any]:
    """
    Main WheelGuide accessibility analysis function.

    Parameters
    ----------
    place_name : str
        Name/address of the place.

    description_text : str
        Reviews, description, accessibility information,
        or other text supplied by the user.

    Returns
    -------
    dict

    Example
    -------
    result = get_accessibility_score(
        "City Mall",
        "The mall has a wheelchair ramp and elevators."
    )

    print(result["score"])
    print(result["has_ramp"])
    """

    place_name = _clean_text(
        place_name
    )

    description_text = _clean_text(
        description_text
    )

    # -------------------------------------------------------
    # Handle empty place name
    # -------------------------------------------------------

    if not place_name:

        place_name = "Unknown place"

    # -------------------------------------------------------
    # Handle empty description
    # -------------------------------------------------------

    if not description_text:

        description_text = (
            f"No accessibility information was supplied "
            f"for {place_name}."
        )

    # -------------------------------------------------------
    # Try Gemini
    # -------------------------------------------------------

    result = score_with_gemini(
        place_name,
        description_text
    )

    if result is not None:

        result["source"] = "gemini_ai"

        result["accessibility_level"] = (
            get_accessibility_level(
                result["score"]
            )
        )

        result["summary"] = (
            get_accessibility_summary(
                result
            )
        )

        return result

    # -------------------------------------------------------
    # Offline fallback
    # -------------------------------------------------------

    result = score_with_heuristic(
        description_text
    )

    result["source"] = "offline_heuristic"

    result["accessibility_level"] = (
        get_accessibility_level(
            result["score"]
        )
    )

    result["summary"] = (
        get_accessibility_summary(
            result
        )
    )

    return result


# ---------------------------------------------------------------------------
# SIMPLE TEST FUNCTION
# ---------------------------------------------------------------------------

def run_demo():
    """
    Test the accessibility analyzer without the GUI.
    """

    sample = """
    This shopping mall has a wheelchair ramp at the main entrance.
    Elevators are available to all floors.
    There is an accessible toilet on the ground floor.
    Accessible parking spaces are available near the entrance.
    The entrance is wide and step-free.
    """

    result = get_accessibility_score(
        "City Mall",
        sample
    )

    print("\n" + "=" * 60)
    print("WHEELGUIDE ACCESSIBILITY ANALYSIS")
    print("=" * 60)

    print(
        f"Score       : {result['score']}/10"
    )

    print(
        f"Level       : {result['accessibility_level']}"
    )

    print(
        f"Ramp        : {result['has_ramp']}"
    )

    print(
        f"Elevator    : {result['has_elevator']}"
    )

    print(
        f"Toilet      : {result['has_accessible_toilet']}"
    )

    print(
        f"Parking     : {result['has_accessible_parking']}"
    )

    print(
        f"Step-free   : {result['step_free_entrance']}"
    )

    print(
        f"Wide Entry  : {result['wide_entrance']}"
    )

    print(
        f"Seating     : {result['accessible_seating']}"
    )

    print(
        f"Confidence  : {result['confidence']}/10"
    )

    print(
        f"Source      : {result['source']}"
    )

    print(
        f"Reason      : {result['reasoning']}"
    )

    print("=" * 60)


# ---------------------------------------------------------------------------
# DIRECT EXECUTION
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_demo()
"""
AI/construction.py
--------------------
Feature 8: Under-construction area detection.

Two complementary approaches, both implemented here:
 1. Visual detection: YOLOv8 (stock COCO weights already recognize some
    relevant objects, e.g. "traffic cone", "truck" (construction trucks) —
    used as a proxy signal for construction zones from a photo/camera frame.
 2. Text/crowd-report detection: users (or an admin) can mark a location as
    "under construction" manually, or the app can flag it if enough app
    users report it recently. This is stored in the database and checked
    by Maps/route.py when planning a route, so construction zones can be
    avoided even when no camera is pointed at them.

For a stronger custom model, train YOLOv8 on a labeled dataset of barricades,
cones, scaffolding, and "under construction" signage (Roboflow has public
datasets for this) and point CUSTOM_MODEL_PATH to your trained weights.
"""

import os
import cv2

CUSTOM_MODEL_PATH = None  # e.g. "AI/models/construction_best.pt"
FALLBACK_MODEL = "yolov8n.pt"

# COCO classes that commonly correlate with construction/road-work zones
CONSTRUCTION_PROXY_LABELS = {"traffic light", "truck", "stop sign"}
# Note: stock COCO does not include "traffic cone" or "barricade" classes.
# These are included here as placeholders for when a custom model is used.
CUSTOM_CONSTRUCTION_LABELS = {"traffic cone", "barricade", "scaffolding",
                               "construction sign", "cone"}

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    from ultralytics import YOLO
    path = CUSTOM_MODEL_PATH if CUSTOM_MODEL_PATH and os.path.exists(CUSTOM_MODEL_PATH) else FALLBACK_MODEL
    _model = YOLO(path)
    return _model


def detect_construction_in_image(image_path: str, conf_threshold: float = 0.35):
    """Runs detection and returns whether the scene likely shows a
    construction/road-work zone, based on detected object classes."""
    model = _load_model()
    results = model.predict(source=image_path, conf=conf_threshold, verbose=False)

    detections = []
    construction_signal = 0
    relevant_labels = CONSTRUCTION_PROXY_LABELS | CUSTOM_CONSTRUCTION_LABELS

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names.get(cls_id, str(cls_id)).lower()
            conf = float(box.conf[0])
            detections.append({"label": label, "confidence": round(conf, 3)})
            if label in relevant_labels:
                construction_signal += 1

    is_construction = construction_signal >= 2  # need at least 2 supporting cues

    return {
        "under_construction": is_construction,
        "signal_strength": construction_signal,
        "detections": detections,
        "note": ("Stock model gives limited accuracy for this feature. "
                 "Train a custom YOLOv8 model on cones/barricades/scaffolding "
                 "for production-grade accuracy.") if not CUSTOM_MODEL_PATH else "",
    }


# ---------------------------------------------------------------------
# Crowd-sourced / manual construction reporting (works fully offline once
# synced, and doesn't depend on computer vision at all)
# ---------------------------------------------------------------------

def report_construction_zone(lat: float, lon: float, note: str = ""):
    """Saves a user-reported construction zone into the places/graph data
    so Maps/route.py can avoid it. Stored as a simple JSON list for
    simplicity; swap for a DB table if you want full history/expiry."""
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "Database", "construction_zones.json")
    zones = []
    if os.path.exists(path):
        with open(path, "r") as f:
            zones = json.load(f)
    zones.append({"lat": lat, "lon": lon, "note": note})
    with open(path, "w") as f:
        json.dump(zones, f, indent=2)
    return True


def get_reported_construction_zones():
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "Database", "construction_zones.json")
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    test_image = "Images/sample_construction.jpg"
    if os.path.exists(test_image):
        print(detect_construction_in_image(test_image))
    else:
        print("Place a test image at Images/sample_construction.jpg to test this module.")

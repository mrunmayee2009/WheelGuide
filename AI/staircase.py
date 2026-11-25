"""
AI/staircase.py
----------------
Feature 9: Staircase detection.

Uses Ultralytics YOLOv8 to analyze a photo (from a folder, camera, or a
frame captured via cv2) and flag whether stairs are visible.

NOTE for your diploma report: the stock "yolov8n.pt" model is trained on
the COCO dataset, which does NOT have a "staircase" class. For a real
production feature you would fine-tune YOLOv8 on a custom labeled dataset
of staircase images (Roboflow has public "stairs detection" datasets you
can use for transfer learning). This file is written so that swapping in
your own trained weights is a one-line change (see CUSTOM_MODEL_PATH
below) — the rest of the pipeline (image in -> boxes out -> GUI warning)
does not need to change.
"""

import os
import cv2

CUSTOM_MODEL_PATH = None  # e.g. "AI/models/staircase_best.pt" once you train one
FALLBACK_MODEL = "yolov8n.pt"

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    from ultralytics import YOLO
    path = CUSTOM_MODEL_PATH if CUSTOM_MODEL_PATH and os.path.exists(CUSTOM_MODEL_PATH) else FALLBACK_MODEL
    _model = YOLO(path)
    return _model


def detect_staircase_in_image(image_path: str, conf_threshold: float = 0.35):
    """
    Runs object detection on an image and returns a dict:
        {
          "staircase_detected": bool,
          "confidence": float,
          "annotated_image_path": str or None,
          "detections": [ {"label": str, "confidence": float, "box": [...]} ]
        }

    With the stock COCO model, we treat detections of "stairs"-adjacent
    classes as a proxy (there is no official COCO "stairs" class, so this
    also runs a simple edge/line-based heuristic as a secondary check).
    """
    model = _load_model()
    results = model.predict(source=image_path, conf=conf_threshold, verbose=False)

    detections = []
    staircase_detected = False
    best_conf = 0.0

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names.get(cls_id, str(cls_id))
            conf = float(box.conf[0])
            detections.append({
                "label": label,
                "confidence": round(conf, 3),
                "box": [round(x, 1) for x in box.xyxy[0].tolist()],
            })
            if label.lower() in ("stairs", "staircase", "stairway"):
                staircase_detected = True
                best_conf = max(best_conf, conf)

    # Secondary heuristic: repeated horizontal lines are a classic visual
    # signature of stairs. Used only when the ML model has no dedicated
    # staircase class (i.e. stock COCO weights).
    heuristic_flag, heuristic_conf = _line_heuristic(image_path)
    if not staircase_detected and heuristic_flag:
        staircase_detected = True
        best_conf = heuristic_conf

    annotated_path = None
    if results:
        annotated = results[0].plot()
        annotated_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Images", "staircase_annotated.jpg",
        )
        cv2.imwrite(annotated_path, annotated)

    return {
        "staircase_detected": staircase_detected,
        "confidence": round(best_conf, 3),
        "annotated_image_path": annotated_path,
        "detections": detections,
    }


def _line_heuristic(image_path: str, min_parallel_lines: int = 4):
    """Detects repeated near-horizontal parallel lines using Canny edges +
    Hough transform, a common visual cue for staircases."""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False, 0.0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, 3.14159 / 180, threshold=80,
                                 minLineLength=60, maxLineGap=10)
        if lines is None:
            return False, 0.0

        horizontal_count = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs((y2 - y1) / (x2 - x1 + 1e-6))
            if angle < 0.2:  # nearly horizontal
                horizontal_count += 1

        detected = horizontal_count >= min_parallel_lines
        confidence = min(0.9, horizontal_count / 15) if detected else 0.0
        return detected, confidence
    except Exception as e:
        print(f"[staircase.py] heuristic failed: {e}")
        return False, 0.0


def detect_staircase_from_webcam(camera_index: int = 0):
    """Captures a single frame from the webcam and runs detection on it.
    Useful for a 'scan my surroundings' button in the GUI."""
    cap = cv2.VideoCapture(camera_index)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return {"error": "Could not access webcam."}

    temp_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Images", "webcam_capture.jpg",
    )
    cv2.imwrite(temp_path, frame)
    return detect_staircase_in_image(temp_path)


if __name__ == "__main__":
    test_image = "Images/sample_stairs.jpg"
    if os.path.exists(test_image):
        print(detect_staircase_in_image(test_image))
    else:
        print("Place a test image at Images/sample_stairs.jpg to test this module.")

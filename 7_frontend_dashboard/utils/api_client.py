# utils/api_client.py
import base64, io, random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
import requests  # Needed for real backend calls

# Toggle mock mode here or set from session in Streamlit
MOCK_MODE = True
API_BASE_URL = "http://127.0.0.1:8000"  # Used when mock = False

# CLASSES used in both mock and real modes
CLASSES = ["diatom", "rotifer", "copepod", "algae"]  # FIXED typo (rotifer)

def set_mode(mock=True, api_base=None):
    """Enable or disable mock mode from Streamlit."""
    global MOCK_MODE, API_BASE_URL
    MOCK_MODE = mock
    if api_base:
        API_BASE_URL = api_base


# ---------------------------------------------------------------------------
# 🔵 MOCK HELPERS (used when backend not running)
# ---------------------------------------------------------------------------
def _random_boxes(img_w, img_h, n=3):
    boxes = []
    for i in range(n):
        w = random.uniform(0.05, 0.25) * img_w
        h = random.uniform(0.05, 0.25) * img_h
        x1 = random.randint(0, max(1, img_w - int(w)))
        y1 = random.randint(0, max(1, img_h - int(h)))
        x2 = x1 + int(w)
        y2 = y1 + int(h)
        cls = random.choice(CLASSES)
        score = round(random.uniform(0.6, 0.99), 2)
        boxes.append({
            "x1": x1, "y1": y1,
            "x2": x2, "y2": y2,
            "class": cls,
            "score": score
        })
    return boxes


def _annotate_image_bytes(image_bytes, boxes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)

    for b in boxes:
        draw.rectangle(
            [b["x1"], b["y1"], b["x2"], b["y2"]],
            outline=(0, 255, 0), width=2
        )
        draw.text(
            (b["x1"] + 3, b["y1"] + 3),
            f"{b['class']} {b['score']}",
            fill=(255, 255, 255)
        )

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 🔥 REAL BACKEND COMMUNICATION (FastAPI)
# ---------------------------------------------------------------------------
def post_predict(image_bytes):
    """
    Send image to /predict endpoint or return MOCK response.
    Returns:
        {
            "timestamp": ...,
            "total": ...,
            "counts": {...},
            "boxes": [...],
            "annotated_bytes": JPEG bytes
        }
    """
    if MOCK_MODE:
        # MOCK MODE
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        boxes = _random_boxes(w, h, n=random.randint(1, 6))

        counts = {}
        for b in boxes:
            counts[b["class"]] = counts.get(b["class"], 0) + 1

        annotated = _annotate_image_bytes(image_bytes, boxes)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total": sum(counts.values()),
            "counts": counts,
            "boxes": boxes,
            "annotated_bytes": annotated
        }

    # REAL BACKEND MODE
    files = {"file": ("upload.jpg", image_bytes, "image/jpeg")}

    # POST to backend predict endpoint (no trailing slash to match FastAPI route)
    try:
        res = requests.post(f"{API_BASE_URL}/predict", files=files, timeout=15)
    except Exception as e:
        raise Exception(f"Failed to reach backend at {API_BASE_URL}: {e}")

    if res.status_code not in (200, 201):
        raise Exception(f"Backend error ({res.status_code}): {res.text}")

    data = res.json()

    # Convert base64 annotated image → bytes
    if "annotated_image" not in data:
        raise Exception(f"Backend response missing 'annotated_image': {data}")
    annotated_bytes = base64.b64decode(data["annotated_image"])

    return {
        "timestamp": data["timestamp"],
        "total": data["total"],
        "counts": data["counts"],
        "boxes": [],   # Optional: backend can be extended later
        "annotated_bytes": annotated_bytes
    }


def get_stats(hours=48):
    """Returns a timeseries for analytics."""
    if MOCK_MODE:
        now = datetime.utcnow()
        times = [now - timedelta(hours=i) for i in range(hours)][::-1]
        rows = []

        for t in times:
            row = {"timestamp": t.isoformat()}
            for c in CLASSES:
                row[c] = random.randint(0, 12)
            row["total"] = sum(row[c] for c in CLASSES)
            rows.append(row)

        return {"timeseries": rows}

    # REAL BACKEND MODE
    res = requests.get(f"{API_BASE_URL}/stats/")
    return res.json()


def get_history(limit=100):
    """Returns history of past detections."""
    if MOCK_MODE:
        now = datetime.utcnow()
        history = []

        for i in range(limit):
            t = now - timedelta(hours=i * 2)
            counts = {c: random.randint(0, 6) for c in CLASSES}
            total = sum(counts.values())

            history.append({
                "timestamp": t.isoformat(),
                "counts": counts,
                "total": total,
                "annotated_bytes": None
            })

        return {"history": history}

    # REAL BACKEND MODE
    res = requests.get(f"{API_BASE_URL}/history/")
    return res.json()


def get_alerts():
    """Mock alerts only for now."""
    if MOCK_MODE:
        now = datetime.utcnow()
        alerts = [
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "level": "yellow",
                "message": "Diatom spike detected"
            },
            {
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "level": "red",
                "message": "Algae bloom risk detected"
            }
        ]
        return {"alerts": alerts}

    # backend alerts endpoint can be added later
    return {"alerts": []}


def get_status():
    """System status."""
    if MOCK_MODE:
        return {
            "service": "AI Inference Engine (MOCK)",
            "status": "online",
            "last_processed": datetime.utcnow().isoformat(),
            "uptime_seconds": 123456
        }

    return {"status": "online"}

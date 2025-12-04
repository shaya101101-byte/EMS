# utils/request_logger.py
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Backend folder paths
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_JSONS_DIR = BACKEND_DIR  # root backend folder where resp_analyze.json lives
UPLOADED_IMAGES_DIR = os.path.join(BACKEND_DIR, "uploaded_images")


def list_history_jsons() -> List[str]:
    """List all JSON files in backend/ folder that contain history/analysis data."""
    json_files = []
    try:
        for f in os.listdir(HISTORY_JSONS_DIR):
            if f.endswith(".json") and ("resp" in f or "analyze" in f or "history" in f):
                json_files.append(f)
    except Exception as e:
        print(f"Error listing JSON files: {e}")
    return sorted(json_files, reverse=True)


def read_history_json(filename: str) -> Dict[str, Any]:
    """Read a single JSON history file from backend/."""
    try:
        path = os.path.join(HISTORY_JSONS_DIR, filename)
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            return {
                "filename": filename,
                "timestamp": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
                "data": data,
                "size": os.path.getsize(path),
            }
    except Exception as e:
        print(f"Error reading {filename}: {e}")
    return {"filename": filename, "error": "Could not read file"}


def list_uploaded_images() -> List[Dict[str, Any]]:
    """List all uploaded images with thumbnails and metadata."""
    images = []
    try:
        for f in os.listdir(UPLOADED_IMAGES_DIR):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                path = os.path.join(UPLOADED_IMAGES_DIR, f)
                mtime = os.path.getmtime(path)
                images.append({
                    "filename": f,
                    "url": f"/uploaded_images/{f}",
                    "timestamp": datetime.fromtimestamp(mtime).isoformat(),
                    "size": os.path.getsize(path),
                })
    except Exception as e:
        print(f"Error listing uploaded images: {e}")
    return sorted(images, key=lambda x: x["timestamp"], reverse=True)


def get_db_history(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve analysis history from the SQLite database."""
    try:
        from database.db import get_history as db_get_history
        return db_get_history(limit=limit)
    except Exception as e:
        print(f"Error retrieving DB history: {e}")
        return []


def log_request(endpoint: str, method: str, status_code: int, duration_ms: float):
    """Log a backend API request (for future event tracking)."""
    # Placeholder: can be extended to write to a log file or database
    pass

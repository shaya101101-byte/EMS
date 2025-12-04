# database/db.py
import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, JSON, select
from sqlalchemy.sql import func
from datetime import datetime
import json

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

detections = Table(
    "detections",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("timestamp", DateTime, default=datetime.utcnow),
    Column("image_path", String, nullable=True),
    Column("counts_json", String, nullable=False),  # JSON string
    Column("total", Integer, nullable=False),
    Column("dominant", String, nullable=True),
    Column("quality", String, nullable=True),
    Column("confidence", String, nullable=True)
)

metadata.create_all(engine)

# helper functions
def insert_detection(record: dict):
    with engine.begin() as conn:
        result = conn.execute(detections.insert().values(
            timestamp=record.get("timestamp"),
            image_path=record.get("image_path"),
            counts_json=json.dumps(record.get("counts", {})),
            total=record.get("total", 0),
            dominant=record.get("dominant"),
            quality=record.get("quality"),
            confidence=str(record.get("confidence"))
        ))
        return result.inserted_primary_key[0]

def get_history(limit=100):
    with engine.connect() as conn:
        sel = select(detections).order_by(detections.c.timestamp.desc()).limit(limit)
        # Use mappings() so rows can be accessed by column name across SQLAlchemy versions
        results = conn.execute(sel)
        out = []
        for row in results.mappings():
            # Build image_url for history items
            image_url = ""
            image_path = row["image_path"]
            if image_path:
                # Normalize path: remove backslashes, handle Windows paths
                normalized = image_path.replace("\\", "/")
                if normalized.startswith("/"):
                    normalized = normalized[1:]
                # If path is relative (e.g., static/results/...), build URL
                if not normalized.startswith("http") and not os.path.isabs(image_path):
                    image_url = f"http://127.0.0.1:8000/{normalized}"
                elif normalized.startswith("static/") or normalized.startswith("uploaded_images/"):
                    image_url = f"http://127.0.0.1:8000/{normalized}"
            
            out.append({
                "id": row["id"],
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] is not None else None,
                "created_at": row["timestamp"].isoformat() if row["timestamp"] is not None else None,
                "image_path": row["image_path"],
                "image_url": image_url,
                "counts": json.loads(row["counts_json"]) if row["counts_json"] else {},
                "total": row["total"],
                "dominant": row["dominant"],
                "quality": row["quality"],
                "confidence": row["confidence"],
                "summary": f"Detected {row['total']} organisms",
                "preds": []
            })
        return out

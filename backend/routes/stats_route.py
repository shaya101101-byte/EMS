# routes/stats_route.py
from fastapi import APIRouter
from database.db import get_history
from datetime import datetime, timedelta
import random

router = APIRouter()

@router.get("/stats")
def stats(hours: int = 48):
    # very simple timeseries derived from history (mock if empty)
    hist = get_history(limit=hours)
    if hist:
        # transform into timeseries
        timeseries = []
        for rec in reversed(hist):
            ts = rec["timestamp"]
            timeseries.append({
                "timestamp": ts,
                "total": rec["total"],
                **rec["counts"]
            })
        return {"timeseries": timeseries}
    else:
        # fallback mock timeseries
        now = datetime.utcnow()
        times = [now - timedelta(hours=i) for i in range(hours)][::-1]
        data = []
        classes = ["diatom","rotifer","copepod","algae"]
        for t in times:
            row = {"timestamp": t.isoformat()}
            for c in classes:
                row[c] = random.randint(0, 12)
            row["total"] = sum(row[c] for c in classes)
            data.append(row)
        return {"timeseries": data}

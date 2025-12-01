# backend/routes/stats_api.py
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/api")

@router.get('/stats')
def get_stats(hours: int = Query(24, ge=1, le=168)):
    # Dummy current values
    current = {
        "turbidity": round(random.uniform(0.5, 5.0), 2),
        "ph": round(random.uniform(6.5, 8.5), 2),
        "temperature": round(random.uniform(20.0, 30.0), 2),
        "do_level": round(random.uniform(6.0, 9.5), 2),
        "tds": int(random.uniform(80, 250)),
        "conductivity": int(random.uniform(200, 1200))
    }

    # Build hourly history for turbidity (most recent first)
    now = datetime.now()
    history = []
    for i in range(hours):
        t = now - timedelta(hours=(hours - 1 - i))
        hour_label = t.strftime('%I %p').lstrip('0')
        history.append({"hour": hour_label, "turbidity": round(random.uniform(0.5, 5.0), 2)})

    return {"current": current, "history": history}

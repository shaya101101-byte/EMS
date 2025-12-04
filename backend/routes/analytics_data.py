from fastapi import APIRouter
import sqlite3
import os
import json
from collections import defaultdict
from datetime import datetime

router = APIRouter()


@router.get('/analytics-data')
def analytics_data():
    """Return aggregated analytics data from history.db

    Response shape:
    {
      "speciesCounts": {species: count, ...},
      "safetyStats": {"safe": X, "warning": Y, "dangerous": Z},
      "dailyTrend": [{"date":"YYYY-MM-DD","count":N}, ...]
    }
    """
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'history.db')
    db_path = os.path.normpath(db_path)
    if not os.path.exists(db_path):
        return {"speciesCounts": {}, "safetyStats": {"safe": 0, "warning": 0, "dangerous": 0}, "dailyTrend": []}

    species_counts = defaultdict(int)
    safety_counters = {"safe": 0, "warning": 0, "dangerous": 0}
    daily = defaultdict(int)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute('SELECT timestamp, counts_json, quality FROM detections')
        rows = cur.fetchall()
        for ts, counts_json, quality in rows:
            # counts_json may be JSON string
            try:
                counts = json.loads(counts_json) if counts_json else {}
            except Exception:
                counts = {}
            for sp, c in counts.items():
                try:
                    species_counts[sp] += int(c)
                except Exception:
                    try:
                        species_counts[sp] += float(c)
                    except Exception:
                        pass

            # safety: use quality field if present
            q = (quality or '').lower() if quality is not None else ''
            if 'good' in q:
                safety_counters['safe'] += 1
            elif 'moderate' in q or 'caution' in q or 'warn' in q:
                safety_counters['warning'] += 1
            else:
                # anything else treat as dangerous if not empty, otherwise count as safe
                if q:
                    safety_counters['dangerous'] += 1
                else:
                    safety_counters['safe'] += 0

            # daily trend from timestamp
            try:
                if ts:
                    # ts may be ISO or SQLite datetime; parse date portion
                    if isinstance(ts, str):
                        date_part = ts.split('T')[0].split(' ')[0]
                    else:
                        # if datetime object
                        date_part = datetime.fromisoformat(str(ts)).date().isoformat()
                    daily[date_part] += 1
            except Exception:
                pass
    finally:
        conn.close()

    # Build daily trend sorted by date
    trend = []
    for d in sorted(daily.keys()):
        trend.append({"date": d, "count": daily[d]})

    return {
        "speciesCounts": dict(species_counts),
        "safetyStats": safety_counters,
        "dailyTrend": trend
    }

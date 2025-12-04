# Backend Data Storage Summary

## What Gets Stored Automatically

When you upload an image and click **"Analyze"**, the backend automatically saves data in **THREE locations**:

### 1️⃣ **SQLite Database** (`backend/database/history.db`)
**Automatically saved** via `insert_detection()` in the analyze endpoint.

**Fields stored:**
- `id` — Unique analysis ID (auto-increment)
- `timestamp` — When analysis was performed (UTC)
- `image_path` — Path to uploaded image (e.g., `uploaded_images/image.jpg`)
- `counts_json` — JSON object with per-class counts (e.g., `{"diatom": 5, "algae": 3}`)
- `total` — Total organisms detected
- `dominant` — Most common class name
- `quality` — Overall verdict (Safe/Caution/Unsafe)
- `confidence` — Average confidence score of top class

**Where:** `C:\EMS_short\backend\database\history.db`

**Access:** Admin dashboard at `/admin/history` reads from this database

---

### 2️⃣ **Uploaded Images** (`backend/uploaded_images/`)
**Automatically saved** by FastAPI when you upload the file.

**Files stored:**
- Original image with timestamp filename (e.g., `20251204_123231_test6.jpg`)

**Where:** `C:\EMS_short\backend\uploaded_images/`

**Access:** Admin dashboard at `/admin/uploads` shows all images with metadata

---

### 3️⃣ **Analysis Artifacts** (`backend/static/results/`)
**Automatically saved** by the analysis service.

**Files stored:**
- **Annotated image** — Original image with bounding boxes drawn (PNG)
- **Charts** — Pie chart and bar chart (PNG, base64-encoded in response)
- **PDF report** — Complete analysis report (base64-encoded in response)

**Where:** `C:\EMS_short\backend/static/results/`

**Naming:** `annotated_{uuid}.png` (e.g., `annotated_e8c5fb76.png`)

---

## Full Analysis Response JSON

When you analyze an image, the backend returns this JSON:

```json
{
  "total_detections": 12,
  "per_class": [
    {
      "class": "diatom",
      "count": 8,
      "percentage": 66.7,
      "avg_confidence": 0.95,
      "safety": "Safe",
      "description": "No immediate concern detected for this class."
    },
    {
      "class": "algae",
      "count": 4,
      "percentage": 33.3,
      "avg_confidence": 0.87,
      "safety": "Caution",
      "description": "Presence of this class may indicate moderate contamination; review recommended."
    }
  ],
  "overall_verdict": {
    "verdict": "Caution",
    "reason": "One or more cautionary classes detected."
  },
  "annotated_image_url": "http://127.0.0.1:8000/static/results/annotated_e8c5fb76.png",
  "annotated_image_base64": "",
  "pie_chart_base64": "iVBORw0KGgoAAAANSUhEUgAAA...",
  "bar_chart_base64": "iVBORw0KGgoAAAANSUhEUgAAA...",
  "pdf_base64": "JVBERi0xLjQKJeLj..."
}
```

---

## Admin Dashboard Storage

The admin dashboard is **READ-ONLY** and automatically pulls data from:

### `/admin/history`
- Reads from **SQLite database** (`history.db`)
- Shows all past analyses with timestamps
- Displays: detection count, quality verdict, confidence score

### `/admin/uploads`
- Reads from **uploaded_images folder**
- Shows all uploaded image files with metadata

### `/admin/api/stats`
- Queries **SQLite database**
- Aggregates statistics: total analyses, per-class counts

### `/admin/view/{id}`
- Reads **SQLite database** by analysis ID
- Shows full JSON details of specific analysis

---

## Storage Flow Diagram

```
User uploads image
        ↓
Frontend → POST /analyze-image
        ↓
Backend receives file
        ↓
✅ Save image → uploaded_images/
✅ Run analysis
✅ Save annotated image → static/results/
✅ Save to database → history.db (NEW!)
        ↓
Return JSON response
        ↓
Admin Dashboard reads from all three locations:
  - Database history
  - Uploaded images
  - Analysis artifacts
```

---

## Verification Checklist

✅ **Image upload storage** — Automatic in `backend/uploaded_images/`

✅ **Analysis results storage** — Automatic in SQLite `history.db` (FIXED!)

✅ **Analysis artifacts** — Automatic in `backend/static/results/`

✅ **Admin visibility** — All data visible in admin dashboard (`/admin?token=ADMIN_TOKEN`)

✅ **Real-time updates** — Admin dashboard polls every 3-5 seconds

✅ **Historical tracking** — All past analyses stored permanently in database

---

## Testing

1. **Upload an image and analyze it**
2. **Check admin dashboard**: `http://127.0.0.1:8000/admin/history?token=ADMIN_TOKEN`
3. **Verify data appears** in the history list within 3-5 seconds
4. **Click "View"** to see full JSON analysis result
5. **Check uploads page**: `http://127.0.0.1:8000/admin/uploads?token=ADMIN_TOKEN`
6. **Verify image appears** with metadata

All data will be **saved permanently** in the database and folders! ✅


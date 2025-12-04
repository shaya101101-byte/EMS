# Quick Start - Live Dashboard YOLO Analysis

## 🚀 Start Backend (Terminal 1)
```powershell
cd C:\EMS_short
python backend/main.py
```
✅ Wait for: `INFO: Uvicorn running on http://127.0.0.1:8000`

## 🚀 Start Frontend (Terminal 2)
```powershell
cd C:\EMS_short\7_frontend_dashboard
npm start
```
✅ Wait for: Frontend running on http://localhost:3000

## 🌐 Open Browser
```
http://localhost:3000/live_dashboard.html
```

---

## 📸 Live Analysis Workflow

### 1️⃣ Start Feed
- Click **"Start Feed"** button
- Allow webcam access
- See live video in container

### 2️⃣ Capture Snapshot
- Click **"Capture Snapshot"** button
- Get confirmation: ✅ "Snapshot Uploaded!"
- **Analyze** button appears

### 3️⃣ Analyze with YOLO
- Click **"Analyze"** button (green)
- Wait 5-10 seconds for inference
- See results:
  - 🦠 Species name
  - 📝 Description
  - 🔢 Count
  - 📊 Confidence %
  - Status: Safe/Unsafe
  - Bounding boxes image

### 4️⃣ Download PDF Report
- Click **"Download Report"** button (blue)
- PDF downloads automatically
- Contains full analysis + image

---

## ⚠️ If Upload Fails

**Error: "Video not playing"**
- Solution: Click "Stop Feed" → "Start Feed"

**Error: "Video not ready"**
- Solution: Wait 3 seconds, click "Capture Snapshot" again

**Error: "Server error: 500"**
- Solution: Check backend logs for ❌ messages

---

## 🔍 Check Backend Models

### Terminal Command
```powershell
cd C:\EMS_short
python -c "from backend.routes.live_detect import detection_model, classification_model; print('Detection:', detection_model is not None); print('Classification:', classification_model is not None)"
```

### Expected Output
```
Detection: True
Classification: True
```

---

## 📝 Expected Results

### Analysis JSON Response
```json
{
  "species": "Guinardia_delicatula",
  "meaning": "✅ Safe to use.",
  "count": 5,
  "confidence": 0.876,
  "safe": true,
  "annotated_image": "/snapshots/annotated/1734000123456_annotated.jpg"
}
```

### PDF Report Contains
- ✅ Title: "AquaSafe AI - Analysis Report"
- ✅ Generated timestamp
- ✅ Species name, count, confidence, status
- ✅ Per-class statistics table
- ✅ Annotated image with bounding boxes

---

## 🎯 Key Features Implemented

✅ Dual YOLO Models (Detection + Classification)
✅ Full Bounding Box Annotation
✅ Per-Class Statistics (count, %, confidence)
✅ Safety Assessment (Safe/Caution/Unsafe)
✅ PDF Report Generation with Embedded Image
✅ Comprehensive Error Handling
✅ Detailed Console Logging
✅ Video Feed Validation
✅ Responsive UI with Results Display

---

## 📊 Model Information

| Model | File | Size | Classes |
|-------|------|------|---------|
| Detection | `best.pt` | 6.2 MB | 8 generic classes |
| Classification | `bestc.pt` | 10.5 MB | 88 species names |

---

## 🐛 Still Having Issues?

See: `TROUBLESHOOTING_GUIDE.md` for detailed debugging steps

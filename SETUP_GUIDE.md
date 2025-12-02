# EMS_short - Quick Setup & Run Guide

## 1️⃣ Install Dependencies

**Important:** Use this exact command on Windows PowerShell:

```powershell
Set-Location 'C:\EMS_short\backend'
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

❌ **DO NOT use:** `pip install -r requirements.txt`  
✅ **DO use:** `.\.venv\Scripts\python -m pip install -r requirements.txt`

## 2️⃣ Start Backend

```powershell
Set-Location 'C:\EMS_short\backend'
.\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
Loaded YOLOv8 model: C:\EMS_short\backend\models\best.pt
YOLO class names: {...}
INFO:     Application startup complete
```

## 3️⃣ Start Frontend

In a new PowerShell terminal:

```powershell
Set-Location 'C:\EMS_short\7_frontend_dashboard'
python -m http.server 3000
```

Expected output:
```
Serving HTTP on 0.0.0.0 port 3000 (http://0.0.0.0:3000/)
```

## 4️⃣ Use the Application

Open your browser to:
```
http://localhost:3000
```

1. Click **Upload**
2. Select an image (JPG/PNG)
3. Click **Analyze**
4. Wait 10-20 seconds for inference
5. View results in **Analytics** page

---

## What's Fixed

✅ **YOLO Model:** Properly loads and stores class names  
✅ **Inference:** Correctly decodes image bytes for YOLO processing  
✅ **Response:** `/predict` returns proper JSON with `annotated_image_url`, `detections`, `counts`  
✅ **Frontend:** Analytics page displays annotated image and detection results  
✅ **Paths:** Output images saved to `static/results/` and served via `/static/results/`  
✅ **CORS:** Enabled for localhost development  

---

## Model Status Check

After backend starts, you should see:
```
YOLO class names: {0: 'organism1', 1: 'organism2', ...}
```

If you see `class0, class1, ...` then your dataset YAML needs updating.

---

## Troubleshooting

**"Unsupported image type" error:**
→ Fixed! Backend now properly decodes image bytes to numpy array.

**"404 Not Found" in analytics:**
→ Ensure backend is running on port 8000 and image files are accessible via `/static/results/`.

**"No detections found":**
→ Check YOLO model confidence (currently set to 0.35 in inference_engine.py).

---

## Project Structure

```
C:\EMS_short\
├── backend/
│   ├── main.py (FastAPI app)
│   ├── routes/predict.py (Image upload endpoint)
│   ├── services/model_loader.py (YOLO model)
│   ├── services/inference_engine.py (Inference logic)
│   ├── models/best.pt (YOLO weights)
│   ├── static/results/ (Output images)
│   ├── uploaded_images/ (Uploaded images)
│   └── .venv/ (Python virtualenv)
└── 7_frontend_dashboard/
    ├── upload.html (Upload page)
    ├── analytics.html (Results page)
    ├── js/analytics.js (Results display)
    └── js/api-client.js (API calls)
```

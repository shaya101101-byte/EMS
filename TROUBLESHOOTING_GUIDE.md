# Troubleshooting Guide - Snapshot Upload & Analysis

## ✅ What Was Fixed

### Issue 1: "Upload Failed" Error
**Symptoms:**
- Click "Capture Snapshot" and get "❌ Upload failed" message
- Video might not be playing or canvas is empty

**Root Cause:**
- Video not loaded or stream not started
- Video dimensions are 0x0 (canvas has no content)
- No validation before attempting upload

**Solution Implemented:**
```javascript
// NEW VALIDATION CHECKS:
1. Check if video has a stream: video.srcObject !== null
2. Check if video is playing: !video.paused && !video.ended
3. Check if video has valid dimensions: video.videoWidth > 0 && video.videoHeight > 0
4. Provide specific error messages for each case
5. Add console.error logging for debugging
```

---

## 🎯 Step-by-Step Instructions to Test

### Step 1: Start Backend
```powershell
cd C:\EMS_short
python backend/main.py
# Should see:
# 🔄 YOLO MODEL LOADING INITIATED
# ✅ Detection model (best.pt) loaded successfully
# ✅ Classification model (bestc.pt) loaded successfully
# INFO: Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Start Frontend
```powershell
cd C:\EMS_short\7_frontend_dashboard
npm start
# Should see:
# Frontend running on http://localhost:3000
```

### Step 3: Open Live Dashboard
- URL: `http://localhost:3000/live_dashboard.html`
- Should load without errors (no JSON parsing error)

### Step 4: Start Video Feed
1. Click **"Start Feed"** button
2. Allow webcam access when prompted
3. Video should show in the container
4. FPS counter should show > 0

**If stuck:**
- Check browser console (F12 → Console tab)
- Check if camera is already in use by another app
- Try "Stop Feed" → "Start Feed" again

### Step 5: Capture Snapshot
1. Click **"Capture Snapshot"** button
2. Should see: ✅ **"Snapshot Uploaded! Click 'Analyze' to run YOLO detection."**

**If you get error:**
- **"Video not playing"**: Click "Stop Feed" then "Start Feed"
- **"Video not ready"**: Wait 2-3 seconds for video to stabilize, try again
- **"Canvas blob conversion failed"**: Browser issue, refresh page
- **"Server error: 500"**: Check backend logs, model issue

### Step 6: Click Analyze
1. Click **"Analyze"** button (turns green during analysis)
2. Wait 5-10 seconds (YOLO inference takes time)
3. Should see analysis results with:
   - 🦠 **Species**: Species name (NOT "No Model")
   - 📝 **Description**: Safety assessment
   - 🔢 **Count**: Number of detections
   - 📊 **Confidence**: Overall confidence percentage
   - Status: ✅ **SAFE** or ⚠️ **UNSAFE**
   - **Annotated Image**: With colored bounding boxes

**If you get "No Model":**
- Backend didn't load YOLO models
- Check backend startup logs for ❌ messages
- Verify models exist: `C:\EMS_short\backend\models\best.pt` and `bestc.pt`

### Step 7: Download Report
1. Click **"Download Report"** button (blue)
2. PDF should download to your Downloads folder
3. Open `aquasafe_report_[ID].pdf`
4. Contains:
   - Analysis results (species, count, confidence, status)
   - Per-class statistics table
   - Annotated image with bounding boxes
   - Footer with branding

---

## 🔍 Common Issues & Solutions

### Issue: "❌ Upload Failed" immediately after "Capture Snapshot"

**Check 1: Is the video playing?**
```javascript
// Open browser console (F12) and run:
const video = document.getElementById('liveVideoFeed');
console.log('Video srcObject:', video.srcObject);
console.log('Video paused:', video.paused);
console.log('Video dimensions:', video.videoWidth, 'x', video.videoHeight);
```

**Expected output:**
```
Video srcObject: MediaStream {id: "...", active: true}
Video paused: false
Video dimensions: 1280 x 720
```

**If dimensions are 0x0:**
- Video isn't ready yet
- Solution: Wait 3 seconds and try again

**If srcObject is null:**
- "Start Feed" wasn't clicked or failed
- Solution: Click "Stop Feed" → "Start Feed"

---

### Issue: "❌ Analysis failed: Server error: 500"

**Check Backend Logs:**
```powershell
# Look for these patterns in backend console:
🔍 Analysis started for snap_id=1734000000000
✅ Image loaded: (720, 1280, 3)
🤖 Running detection inference...
❌ Inference error: [error message]
```

**Common backend errors:**
1. **"YOLO model is None"**
   - Models failed to load during startup
   - Solution: Restart backend, check for ❌ in model loading logs

2. **"CUDA out of memory"**
   - GPU memory exhausted
   - Solution: Restart backend, or try CPU inference

3. **"File not found"** for snapshot
   - Uploaded image got deleted
   - Solution: Take a new snapshot

---

### Issue: Analysis works but shows "No Model"

**This means:**
- Upload succeeded (snapshot saved)
- Analyze endpoint was called
- But detection_model is None

**Solution:**
1. Check backend startup logs for model loading
2. Verify file paths are correct:
   - `C:\EMS_short\backend\models\best.pt` (6.2 MB)
   - `C:\EMS_short\backend\models\bestc.pt` (10.5 MB)
3. Restart backend

---

### Issue: PDF Download Opens But Has Blank Content

**Check Backend Logs:**
```powershell
📄 Generating report for snap_id=1734000000000
✅ Report generated successfully | Size: 125432 bytes
```

**If you see error:**
```
⚠️ Image embed failed: [error]
```

**Solution:**
- Annotated image wasn't saved properly
- Try analyzing again with a clearer image

---

## 📊 Expected Logs

### Successful Upload Flow
```
📸 Snapshot uploaded: ID=1734000123456, File=backend/snapshots/1734000123456.jpg
```

### Successful Analysis Flow
```
🔍 Analysis started for snap_id=1734000123456
✅ Image loaded: (720, 1280, 3)
🤖 Running detection inference...
✅ Detection completed
📊 Detections found: 5
🏷️ Detection classes available: {0: 'class1', 1: 'class2', ..., 7: 'class8'}
   Box 0: Guinardia_delicatula (conf=0.876)
   Box 1: Skeletonema (conf=0.812)
   ...
📋 Results: species=Guinardia_delicatula, count=5, safe=True, confidence=0.876
💾 Annotated image saved: backend/annotated/1734000123456_annotated.jpg
✅ Analysis completed successfully
```

### Successful PDF Generation
```
📄 Generating report for snap_id=1734000123456
✅ Annotated image embedded in PDF
✅ Report generated successfully | Size: 145623 bytes
```

---

## 🧪 Quick Debug Commands

### Check Backend is Running
```powershell
# Visit in browser or PowerShell:
Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing
# Should return HTML (not an error)
```

### Check Models are Loaded
```powershell
cd C:\EMS_short
python -c "
from backend.routes.live_detect import detection_model, classification_model
print('Detection model loaded:', detection_model is not None)
print('Classification model loaded:', classification_model is not None)
"
```

### Test Upload Endpoint
```powershell
# Create a test image and upload it
python -c "
from PIL import Image
import requests
import io

# Create test image
img = Image.new('RGB', (640, 480), color='red')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

# Upload
files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
response = requests.post('http://127.0.0.1:8000/api/upload-snapshot/', files=files)
print('Upload response:', response.json())
"
```

---

## ✅ Success Checklist

- [ ] Backend starts without errors
- [ ] Both YOLO models load successfully
- [ ] Frontend loads at localhost:3000/live_dashboard.html
- [ ] "Start Feed" shows video
- [ ] "Capture Snapshot" uploads successfully
- [ ] "Analyze" shows species name (not "No Model")
- [ ] Shows detection count, confidence, boxes, status
- [ ] Annotated image appears with bounding boxes
- [ ] "Download Report" opens PDF with full results

---

## 📝 Files Modified

1. **`backend/routes/live_detect.py`**
   - Complete rewrite with detailed logging
   - Proper model loading with validation
   - Robust error handling
   - Full PDF generation

2. **`7_frontend_dashboard/live_dashboard.html`**
   - Video validation before capture
   - Better error messages
   - Response validation
   - Improved error handling in analyze/download

3. **`7_frontend_dashboard/js/live_dashboard.js`**
   - Fixed stats URL to use backend port 8000
   - Removed blocking alerts for optional stats

---

**Last Updated**: December 4, 2025
**Status**: ✅ Ready for Testing

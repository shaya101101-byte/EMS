"""
live_detect.py
Live model detection endpoints for snapshot → analyze → report workflow.
Uses unified YoloPipeline from app.state.yolo (initialized in main.py).
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from datetime import datetime
import os
import cv2
import io
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter
import numpy as np
from PIL import Image
import base64
from ultralytics import YOLO

router = APIRouter()

# ============================================
# GLOBALS & DIRECTORIES
# ============================================
snapshots_store = {}
# Use absolute paths based on backend directory location
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_DIR = os.path.join(BACKEND_DIR, "snapshots")
ANNOTATED_DIR = os.path.join(BACKEND_DIR, "annotated")

# Ensure directories exist
Path(SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)
Path(ANNOTATED_DIR).mkdir(parents=True, exist_ok=True)

# ============================================
# 1️⃣ UPLOAD SNAPSHOT
# ============================================
@router.post("/api/upload-snapshot/")
async def upload_snapshot(image: UploadFile = File(...)):
    """
    Receive a snapshot from frontend and save it.
    Returns snapshot ID for later analysis.
    """
    try:
        if not image.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Generate unique ID based on timestamp
        snap_id = int(datetime.utcnow().timestamp() * 1000)
        
        # Read image bytes
        contents = await image.read()
        
        # Save original image
        img_path = f"{SNAPSHOT_DIR}/{snap_id}.jpg"
        with open(img_path, "wb") as f:
            f.write(contents)
        
        # Store metadata
        snapshots_store[snap_id] = {
            "path": img_path,
            "timestamp": datetime.utcnow().isoformat(),
            "filename": image.filename,
            "analyzed": False
        }
        
        print(f"📸 Snapshot uploaded: ID={snap_id}, File={img_path}")
        
        return {
            "id": snap_id,
            "message": "Snapshot uploaded successfully"
        }
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ============================================
# 2️⃣ ANALYZE SNAPSHOT WITH YOLO (UNIFIED PIPELINE)
# ============================================
@router.get("/api/analyze/{snap_id}/")
async def analyze_snapshot(snap_id: int, request: Request):
    """
    Run YOLO models on uploaded snapshot via the unified YoloPipeline.
    Pipeline is pre-initialized and attached to app.state.yolo in main.py.
    Returns JSON with species, detections, boxes, and per-class statistics.
    """
    try:
        print(f"\n🔍 Analysis started for snap_id={snap_id}")

        if snap_id not in snapshots_store:
            print(f"❌ Snapshot not found: snap_id={snap_id}")
            raise HTTPException(status_code=404, detail="Snapshot not found")

        snap_data = snapshots_store[snap_id]
        img_path = snap_data["path"]

        if not os.path.exists(img_path):
            print(f"❌ Snapshot file not found: {img_path}")
            raise HTTPException(status_code=404, detail="Snapshot file not found")

        # Access the unified pipeline from app state
        yolo = getattr(request.app.state, 'yolo', None)
        if yolo is None:
            print("❌ Yolo pipeline not initialized on app.state")
            raise HTTPException(status_code=500, detail="Yolo pipeline not initialized on server")

        # Run unified pipeline (detection + per-crop classification)
        try:
            res = yolo.run(image_path=img_path)
        except Exception as e:
            print(f"❌ Pipeline run failed: {e}")
            raise HTTPException(status_code=500, detail=f"Pipeline run failed: {e}")

        detections = res.get('detections', [])
        annotated_img = res.get('annotated', None)

        # Convert detections to boxes_info format
        boxes_info = []
        for d in detections:
            bbox = d.get('bbox', [])
            cname = d.get('class_name', 'unknown')
            confv = float(d.get('confidence', 0.0))
            boxes_info.append({'box': bbox, 'confidence': confv, 'class': cname})

        count = len(boxes_info)

        # Aggregate per-class stats
        counts = {}
        conf_sums = {}
        for b in boxes_info:
            cname = b['class']
            counts[cname] = counts.get(cname, 0) + 1
            conf_sums[cname] = conf_sums.get(cname, 0.0) + b.get('confidence', 0.0)

        per_class = []
        for cname, cnt in counts.items():
            avg_conf = (conf_sums.get(cname, 0.0) / cnt) if cnt > 0 else 0.0
            percentage = round((cnt / count * 100), 1) if count > 0 else 0.0
            unsafe_classes = ["rotifer"]
            caution_classes = ["algae"]
            safety = 'Unsafe' if cname.lower() in unsafe_classes else ('Caution' if cname.lower() in caution_classes else 'Safe')
            per_class.append({
                'class': cname,
                'count': cnt,
                'percentage': percentage,
                'avg_confidence': round(avg_conf, 3),
                'safety': safety
            })

        per_class_sorted = sorted(per_class, key=lambda x: (x['count'], x['avg_confidence']), reverse=True)

        # Determine primary species and safety status
        if count == 0:
            species_name = "None Detected"
            meaning = "No microorganisms detected in the image."
            safe = True
            overall_confidence = 0.0
        else:
            primary = per_class_sorted[0]
            species_name = primary['class']
            overall_confidence = primary['avg_confidence']
            if primary['safety'] == 'Unsafe':
                meaning = f"⚠️ {species_name} is a high-risk organism. Immediate action recommended."
                safe = False
            elif primary['safety'] == 'Caution':
                meaning = f"⚠️ {species_name} detected. Review recommended."
                safe = True
            else:
                meaning = f"✅ {species_name} detected. Safe to use."
                safe = True

        # Save annotated image if provided by pipeline
        annotated_filename = f"{snap_id}_annotated.jpg"
        annotated_path = os.path.join(ANNOTATED_DIR, annotated_filename)
        if annotated_img is not None:
            try:
                cv2.imwrite(annotated_path, annotated_img)
                print(f"💾 Annotated image saved: {annotated_path}")
            except Exception as e:
                print(f"⚠️ Failed to save annotated image: {e}")
                annotated_path = None
        else:
            annotated_path = None

        # Update snapshot store with analysis results
        snap_data["analyzed"] = True
        snap_data["species"] = species_name
        snap_data["meaning"] = meaning
        snap_data["count"] = count
        snap_data["safe"] = safe
        snap_data["confidence"] = overall_confidence
        snap_data["annotated_image"] = annotated_path
        snap_data["boxes"] = boxes_info
        snap_data["per_class_stats"] = per_class_sorted

        print(f"✅ Analysis completed: {count} detections found, primary species: {species_name}\n")

        return {
            "id": snap_id,
            "species": species_name,
            "meaning": meaning,
            "count": count,
            "safe": safe,
            "confidence": overall_confidence,
            "annotated_image": f"/snapshots/annotated/{annotated_filename}" if annotated_path else None,
            "boxes": boxes_info,
            "per_class_stats": per_class_sorted
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# --- INSERT: POST /analyze (accept uploaded image and return YOLO results) ---
def _ensure_models(app):
    """Lazily load detection and classification models and cache on app.state."""
    if getattr(app.state, 'yolo_models', None) is not None:
        return app.state.yolo_models

    # Use absolute paths for model loading
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    det_path = os.path.join(base_dir, 'models', 'best.pt')
    cls_path = os.path.join(base_dir, 'models', 'bestc.pt')

    print(f"[DEBUG] Loading detection model from: {det_path}")
    print(f"[DEBUG] Loading classification model from: {cls_path}")
    
    det_model = YOLO(det_path)
    cls_model = YOLO(cls_path)

    app.state.yolo_models = { 'det': det_model, 'cls': cls_model }
    return app.state.yolo_models


@router.post('/analyze')
async def analyze_upload(image: UploadFile = File(...), request: Request = None):
    """Accept uploaded image, run detection+classification, return JSON with base64 annotated image and snapshot ID for PDF download."""
    try:
        if image is None:
            raise HTTPException(status_code=400, detail='No file uploaded')

        # Save snapshot first so we have an ID for PDF download
        snap_id = int(datetime.utcnow().timestamp() * 1000)
        contents = await image.read()
        img_path = f"{SNAPSHOT_DIR}/{snap_id}.jpg"
        with open(img_path, "wb") as f:
            f.write(contents)
        
        snapshots_store[snap_id] = {
            "path": img_path,
            "timestamp": datetime.utcnow().isoformat(),
            "filename": image.filename,
            "analyzed": False
        }
        print(f"📸 Snapshot saved: ID={snap_id}")

        models = _ensure_models(request.app if request is not None else None)
        det_model = models['det']
        cls_model = models['cls']

        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail='Invalid image')

        # Run detection
        det_res = det_model(img, conf=0.25)
        det0 = det_res[0]

        detections = []
        annotated = img.copy()

        boxes = []
        try:
            if hasattr(det0, 'boxes') and det0.boxes is not None:
                xyxy = det0.boxes.xyxy.cpu().numpy()
                confs = det0.boxes.conf.cpu().numpy()
                cls_idxs = det0.boxes.cls.cpu().numpy() if hasattr(det0.boxes, 'cls') else [0]*len(confs)
                for (b, c, cf) in zip(xyxy, cls_idxs, confs):
                    x1, y1, x2, y2 = [int(v) for v in b]
                    boxes.append((x1, y1, x2, y2, int(c), float(cf)))
        except Exception:
            boxes = []

        for (x1, y1, x2, y2, cls_idx, det_conf) in boxes:
            h, w = img.shape[:2]
            x1c, y1c = max(0, x1), max(0, y1)
            x2c, y2c = min(w-1, x2), min(h-1, y2)
            if x2c <= x1c or y2c <= y1c:
                continue

            crop = img[y1c:y2c, x1c:x2c]
            # classify crop
            try:
                cls_res = cls_model(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                r0 = cls_res[0]
                class_name = None
                class_conf = None
                if getattr(r0, 'probs', None) is not None:
                    try:
                        arr = r0.probs.cpu().numpy()
                    except Exception:
                        arr = np.array(r0.probs)
                    top_idx = int(np.argmax(arr))
                    top_conf = float(np.max(arr))
                    class_name = cls_model.names.get(top_idx, str(top_idx)) if getattr(cls_model, 'names', None) else str(top_idx)
                    class_conf = top_conf
                elif getattr(r0, 'boxes', None) is not None and len(r0.boxes) > 0:
                    p = r0.boxes[0]
                    class_conf = float(getattr(p, 'conf', det_conf))
                    class_name = cls_model.names.get(int(getattr(p, 'cls', 0)), str(int(getattr(p, 'cls', 0))))
                else:
                    class_name = det_model.names.get(cls_idx, f'class_{cls_idx}') if getattr(det_model, 'names', None) else f'class_{cls_idx}'
                    class_conf = float(det_conf)
            except Exception:
                class_name = det_model.names.get(cls_idx, f'class_{cls_idx}') if getattr(det_model, 'names', None) else f'class_{cls_idx}'
                class_conf = float(det_conf)

            detections.append({
                'class_name': str(class_name),
                'confidence': float(round(class_conf, 4)),
                'bbox': [int(x1c), int(y1c), int(x2c), int(y2c)]
            })

            # draw
            color = (0,255,0)
            cv2.rectangle(annotated, (x1c, y1c), (x2c, y2c), color, 2)
            label = f"{class_name} {class_conf:.2f}"
            cv2.putText(annotated, label, (x1c, max(10, y1c-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        counts = {}
        max_conf = {}
        for d in detections:
            cname = d['class_name']
            counts[cname] = counts.get(cname, 0) + 1
            max_conf[cname] = max(max_conf.get(cname, 0.0), float(d['confidence']))

        unsafe_classes = {'rotifer', 'parasite', 'pathogen'}
        safety_status = 'Safe'
        for cname in counts.keys():
            if cname.lower() in unsafe_classes:
                safety_status = 'Unsafe'
                break

        # Save annotated image for PDF and static serve
        annotated_filename = f"{snap_id}_annotated.jpg"
        annotated_path = os.path.join(ANNOTATED_DIR, annotated_filename)
        try:
            cv2.imwrite(annotated_path, annotated)
            print(f"💾 Annotated image saved: {annotated_path}")
        except Exception as e:
            print(f"⚠️ Failed to save annotated image: {e}")
            annotated_path = None

        # Update snapshot store with analysis
        snapshots_store[snap_id]["analyzed"] = True
        snapshots_store[snap_id]["annotated_image"] = annotated_path
        snapshots_store[snap_id]["detections"] = detections
        snapshots_store[snap_id]["counts"] = counts

        success, enc = cv2.imencode('.jpg', annotated)
        if success:
            b64 = base64.b64encode(enc.tobytes()).decode('utf-8')
        else:
            b64 = ''

        return {
            'success': True,
            'id': snap_id,
            'detections': detections,
            'count': counts,
            'max_confidence': {k: float(round(v,4)) for k,v in max_conf.items()},
            'safety_status': safety_status,
            'image_with_boxes': b64
        }

    except HTTPException:
        raise
    except Exception as e:
        print('Analyze upload failed:', e)
        raise HTTPException(status_code=500, detail=str(e))

# --- END INSERT ---


# ============================================
# 3️⃣ GENERATE PDF REPORT
# ============================================
@router.get("/api/download-report/{snap_id}/")
async def download_report(snap_id: int):
    """
    Generate PDF report with analysis results and annotated image.
    """
    try:
        print(f"📄 Generating report for snap_id={snap_id}")
        
        if snap_id not in snapshots_store:
            print(f"❌ Snapshot not found: snap_id={snap_id}")
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        snap_data = snapshots_store[snap_id]
        
        if not snap_data.get("analyzed"):
            print(f"❌ Snapshot not analyzed yet: snap_id={snap_id}")
            raise HTTPException(status_code=400, detail="Snapshot has not been analyzed yet")
        
        # Create PDF in memory
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Title
        p.setFont("Helvetica-Bold", 20)
        p.drawString(40, height - 40, "AquaSafe AI - Analysis Report")
        
        # Report metadata
        p.setFont("Helvetica", 10)
        p.drawString(40, height - 60, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        p.drawString(40, height - 75, f"Snapshot ID: {snap_id}")
        
        # Analysis results section
        p.setFont("Helvetica-Bold", 14)
        p.drawString(40, height - 110, "Analysis Results")
        
        p.setFont("Helvetica", 11)
        y_pos = height - 135
        
        results_text = [
            f"Primary Species: {snap_data.get('species', 'Unknown')}",
            f"Total Detections: {snap_data.get('count', 0)} organisms",
            f"Overall Confidence: {snap_data.get('confidence', 0):.2%}",
            f"Status: {'✅ SAFE' if snap_data.get('safe', True) else '⚠️ UNSAFE'}",
            f"Description: {snap_data.get('meaning', 'No description')}"
        ]
        
        for line in results_text:
            p.drawString(40, y_pos, line)
            y_pos -= 18
        
        # Per-class statistics table
        per_class = snap_data.get('per_class_stats', [])
        if per_class:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(40, y_pos - 15, "Per-Class Statistics")
            p.setFont("Helvetica", 10)
            y_pos -= 35
            
            # Table header
            p.setFont("Helvetica-Bold", 10)
            p.drawString(40, y_pos, "Class")
            p.drawString(140, y_pos, "Count")
            p.drawString(200, y_pos, "Percentage")
            p.drawString(280, y_pos, "Avg Conf")
            p.drawString(360, y_pos, "Safety")
            y_pos -= 16
            
            p.setFont("Helvetica", 9)
            for row in per_class:
                p.drawString(40, y_pos, str(row.get('class', 'N/A')))
                p.drawString(140, y_pos, str(row.get('count', 0)))
                p.drawString(200, y_pos, f"{row.get('percentage', 0):.1f}%")
                p.drawString(280, y_pos, f"{row.get('avg_confidence', 0):.3f}")
                p.drawString(360, y_pos, row.get('safety', 'N/A'))
                y_pos -= 14
                if y_pos < 80:
                    p.showPage()
                    y_pos = height - 40
        
        # Add annotated image if exists
        annotated_path = snap_data.get("annotated_image")
        if annotated_path and os.path.exists(annotated_path):
            if y_pos < 350:
                p.showPage()
                y_pos = height - 40
            
            p.setFont("Helvetica-Bold", 12)
            p.drawString(40, y_pos, "Annotated Image (with Bounding Boxes)")
            y_pos -= 25
            
            try:
                img_reader = ImageReader(annotated_path)
                p.drawImage(img_reader, 40, y_pos - 300, width=350, height=300, preserveAspectRatio=True)
                print(f"✅ Annotated image embedded in PDF")
            except Exception as e:
                p.drawString(40, y_pos - 40, f"[Image could not be embedded: {str(e)}]")
                print(f"⚠️  Image embed failed: {e}")
        
        # Footer
        p.setFont("Helvetica", 8)
        p.drawString(40, 20, "AquaSafe AI - Water Quality Monitoring System | Powered by YOLO Detection")
        
        p.showPage()
        p.save()
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        print(f"✅ Report generated successfully | Size: {len(pdf_bytes):,} bytes\n")
        
        # Return PDF as download using StreamingResponse
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=aquasafe_report_{snap_id}.pdf"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Report generation failed: {e}\n")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# ============================================
# SERVE STATIC ANNOTATED IMAGES
# ============================================
@router.get("/snapshots/{file_path:path}")
async def serve_snapshot(file_path: str):
    """
    Serve snapshot and annotated images as static files.
    """
    full_path = os.path.join("backend", file_path)
    if os.path.exists(full_path):
        return FileResponse(full_path)
    raise HTTPException(status_code=404, detail="File not found")

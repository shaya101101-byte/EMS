"""
live_detect.py
Live model detection endpoints for snapshot → analyze → report workflow
YOLO detection and classification models with full error handling and logging.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
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

router = APIRouter()

# ============================================
# GLOBALS & DIRECTORIES
# ============================================
snapshots_store = {}
SNAPSHOT_DIR = "backend/snapshots"
ANNOTATED_DIR = "backend/annotated"

# Ensure directories exist
Path(SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)
Path(ANNOTATED_DIR).mkdir(parents=True, exist_ok=True)

# ============================================
# MODEL LOADING WITH LOGGING
# ============================================
detection_model = None
classification_model = None

def load_models():
    """Load both detection and classification YOLO models with detailed logging."""
    global detection_model, classification_model
    
    try:
        from ultralytics import YOLO
        print("\n" + "="*60)
        print("🔄 YOLO MODEL LOADING INITIATED")
        print("="*60)
        
        # ========== DETECTION MODEL (best.pt) ==========
        det_path = os.path.abspath(os.path.join('backend', 'models', 'best.pt'))
        print(f"\n📍 Looking for detection model at: {det_path}")
        
        if os.path.exists(det_path):
            file_size = os.path.getsize(det_path)
            print(f"✅ Detection model file found | Size: {file_size:,} bytes")
            try:
                detection_model = YOLO(det_path)
                print(f"✅ Detection model (best.pt) loaded successfully")
                print(f"   - Model type: {type(detection_model)}")
                print(f"   - Model names: {getattr(detection_model, 'names', 'N/A')}")
            except Exception as e:
                print(f"❌ Failed to load detection model: {e}")
                detection_model = None
        else:
            print(f"❌ Detection model NOT FOUND at: {det_path}")
        
        # ========== CLASSIFICATION MODEL (bestc.pt) ==========
        cls_path = os.path.abspath(os.path.join('backend', 'models', 'bestc.pt'))
        print(f"\n📍 Looking for classification model at: {cls_path}")
        
        if os.path.exists(cls_path):
            file_size = os.path.getsize(cls_path)
            print(f"✅ Classification model file found | Size: {file_size:,} bytes")
            try:
                classification_model = YOLO(cls_path)
                print(f"✅ Classification model (bestc.pt) loaded successfully")
                print(f"   - Model type: {type(classification_model)}")
                print(f"   - Model names: {getattr(classification_model, 'names', 'N/A')}")
            except Exception as e:
                print(f"❌ Failed to load classification model: {e}")
                classification_model = None
        else:
            print(f"⚠️  Classification model NOT FOUND at: {cls_path}")
        
        print("\n" + "="*60)
        print("MODEL LOADING SUMMARY")
        print("="*60)
        print(f"Detection Model (best.pt):       {'✅ LOADED' if detection_model else '❌ FAILED'}")
        print(f"Classification Model (bestc.pt): {'✅ LOADED' if classification_model else '⚠️  NOT AVAILABLE'}")
        print("="*60 + "\n")
        
    except ImportError:
        print("❌ ultralytics package not installed. Install with: pip install ultralytics")
        detection_model = None
        classification_model = None
    except Exception as e:
        print(f"❌ Unexpected error during model loading: {e}")
        detection_model = None
        classification_model = None

# Load models on module import
load_models()


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
# 2️⃣ ANALYZE SNAPSHOT WITH YOLO
# ============================================
@router.get("/api/analyze/{snap_id}/")
async def analyze_snapshot(snap_id: int):
    """
    Run YOLO models on uploaded snapshot.
    Returns: species, count, safety verdict, bounding boxes, confidence, annotated image.
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
        
        # Read image
        img = cv2.imread(img_path)
        if img is None:
            print(f"❌ Invalid image format: {img_path}")
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        print(f"✅ Image loaded: {img.shape}")
        
        # ========== CHECK MODEL AVAILABILITY ==========
        if detection_model is None:
            print(f"❌ Detection model not available")
            return {
                "id": snap_id,
                "species": "No Model",
                "meaning": "YOLO detection model failed to load. Check backend logs.",
                "count": 0,
                "safe": True,
                "confidence": 0.0,
                "annotated_image": f"/snapshots/{snap_id}.jpg",
                "boxes": [],
                "per_class_stats": []
            }
        
        # ========== RUN DETECTION ==========
        try:
            print(f"🤖 Running detection inference...")
            results = detection_model(img_path, conf=0.35, iou=0.45)
            detections = results[0]
            print(f"✅ Detection completed")
            
            boxes = []
            confidences = []
            class_idxs = []

            # Extract detections
            if hasattr(detections, 'boxes') and detections.boxes is not None:
                try:
                    xyxy = detections.boxes.xyxy.cpu().numpy()
                    cls_arr = detections.boxes.cls.cpu().numpy()
                    conf_arr = detections.boxes.conf.cpu().numpy()
                    
                    for b, c, cf in zip(xyxy, cls_arr, conf_arr):
                        boxes.append([int(b[0]), int(b[1]), int(b[2]), int(b[3])])
                        class_idxs.append(int(c))
                        confidences.append(float(cf))
                except Exception as e:
                    print(f"⚠️  Error parsing detection boxes: {e}")

            count = len(boxes)
            print(f"📊 Detections found: {count}")
            
            # Get detection model class names
            det_names = getattr(detection_model, 'names', {}) or {}
            print(f"🏷️  Detection classes available: {det_names}")
            
            # ========== OPTIONAL: RUN CLASSIFICATION ON EACH DETECTION ==========
            boxes_info = []
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box
                det_conf = confidences[i] if i < len(confidences) else 0.0
                det_cls_idx = class_idxs[i] if i < len(class_idxs) else None
                det_cls_name = det_names.get(det_cls_idx, f"class_{det_cls_idx}") if det_cls_idx is not None else "unknown"
                
                final_name = det_cls_name
                final_conf = det_conf
                
                # Try classification model if available
                if classification_model is not None:
                    try:
                        crop = img[y1:y2, x1:x2]
                        if crop is not None and crop.size > 0:
                            pil_crop = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                            cls_res = classification_model(pil_crop)
                            r0 = cls_res[0]
                            probs = getattr(r0, 'probs', None)
                            if probs is not None:
                                try:
                                    top_idx = int(np.argmax(probs.cpu().numpy())) if hasattr(probs, 'cpu') else int(np.argmax(probs))
                                    top_conf = float(np.max(probs.cpu().numpy())) if hasattr(probs, 'cpu') else float(np.max(probs))
                                    cls_names = getattr(classification_model, 'names', {}) or {}
                                    final_name = cls_names.get(top_idx, final_name)
                                    final_conf = top_conf
                                except Exception:
                                    pass
                    except Exception as e:
                        print(f"⚠️  Classification failed for box {i}: {e}")
                
                boxes_info.append({
                    'box': [x1, y1, x2, y2],
                    'confidence': final_conf,
                    'class': final_name
                })
                print(f"   Box {i}: {final_name} (conf={final_conf:.3f})")
            
            # ========== AGGREGATE PER-CLASS STATISTICS ==========
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
                
                # Safety mapping
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
            
            # ========== DETERMINE PRIMARY SPECIES & SAFETY ==========
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
            
            print(f"📋 Results: species={species_name}, count={count}, safe={safe}, confidence={overall_confidence:.3f}")
            
            # ========== DRAW BOUNDING BOXES ==========
            img_annotated = img.copy()
            for b in boxes_info:
                x1, y1, x2, y2 = b['box']
                conf = b.get('confidence', 0.0)
                cls_name = b.get('class', 'unknown')
                
                # Color: green for safe, red for unsafe
                unsafe_classes = ["rotifer"]
                color = (0, 0, 255) if cls_name.lower() in unsafe_classes else (0, 255, 0)
                
                cv2.rectangle(img_annotated, (x1, y1), (x2, y2), color, 2)
                label = f"{cls_name} {conf:.2f}"
                cv2.putText(img_annotated, label, (x1, max(y1 - 6, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # ========== SAVE ANNOTATED IMAGE ==========
            annotated_filename = f"{snap_id}_annotated.jpg"
            annotated_path = os.path.join(ANNOTATED_DIR, annotated_filename)
            cv2.imwrite(annotated_path, img_annotated)
            print(f"💾 Annotated image saved: {annotated_path}")
            
            # ========== UPDATE SNAPSHOT STORE ==========
            snap_data["analyzed"] = True
            snap_data["species"] = species_name
            snap_data["meaning"] = meaning
            snap_data["count"] = count
            snap_data["safe"] = safe
            snap_data["confidence"] = overall_confidence
            snap_data["annotated_image"] = annotated_path
            snap_data["boxes"] = boxes_info
            snap_data["per_class_stats"] = per_class_sorted
            
            print(f"✅ Analysis completed successfully\n")
            
            return {
                "id": snap_id,
                "species": species_name,
                "meaning": meaning,
                "count": count,
                "safe": safe,
                "confidence": overall_confidence,
                "annotated_image": f"/snapshots/annotated/{annotated_filename}",
                "boxes": boxes_info,
                "per_class_stats": per_class_sorted
            }
        
        except Exception as e:
            print(f"❌ Inference error: {e}")
            raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


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
        
        # Per-class statistics
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
        
        # Return PDF as download
        return FileResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            filename=f"aquasafe_report_{snap_id}.pdf"
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

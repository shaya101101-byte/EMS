"""
live_detect.py
Live model detection endpoints for snapshot → analyze → report workflow
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

router = APIRouter()

# Track snapshots in memory (in production, use database)
snapshots_store = {}
SNAPSHOT_DIR = "backend/snapshots"
ANNOTATED_DIR = "backend/annotated"

# Ensure directories exist
Path(SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)
Path(ANNOTATED_DIR).mkdir(parents=True, exist_ok=True)

# Import YOLO model
try:
    from services.yolo_analyzer import analyzer as yolo_analyzer
    yolo_model = None
    if yolo_analyzer and hasattr(yolo_analyzer, 'model'):
        yolo_model = yolo_analyzer.model
except Exception as e:
    print(f"Warning: Could not load YOLO analyzer: {e}")
    yolo_model = None


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
        
        return {
            "id": snap_id,
            "message": "Snapshot uploaded successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ============================================
# 2️⃣ ANALYZE SNAPSHOT WITH YOLO
# ============================================
@router.get("/api/analyze/{snap_id}/")
async def analyze_snapshot(snap_id: int):
    """
    Run YOLO model on uploaded snapshot.
    Returns species, count, safety verdict, and annotated image URL.
    """
    try:
        if snap_id not in snapshots_store:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        snap_data = snapshots_store[snap_id]
        img_path = snap_data["path"]
        
        if not os.path.exists(img_path):
            raise HTTPException(status_code=404, detail="Snapshot file not found")
        
        # Read image
        img = cv2.imread(img_path)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        # ========== RUN YOLO MODEL ==========
        if yolo_model is None:
            # Fallback: if model not loaded, use placeholder results
            species_name = "No Model"
            count = 0
            meaning = "YOLO model not loaded. Please check backend configuration."
            safe = True
            annotated_path = img_path
        else:
            try:
                # Run detection
                results = yolo_model(img_path)
                detections = results[0]
                
                # Extract bounding boxes and class IDs
                boxes = detections.boxes.xyxy.cpu().numpy() if hasattr(detections.boxes, 'xyxy') else []
                class_ids = detections.boxes.cls.cpu().numpy() if hasattr(detections.boxes, 'cls') else []
                confidences = detections.boxes.conf.cpu().numpy() if hasattr(detections.boxes, 'conf') else []
                
                count = len(boxes)
                
                # Determine species and safety
                if count == 0:
                    species_name = "None"
                    meaning = "No microorganisms detected."
                    safe = True
                else:
                    # Use first detected class as primary species
                    class_id = int(class_ids[0])
                    class_names = {0: "diatom", 1: "rotifer", 2: "copepod", 3: "algae"}
                    species_name = class_names.get(class_id, f"Class_{class_id}")
                    
                    # Safety logic
                    unsafe_classes = ["rotifer"]
                    caution_classes = ["algae"]
                    
                    if species_name.lower() in unsafe_classes:
                        meaning = f"⚠️ {species_name} is a high-risk organism. Immediate action recommended."
                        safe = False
                    elif species_name.lower() in caution_classes:
                        meaning = f"⚠️ {species_name} detected. Review recommended."
                        safe = True  # Caution = still safe but needs review
                    else:
                        meaning = f"✅ {species_name} detected. Safe."
                        safe = True
                
                # Draw bounding boxes on image
                img_annotated = img.copy()
                for (x1, y1, x2, y2), conf in zip(boxes, confidences):
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    color = (0, 255, 0) if safe else (0, 0, 255)  # Green if safe, red if unsafe
                    cv2.rectangle(img_annotated, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(img_annotated, f"{species_name} {conf:.2f}", 
                               (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # Save annotated image
                annotated_path = f"{ANNOTATED_DIR}/{snap_id}_annotated.jpg"
                cv2.imwrite(annotated_path, img_annotated)
                
            except Exception as e:
                print(f"YOLO inference error: {e}")
                species_name = "Error"
                count = 0
                meaning = f"Analysis failed: {str(e)}"
                safe = True
                annotated_path = img_path
        
        # Update snapshot store
        snap_data["analyzed"] = True
        snap_data["species"] = species_name
        snap_data["meaning"] = meaning
        snap_data["count"] = count
        snap_data["safe"] = safe
        snap_data["annotated_image"] = annotated_path
        
        return {
            "id": snap_id,
            "species": species_name,
            "meaning": meaning,
            "count": count,
            "safe": safe,
            "annotated_image": f"/snapshots/annotated/{snap_id}_annotated.jpg" if os.path.exists(annotated_path) else f"/snapshots/{snap_id}.jpg"
        }
    
    except HTTPException:
        raise
    except Exception as e:
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
        if snap_id not in snapshots_store:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        snap_data = snapshots_store[snap_id]
        
        if not snap_data.get("analyzed"):
            raise HTTPException(status_code=400, detail="Snapshot has not been analyzed yet")
        
        # Create PDF in memory
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Title
        p.setFont("Helvetica-Bold", 18)
        p.drawString(40, height - 40, "AquaSafe AI - Analysis Report")
        
        # Report metadata
        p.setFont("Helvetica", 10)
        p.drawString(40, height - 60, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        p.drawString(40, height - 75, f"Snapshot ID: {snap_id}")
        
        # Analysis results
        p.setFont("Helvetica-Bold", 12)
        p.drawString(40, height - 110, "Analysis Results")
        
        p.setFont("Helvetica", 10)
        y_pos = height - 130
        results_text = [
            f"Species: {snap_data.get('species', 'Unknown')}",
            f"Count: {snap_data.get('count', 0)} organisms",
            f"Status: {'✅ SAFE' if snap_data.get('safe', True) else '⚠️ UNSAFE'}",
            f"Description: {snap_data.get('meaning', 'No description')}"
        ]
        
        for line in results_text:
            p.drawString(40, y_pos, line)
            y_pos -= 15
        
        # Add annotated image if exists
        annotated_path = snap_data.get("annotated_image")
        if annotated_path and os.path.exists(annotated_path):
            p.drawString(40, y_pos - 20, "Annotated Image:")
            try:
                img_reader = ImageReader(annotated_path)
                p.drawImage(img_reader, 40, y_pos - 320, width=350, height=280)
            except Exception as e:
                p.drawString(40, y_pos - 40, f"[Image could not be embedded: {str(e)}]")
        
        # Footer
        p.setFont("Helvetica", 8)
        p.drawString(40, 20, "AquaSafe AI - Water Quality Monitoring System")
        
        p.showPage()
        p.save()
        
        # Return PDF
        buffer.seek(0)
        return FileResponse(
            io.BytesIO(buffer.getvalue()),
            media_type="application/pdf",
            filename=f"aquasafe_report_{snap_id}.pdf"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# ============================================
# Serve snapshot files statically (optional)
# ============================================
@router.get("/snapshots/{file_path:path}")
async def serve_snapshot(file_path: str):
    """
    Serve snapshot and annotated images as static files.
    """
    full_path = f"backend/{file_path}"
    if os.path.exists(full_path):
        return FileResponse(full_path)
    raise HTTPException(status_code=404, detail="File not found")

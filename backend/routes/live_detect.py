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
from backend.ai_analyzer import get_ai_analyzer

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

        # Persist analysis to history.json via AquaSafeAI helper so the
        # live dashboard analysis appears in the history page.
        try:
            analyzer = get_ai_analyzer()
            percentages = {}
            if count > 0:
                for k, v in counts.items():
                    percentages[k] = round((v / count * 100), 1)

            history_entry = {
                "status": "UNSAFE" if not safe else "SAFE",
                "counts": counts,
                "percentages": percentages,
                "annotated_image": f"snapshots/annotated/{annotated_filename}" if annotated_path else None,
                "pie_chart": "",
                "bar_chart": "",
                "pdf": None,
                "timestamp": datetime.utcnow().isoformat()
            }
            analyzer.save_to_history(history_entry)
            print(f"💾 Analysis saved to history.json for snap_id={snap_id}")
        except Exception as e:
            print(f"⚠️ Failed to save analysis to history: {e}")

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

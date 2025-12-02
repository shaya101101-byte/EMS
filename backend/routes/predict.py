# routes/predict.py
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from services.inference_engine import run_inference_on_bytes
from services.postprocessing import to_base64
from database.db import insert_detection
from config import RESULTS_DIR
import os, io, uuid, shutil
from datetime import datetime

router = APIRouter()

@router.post("/predict")
@router.post("/predict/")
async def predict(image: UploadFile = File(...)):
    try:
        # Read bytes for inference
        contents = await image.read()

        # Ensure upload folder exists and save original using stream copy
        os.makedirs("uploaded_images", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp_filename = f"{timestamp}_{image.filename}"
        uploaded_image_path = os.path.join("uploaded_images", timestamp_filename)

        # Reset file pointer then copy the underlying file stream to disk
        try:
            image.file.seek(0)
        except Exception:
            pass

        with open(uploaded_image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # run inference on the bytes we read
        result = run_inference_on_bytes(contents)

        # save annotated image to disk in static/results
        os.makedirs("static/results", exist_ok=True)
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
        outpath = os.path.join("static/results", filename)
        with open(outpath, "wb") as f:
            f.write(result["annotated_bytes"])

        # store to DB (best-effort) — don't fail the request if DB insert fails
        rec = {
            "timestamp": datetime.utcnow(),
            "image_path": outpath,
            "counts": result["counts"],
            "total": result["total"],
            "dominant": result["dominant"],
            "quality": result["quality"],
            "confidence": result["confidence"]
        }
        try:
            inserted_id = insert_detection(rec)
        except Exception as db_e:
            # log and continue — return response without DB id
            print("DB insert failed:", db_e)
            inserted_id = None

        # Build detections list from boxes
        detections = []
        if "boxes" in result:
            for box in result["boxes"]:
                detections.append({
                    "class": box["class"],
                    "confidence": box["score"],
                    "x1": box["x1"],
                    "y1": box["y1"],
                    "x2": box["x2"],
                    "y2": box["y2"]
                })

        # Return exact JSON structure required by frontend
        return JSONResponse({
            "analysis_id": inserted_id or 0,
            "total_count": result["total"],
            "species": result.get("species", []),
            "summary": result.get("summary", "Analysis complete."),
            "annotated_image_url": f"/static/results/{filename}",
            # Additional fields for backward compatibility
            "detections": detections,
            "counts": result["counts"],
            "timestamp": datetime.utcnow().isoformat(),
            "uploaded_image_url": f"/uploaded_images/{timestamp_filename}",
            "id": inserted_id
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

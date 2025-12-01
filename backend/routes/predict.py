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

        # save annotated image to disk
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
        outpath = os.path.join(RESULTS_DIR, filename)
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

        # produce base64 for frontend
        annotated_b64 = to_base64(result["annotated_bytes"])

        # add URL so frontend can display the original uploaded image
        image_url = f"/uploaded_images/{timestamp_filename}"

        return JSONResponse({
            "id": inserted_id,
            "timestamp": datetime.utcnow().isoformat(),
            "annotated_image": annotated_b64,
            "uploaded_image_url": image_url,
            "original_filename": image.filename,
            "counts": result["counts"],
            "total": result["total"],
            "dominant": result["dominant"],
            "quality": result["quality"],
            "confidence": result["confidence"],
            "image_path": outpath
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

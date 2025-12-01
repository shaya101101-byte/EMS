# routes/history_route.py
from fastapi import APIRouter, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse
from database.db import get_history, insert_detection
import json, os
from config import RESULTS_DIR
from datetime import datetime
import uuid

router = APIRouter()

@router.get("/history")
def history(limit: int = Query(100, ge=1, le=1000)):
    data = get_history(limit=limit)
    return {"history": data}

@router.post("/history/save")
async def save_to_history(image: UploadFile = File(...), analysis_json: str = Form(...)):
    """
    Save analysis result to history
    - image: uploaded image file
    - analysis_json: JSON string of analysis result from /predict
    """
    try:
        # Parse analysis JSON
        analysis = json.loads(analysis_json)
        
        # Save image to disk
        contents = await image.read()
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
        outpath = os.path.join(RESULTS_DIR, filename)
        os.makedirs(RESULTS_DIR, exist_ok=True)
        with open(outpath, "wb") as f:
            f.write(contents)
        
        # Create record to insert
        rec = {
            "timestamp": datetime.utcnow(),
            "image_path": outpath,
            "counts": analysis.get("counts", {}),
            "total": analysis.get("total", 0),
            "dominant": analysis.get("dominant"),
            "quality": analysis.get("quality"),
            "confidence": analysis.get("confidence")
        }
        
        # Insert to DB
        inserted_id = insert_detection(rec)
        
        return JSONResponse({
            "status": "saved",
            "id": inserted_id,
            "message": "Analysis saved to history"
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

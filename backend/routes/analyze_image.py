from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from services.yolo_analyzer import initialize_model, analyze_image_bytes
from database.db import insert_detection
from datetime import datetime
import traceback
import json

router = APIRouter()


@router.post('/analyze-image')
async def analyze_image(file: UploadFile = File(...)):
    """Accepts multipart form file field named 'file' and returns full analysis result.
    Automatically saves analysis result to SQLite database."""
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail='Empty file uploaded')

        # Ensure model initialized; initialize_model raises informative errors if something is wrong
        try:
            initialize_model()
        except Exception as e:
            # bubble up as 500 with description
            raise HTTPException(status_code=500, detail=str(e))

        result = analyze_image_bytes(contents)

        # ✅ AUTOMATICALLY SAVE to database
        try:
            record = {
                "timestamp": datetime.utcnow(),
                "image_path": f"uploaded_images/{file.filename}",
                "counts": {p['class']: p['count'] for p in result.get('per_class', [])},
                "total": result.get('total_detections', 0),
                "dominant": result.get('per_class', [{}])[0].get('class') if result.get('per_class') else None,
                "quality": result.get('overall_verdict', {}).get('verdict', 'Unknown'),
                "confidence": result.get('per_class', [{}])[0].get('avg_confidence', 0.0) if result.get('per_class') else 0.0
            }
            insert_detection(record)
            print(f"✅ Analysis saved to database for {file.filename}")
        except Exception as e:
            print(f"⚠️ Warning: Could not save to database: {e}")
            # Don't fail the request if DB save fails; still return result
            pass

        # ✅ SAVE ANALYSIS DATA FOR FRONTEND (NEW)
        try:
            organism_counts = {p['class']: p['count'] for p in result.get('per_class', [])}
            verdict_summary = result.get('overall_verdict', {})
            crop_image_paths = result.get('crops', [])

            result_data = {
                "organism_counts": organism_counts,
                "verdict": verdict_summary,
                "crops": crop_image_paths
            }

            with open("latest_analysis.json", "w") as f:
                json.dump(result_data, f)
            print(f"✅ Latest analysis saved to latest_analysis.json")
        except Exception as e:
            print(f"⚠️ Warning: Could not save latest analysis: {e}")
            pass

        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f'Analysis failed: {e}\n{tb}')

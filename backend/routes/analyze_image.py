from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from services.yolo_analyzer import initialize_model, analyze_image_bytes
import traceback

router = APIRouter()


@router.post('/analyze-image')
async def analyze_image(file: UploadFile = File(...)):
    """Accepts multipart form file field named 'file' and returns full analysis result."""
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

        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f'Analysis failed: {e}\n{tb}')

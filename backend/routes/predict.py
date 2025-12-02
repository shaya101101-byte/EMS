# routes/predict.py
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from services.inference_engine import run_inference_on_bytes
from services.postprocessing import to_base64
from database.db import insert_detection
from config import RESULTS_DIR
import os, io, uuid, shutil
from datetime import datetime
from werkzeug.utils import secure_filename

router = APIRouter()

# Constants for validation
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _validate_image_file(file: UploadFile, contents: bytes) -> tuple[bool, str]:
    """
    Validate uploaded file for type, size, and name.
    Returns: (is_valid, error_message)
    """
    # Check MIME type
    content_type = file.content_type or ""
    if content_type.lower() not in ALLOWED_MIME_TYPES:
        return False, "Invalid file. Please upload a JPG or PNG image under 10 MB."
    
    # Check file size
    file_size = len(contents)
    if file_size == 0:
        return False, "Invalid file. Please upload a JPG or PNG image under 10 MB."
    
    if file_size > MAX_FILE_SIZE_BYTES:
        return False, "Invalid file. Please upload a JPG or PNG image under 10 MB."
    
    # Check file extension
    filename = file.filename or ""
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, "Invalid file. Please upload a JPG or PNG image under 10 MB."
    
    return True, ""


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize filename and ensure proper extension.
    Prevents path injection and ensures valid image extension.
    """
    if not filename:
        filename = f"image_{uuid.uuid4().hex[:8]}.jpg"
    
    # Use werkzeug's secure_filename to prevent path injection
    safe_name = secure_filename(filename)
    
    if not safe_name:
        safe_name = f"image_{uuid.uuid4().hex[:8]}.jpg"
    
    # Ensure proper extension
    name_without_ext = os.path.splitext(safe_name)[0]
    ext = os.path.splitext(safe_name)[1].lower()
    
    # Add .jpg if no extension or wrong extension
    if not ext or ext not in ALLOWED_EXTENSIONS:
        ext = ".jpg"
    
    return f"{name_without_ext}{ext}"


@router.post("/predict")
@router.post("/predict/")
async def predict(image: UploadFile = File(...)):
    """
    Predict/analyze image with full validation and error handling.
    
    Accepts: JPG, JPEG, PNG images under 10 MB
    Returns: JSON with detections, annotated image URL, and metadata
    """
    try:
        # Step 1: Read and validate file
        contents = await image.read()
        is_valid, error_msg = _validate_image_file(image, contents)
        
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"error": error_msg}
            )
        
        # Step 2: Save uploaded image to /uploaded_images
        try:
            os.makedirs("uploaded_images", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = _sanitize_filename(image.filename or "image.jpg")
            timestamp_filename = f"{timestamp}_{safe_filename}"
            uploaded_image_path = os.path.join("uploaded_images", timestamp_filename)
            
            # Write original image to disk
            with open(uploaded_image_path, "wb") as buffer:
                buffer.write(contents)
        except Exception as save_e:
            print(f"Error saving uploaded image: {save_e}")
            # Continue anyway — inference can still work with bytes in memory
            timestamp_filename = "unknown.jpg"
        
        # Step 3: Run YOLO inference with error handling
        try:
            result = run_inference_on_bytes(contents)
        except Exception as inference_e:
            print(f"Model inference failed: {inference_e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Model failed to process image. Try a clearer image."}
            )
        
        # Step 4: Validate inference result
        if not result or not isinstance(result, dict):
            return JSONResponse(
                status_code=500,
                content={"error": "Model failed to process image. Try a clearer image."}
            )
        
        # Step 5: Save annotated output image to /static/results
        annotated_filename = "unknown.jpg"
        annotated_image_url = "/static/results/unknown.jpg"
        try:
            os.makedirs("static/results", exist_ok=True)
            annotated_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
            outpath = os.path.join("static/results", annotated_filename)
            
            if "annotated_bytes" in result and result["annotated_bytes"]:
                with open(outpath, "wb") as f:
                    f.write(result["annotated_bytes"])
                annotated_image_url = f"/static/results/{annotated_filename}"
        except Exception as annotate_e:
            print(f"Error saving annotated image: {annotate_e}")
            # Continue — we have detection data even if image save fails
        
        # Step 6: Build clean JSON response with detections
        detections = []
        if "boxes" in result and result["boxes"]:
            for box in result["boxes"]:
                detections.append({
                    "class": box.get("class", "unknown"),
                    "confidence": float(box.get("score", 0.0)),
                    "x1": int(box.get("x1", 0)),
                    "y1": int(box.get("y1", 0)),
                    "x2": int(box.get("x2", 0)),
                    "y2": int(box.get("y2", 0))
                })
        
        # Step 7: Store to database (best-effort — don't fail request if DB fails)
        inserted_id = None
        try:
            rec = {
                "timestamp": datetime.utcnow(),
                "image_path": f"static/results/{annotated_filename}",
                "counts": result.get("counts", {}),
                "total": result.get("total", 0),
                "dominant": result.get("dominant", ""),
                "quality": result.get("quality", "Unknown"),
                "confidence": result.get("confidence", 0.0)
            }
            inserted_id = insert_detection(rec)
        except Exception as db_e:
            print(f"DB insert failed: {db_e}")
            # Continue — don't fail request if DB is unavailable
        
        # Step 8: Return complete response
        return JSONResponse(
            status_code=200,
            content={
                "analysis_id": inserted_id or 0,
                "total_count": result.get("total", 0),
                "species": result.get("species", []),
                "summary": result.get("summary", "Analysis complete."),
                "annotated_image_url": annotated_image_url,
                # Additional fields for backward compatibility
                "detections": detections,
                "counts": result.get("counts", {}),
                "timestamp": datetime.utcnow().isoformat(),
                "uploaded_image_url": f"/uploaded_images/{timestamp_filename}",
                "id": inserted_id
            }
        )
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error in /predict: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Model failed to process image. Try a clearer image."}
        )

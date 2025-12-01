# main.py
import uvicorn
import os
import shutil
from datetime import datetime
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes.predict import router as predict_router
from routes.history_route import router as history_router
from routes.stats_route import router as stats_router
from routes.status_route import router as status_router
from routes.stats_api import router as stats_api_router
from services.model_loader import initialize_model, MODEL
from fastapi.middleware.cors import CORSMiddleware
from config import STATIC_DIR
# ---- AquaSafe AI (Added Feature) ----
from fastapi import UploadFile, File
from ai_analyzer import get_ai_analyzer
import numpy as np
import cv2

app = FastAPI(title="Microscopy AI Inference API")

# CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# startup: initialize model
@app.on_event("startup")
def startup_event():
    initialize_model()
    # ensure static dir exists
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs("uploaded_images", exist_ok=True)
    # ---- AquaSafe AI (Added Feature) ----
    # ensure outputs dir exists for AI-generated files
    os.makedirs("outputs", exist_ok=True)

# Mount static files directories
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs("uploaded_images", exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images")
# ---- AquaSafe AI (Added Feature) ----
# Mount outputs so generated charts, images and PDFs are available at /outputs
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# include routers
app.include_router(predict_router, prefix="")
app.include_router(history_router, prefix="")
app.include_router(stats_router, prefix="")
app.include_router(status_router, prefix="")
app.include_router(stats_api_router, prefix="")

# ---- AquaSafe AI Endpoint (Added Feature) ----
@app.post("/ai/analyze")
async def ai_analyze(image: UploadFile = File(...)):
    """
    AI-powered water quality analysis using YOLO detection.
    Accepts an image and returns species counts, safety status, and generated reports.
    """
    try:
        # Read image from upload
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_array is None:
            return {"error": "Invalid image format", "status": "ERROR"}
        
        # Run analysis
        analyzer = get_ai_analyzer()
        result = analyzer.analyze_image(img_array)
        
        return result
    except Exception as e:
        return {"error": str(e), "status": "ERROR"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

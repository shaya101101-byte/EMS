# main.py - Clean, simplified for PlanktoVision project
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from services.yolo_pipeline import YoloPipeline

app = FastAPI(title="PlanktoVision AI - Water Quality Analysis")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event - initialize models
@app.on_event("startup")
def startup_event():
    try:
        app.state.yolo = YoloPipeline()
        print("✅ YoloPipeline initialized")
    except Exception as e:
        app.state.yolo = None
        print(f"⚠️ YoloPipeline init failed: {e}")
    
    # Ensure directories exist
    for directory in ["static", "static/results", "uploaded_images", "backend/snapshots", "backend/annotated"]:
        os.makedirs(directory, exist_ok=True)

# Mount static files
os.makedirs("static/results", exist_ok=True)
os.makedirs("uploaded_images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images")

# Include only necessary routers
from routes.live_detect import router as live_detect_router
from routes.history_route import router as history_router

app.include_router(live_detect_router, prefix="")
app.include_router(history_router, prefix="")

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "yolo_available": app.state.yolo is not None}

@app.get("/")
async def root():
    return {"message": "PlanktoVision API running", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

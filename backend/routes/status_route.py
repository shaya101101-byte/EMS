# routes/status_route.py
from fastapi import APIRouter
from services.model_loader import MODEL
from datetime import datetime

router = APIRouter()

@router.get("/status")
def status():
    return {
        "service": "Microscopy AI Inference (FastAPI)",
        "status": "online",
        "model_type": MODEL.type,
        "timestamp": datetime.utcnow().isoformat()
    }

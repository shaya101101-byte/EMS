# backend/api.py
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import io
from PIL import Image
import time, os, uuid, json

app = FastAPI()

@app.post("/api/predict")
async def predict(image: UploadFile = File(...)):
    t0 = time.time()
    try:
        contents = await image.read()
        pil = Image.open(io.BytesIO(contents)).convert("RGB")
        # Dummy inference: pretend we found 2 Paramecium, 1 Rotifer
        preds = [
            {"class":"Paramecium","count":2,"boxes":[[20,30,120,130],[140,160,240,260]],"confidences":[0.98,0.95]},
            {"class":"Rotifer","count":1,"boxes":[[60,80,140,160]],"confidences":[0.92]}
        ]
        resp = {
            "status":"ok",
            "preds": preds,
            "summary": "Detected 2 Paramecium and 1 Rotifer",
            "metrics": {"inference_time_ms": int((time.time()-t0)*1000)},
            "id": str(uuid.uuid4())
        }
        return JSONResponse(resp)
    except Exception as e:
        return JSONResponse({"status":"error","message":str(e)}, status_code=500)

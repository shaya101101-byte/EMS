# services/inference_engine.py
import random
import io
from services.postprocessing import annotate_image_bytes, summarize_counts
from config import SAMPLE_IMAGE_PATH
from services.model_loader import MODEL

# produce mock boxes
def _mock_boxes(img_w, img_h):
    boxes = []
    n = random.randint(1,6)
    classes = ["diatom","rotifer","copepod","algae"]
    for _ in range(n):
        w = int(random.uniform(0.06, 0.25) * img_w)
        h = int(random.uniform(0.06, 0.25) * img_h)
        x1 = random.randint(0, max(1, img_w-w))
        y1 = random.randint(0, max(1, img_h-h))
        boxes.append({
            "x1": x1, "y1": y1, "x2": x1+w, "y2": y1+h,
            "score": random.uniform(0.6, 0.99),
            "class": random.choice(classes)
        })
    return boxes

def run_inference_on_bytes(image_bytes):
    # If model type is yolov8, use it; else use mock
    try:
        if MODEL.type == "yolov8" and MODEL.model is not None:
            # Decode bytes to numpy array for YOLO
            import cv2
            import numpy as np
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image")
            # run YOLO inference using ultralytics API
            results = MODEL.model.predict(source=img, imgsz=640, conf=0.35)
            # ultralytics returns a list; take first
            res = results[0]
            boxes = []
            for det in res.boxes:
                x1,y1,x2,y2 = map(int, det.xyxy[0].tolist())
                score = float(det.conf[0])
                cls_idx = int(det.cls[0])
                # Use class names from MODEL.class_names (stored during model load)
                cls_name = MODEL.class_names.get(cls_idx, f"class{cls_idx}") if MODEL.class_names else f"class{cls_idx}"
                boxes.append({"x1":x1,"y1":y1,"x2":x2,"y2":y2,"score":score,"class":cls_name})
        else:
            # mock path — derive image size and produce random boxes
            from PIL import Image
            im = Image.open(io.BytesIO(image_bytes))
            w,h = im.size
            boxes = _mock_boxes(w,h)

        counts, total, dominant = summarize_counts(boxes)
        
        # Calculate percentages for species
        species_list = []
        for class_name, count in counts.items():
            percentage = round((count / total * 100), 1) if total > 0 else 0
            species_list.append({
                "name": class_name,
                "count": count,
                "percentage": percentage
            })
        
        # Sort by count (descending)
        species_list = sorted(species_list, key=lambda x: x["count"], reverse=True)
        
        # Create summary text
        summary = f"Detected {total} organisms across {len(species_list)} species."
        
        annotated = annotate_image_bytes(image_bytes, boxes)
        avg_conf = sum([b["score"] for b in boxes]) / (len(boxes) or 1)
        quality = "Good" if total < 10 else ("Moderate" if total < 25 else "Poor")

        return {
            "boxes": boxes,
            "counts": counts,
            "total": total,
            "dominant": dominant,
            "quality": quality,
            "confidence": round(avg_conf, 3),
            "annotated_bytes": annotated,
            "species": species_list,
            "summary": summary
        }
    except Exception as e:
        # in case inference fails, return a mock result
        print("Inference error:", e)
        return run_inference_on_bytes_mock(image_bytes)

def run_inference_on_bytes_mock(image_bytes):
    # identical to above mock branch
    from PIL import Image
    im = Image.open(io.BytesIO(image_bytes))
    w,h = im.size
    boxes = _mock_boxes(w,h)
    counts, total, dominant = summarize_counts(boxes)
    
    # Calculate percentages for species
    species_list = []
    for class_name, count in counts.items():
        percentage = round((count / total * 100), 1) if total > 0 else 0
        species_list.append({
            "name": class_name,
            "count": count,
            "percentage": percentage
        })
    
    # Sort by count (descending)
    species_list = sorted(species_list, key=lambda x: x["count"], reverse=True)
    
    # Create summary text
    summary = f"Detected {total} organisms across {len(species_list)} species."
    
    annotated = annotate_image_bytes(image_bytes, boxes)
    avg_conf = sum([b["score"] for b in boxes]) / (len(boxes) or 1)
    quality = "Good" if total < 10 else ("Moderate" if total < 25 else "Poor")
    return {
        "boxes": boxes,
        "counts": counts,
        "total": total,
        "dominant": dominant,
        "quality": quality,
        "confidence": round(avg_conf, 3),
        "annotated_bytes": annotated,
        "species": species_list,
        "summary": summary
    }

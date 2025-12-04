from ultralytics import YOLO
from PIL import Image
import io

# Load both models safely
detect_model = YOLO("models/best.pt")      # OLD model → detection
classify_model = YOLO("models/bestc.pt")   # NEW model → classification

def analyze_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))

    # Step 1 — Detection with old model
    det_results = detect_model.predict(img)

    detections = []
    class_counts = {}

    for box in det_results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        crop = img.crop((x1, y1, x2, y2))

        # Step 2 — Classification with new model
        cls_res = classify_model.predict(crop)
        cls_id = int(cls_res[0].boxes[0].cls)
        cls_name = cls_res[0].names[cls_id]
        conf = float(cls_res[0].boxes[0].conf)

        detections.append({
            "class": cls_name,
            "confidence": round(conf, 4),
            "bbox": [x1, y1, x2, y2]
        })

        # Count
        if cls_name not in class_counts:
            class_counts[cls_name] = 0
        class_counts[cls_name] += 1

    total = sum(class_counts.values())

    percentages = {
        cls: round((count / total) * 100, 2)
        for cls, count in class_counts.items()
    }

    return {
        "total_organisms": total,
        "detections": detections,
        "counts": class_counts,
        "percentages": percentages
    }

"""
yolo_pipeline.py
Singleton-style YOLO pipeline class used by FastAPI app.

Responsibilities:
- Load detection (`best.pt`) and classification (`bestc.pt`) models once
- Run detection on an image (path or numpy array)
- Crop detections and classify each crop
- Return structured results plus an annotated image (numpy BGR)

"""
from typing import List, Dict, Optional, Tuple
import os
import cv2
import numpy as np
from PIL import Image


class YoloPipeline:
    def __init__(self, det_path: str = None,
                 cls_path: str = None,
                 device: Optional[str] = None, use_absolute_paths: bool = True):
        """Load detection and classification models.

        The constructor performs model loading once. It raises exceptions
        if ultralytics is not installed or model files are missing.
        """
        try:
            from ultralytics import YOLO
        except Exception as e:
            raise ImportError("ultralytics is required for YoloPipeline: pip install ultralytics") from e

        # Resolve default model paths relative to this services file to avoid CWD issues
        services_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(services_dir)
        self.det_path = det_path or os.path.join(backend_dir, 'models', 'best.pt')
        self.cls_path = cls_path or os.path.join(backend_dir, 'models', 'bestc.pt')
        self.device = device

        # Convert to absolute paths (defensive)
        if use_absolute_paths and not os.path.isabs(self.det_path):
            self.det_path = os.path.join(backend_dir, self.det_path)
        if use_absolute_paths and not os.path.isabs(self.cls_path):
            self.cls_path = os.path.join(backend_dir, self.cls_path)

        if not os.path.exists(self.det_path):
            raise FileNotFoundError(f"Detection model not found: {self.det_path}")
        if not os.path.exists(self.cls_path):
            raise FileNotFoundError(f"Classification model not found: {self.cls_path}")

        # Load models
        self.detection_model = YOLO(self.det_path)
        self.classification_model = YOLO(self.cls_path)

        # Names mapping (if available)
        self.det_names = getattr(self.detection_model, 'names', {}) or {}
        self.cls_names = getattr(self.classification_model, 'names', {}) or {}

    def _read_image(self, image_path: Optional[str], image_array: Optional[np.ndarray]) -> np.ndarray:
        if image_array is not None:
            return image_array
        if image_path is None:
            raise ValueError("Either image_path or image_array must be provided")
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        return img

    def run(self, image_path: Optional[str] = None, image_array: Optional[np.ndarray] = None,
            conf: float = 0.35, iou: float = 0.45) -> Dict:
        """Run detection then classification on crops.

        Returns a dict:
        {
           'detections': [ {'bbox':[x1,y1,x2,y2], 'class_name': str, 'confidence': float}, ...],
           'annotated': np.ndarray (BGR image)
        }
        """
        img = self._read_image(image_path, image_array)
        # Run detection (ultralytics can accept path or numpy array)
        results = self.detection_model(image_path if image_path is not None else img, conf=conf, iou=iou)
        det0 = results[0]

        detections: List[Dict] = []

        # Prepare annotated image copy
        annotated = img.copy()

        # Extract boxes safely
        boxes = []
        try:
            if hasattr(det0, 'boxes') and det0.boxes is not None:
                xyxy = det0.boxes.xyxy.cpu().numpy()
                cls_arr = det0.boxes.cls.cpu().numpy()
                conf_arr = det0.boxes.conf.cpu().numpy()
                for b, c, cf in zip(xyxy, cls_arr, conf_arr):
                    x1, y1, x2, y2 = [int(v) for v in b]
                    boxes.append((x1, y1, x2, y2, int(c), float(cf)))
        except Exception:
            # Best-effort: try attributes on raw results
            try:
                raw = getattr(det0, 'boxes', None)
                if raw is not None:
                    for r in raw:
                        b = r.xyxy
                        boxes.append((int(b[0]), int(b[1]), int(b[2]), int(b[3]), 0, float(r.conf)))
            except Exception:
                pass

        # For each detection, crop and classify
        for (x1, y1, x2, y2, cls_idx, det_conf) in boxes:
            # Clamp coordinates
            h, w = img.shape[:2]
            x1c = max(0, min(w - 1, x1))
            y1c = max(0, min(h - 1, y1))
            x2c = max(0, min(w - 1, x2))
            y2c = max(0, min(h - 1, y2))

            if x2c <= x1c or y2c <= y1c:
                continue

            crop = img[y1c:y2c, x1c:x2c]

            # Convert to PIL RGB as ultralytics classifiers often accept PIL too
            try:
                pil_crop = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            except Exception:
                pil_crop = None

            final_name = self.det_names.get(cls_idx, f'class_{cls_idx}')
            final_conf = float(det_conf)

            # Run classification model if crop present
            if pil_crop is not None:
                try:
                    cls_res = self.classification_model(pil_crop)
                    r0 = cls_res[0]
                    probs = getattr(r0, 'probs', None)
                    if probs is not None:
                        # Convert to numpy
                        try:
                            arr = probs.cpu().numpy()
                        except Exception:
                            arr = np.array(probs)
                        top_idx = int(np.argmax(arr))
                        top_conf = float(np.max(arr))
                        final_name = self.cls_names.get(top_idx, final_name)
                        final_conf = float(top_conf)
                    else:
                        # Try .probs not available: fallback to .boxes or .scores
                        # Some classifier variants set .boxes or .scores; attempt to read first prediction
                        try:
                            pred = getattr(r0, 'boxes', None)
                            if pred is not None and len(pred) > 0:
                                p = pred[0]
                                final_conf = float(getattr(p, 'conf', final_conf))
                        except Exception:
                            pass
                except Exception:
                    # If classification fails, keep detection class/conf
                    pass

            # Draw box and label on annotated image
            color = (0, 255, 0)
            cv2.rectangle(annotated, (x1c, y1c), (x2c, y2c), color, 2)
            label = f"{final_name} {final_conf:.2f}"
            cv2.putText(annotated, label, (x1c, max(y1c - 6, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            detections.append({
                'bbox': [x1c, y1c, x2c, y2c],
                'class_name': final_name,
                'confidence': round(float(final_conf), 4)
            })

        return {
            'detections': detections,
            'annotated': annotated
        }


# End of file

# backend/debug_yolo_test.py
import os
import cv2
import numpy as np
from ultralytics import YOLO

# -------------------------------
# Correct model & test image paths
# -------------------------------
DET_MODEL = "models/best.pt"        # detection model
CLS_MODEL = "models/bestc.pt"       # classification model
TEST_IMAGE = "test_images/debug_test.jpg"   # sample test image

# Folder for saving debug classifier crops
os.makedirs("backend/debug_crops", exist_ok=True)


# -------------------------------
# Load YOLO models
# -------------------------------
def load_models():
    print("Loading detection model:", DET_MODEL)
    det = YOLO(DET_MODEL)

    print("Loading classification model:", CLS_MODEL)
    cls = YOLO(CLS_MODEL)

    return det, cls


# -------------------------------
# Convert xyxy float → int
# -------------------------------
def xyxy_to_int(box):
    x1, y1, x2, y2 = box
    return [
        int(max(0, x1)),
        int(max(0, y1)),
        int(max(0, x2)),
        int(max(0, y2)),
    ]


# -------------------------------
# Main Debug Test Function
# -------------------------------
def run_test(image_path):
    print("Testing image:", image_path)

    img = cv2.imread(image_path)
    if img is None:
        print("ERROR: Test image not found:", image_path)
        return

    h, w = img.shape[:2]
    print("Image shape (h, w):", (h, w))

    # Load models
    det_model, cls_model = load_models()

    # Run detection
    det_results = det_model(image_path)
    if len(det_results) == 0:
        print("No detection results returned.")
        return

    res = det_results[0]
    boxes = getattr(res, "boxes", None)

    if boxes is None:
        print("No bounding boxes detected.")
        print("Raw result:", res)
        return

    xyxy_all = boxes.xyxy.cpu().numpy()
    confs = boxes.conf.cpu().numpy()
    det_classes = boxes.cls.cpu().numpy()

    print("Found", len(xyxy_all), "detections")

    # -------------------------------
    # Crop each detection & classify
    # -------------------------------
    for i, (xyxy, conf, dcls) in enumerate(zip(xyxy_all, confs, det_classes)):
        x1, y1, x2, y2 = xyxy_to_int(xyxy)
        print(f"Box {i}: ({x1},{y1},{x2},{y2})  conf={conf:.3f}  det_clsIndex={int(dcls)}")

        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            print("  WARNING: Crop was empty. Using whole image.")
            crop = img.copy()

        crop_path = f"backend/debug_crops/crop_{i}.jpg"
        cv2.imwrite(crop_path, crop)
        print("  Saved crop:", crop_path)

        # Run classifier on the crop
        cls_res = cls_model(crop)[0]
        cls_boxes = getattr(cls_res, "boxes", None)

        if cls_boxes is not None and len(cls_boxes) > 0:
            cls_xyxy = cls_boxes.xyxy.cpu().numpy()
            cls_conf = cls_boxes.conf.cpu().numpy()
            cls_ids = cls_boxes.cls.cpu().numpy()

            print("  CLASSIFIER produced", len(cls_xyxy), "results:")
            for j, (cxy, cconf, cid) in enumerate(zip(cls_xyxy, cls_conf, cls_ids)):
                print(f"    [{j}] Box={cxy}  conf={cconf:.3f}  classIndex={int(cid)}")

        else:
            print("  CLASSIFIER raw output:", cls_res)

    print("\nDetection model classes:", det_model.names)
    print("Classification model classes:", cls_model.names)
    print("\nDebug test finished.")


# -------------------------------
# Script entry point
# -------------------------------
if __name__ == "__main__":
    print("Starting YOLO debug test...\n")
    run_test(TEST_IMAGE)
    print("\nDone.")

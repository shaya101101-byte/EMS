# services/model_loader.py
import os
from config import MODEL_PATH, TFLITE_PATH, USE_TFLITE

class ModelWrapper:
    def __init__(self):
        self.model = None
        self.type = "mock"

    def load(self):
        # Try to load a YOLO model (ultralytics) if available
        try:
            # If ultralytics is installed and a model file exists
            if os.path.exists(MODEL_PATH):
                from ultralytics import YOLO
                self.model = YOLO(MODEL_PATH)
                self.type = "yolov8"
                print("Loaded YOLOv8 model:", MODEL_PATH)
                return
        except Exception as e:
            print("YOLO load failed:", e)

        # Try to load TFLite if configured
        if USE_TFLITE and os.path.exists(TFLITE_PATH):
            try:
                import tflite_runtime.interpreter as tflite
                interp = tflite.Interpreter(model_path=TFLITE_PATH)
                interp.allocate_tensors()
                self.model = interp
                self.type = "tflite"
                print("Loaded TFLite model:", TFLITE_PATH)
                return
            except Exception as e:
                print("TFLite load failed:", e)

        # Fallback to mock
        self.model = None
        self.type = "mock"
        print("Using MOCK model (no real weights found).")

MODEL = ModelWrapper()

def initialize_model():
    MODEL.load()
    return MODEL

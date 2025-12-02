# services/model_loader.py
import os
from config import MODEL_PATH, TFLITE_PATH, USE_TFLITE

class ModelWrapper:
    def __init__(self):
        self.model = None
        self.type = "mock"
        self.class_names = {}  # Store YOLO class names

    def load(self):
        # Try to load a YOLO model (ultralytics) if available
        try:
            # If ultralytics is installed and a model file exists
            if os.path.exists(MODEL_PATH):
                from ultralytics import YOLO
                self.model = YOLO(MODEL_PATH)
                self.type = "yolov8"
                # Store class names from the model
                if hasattr(self.model, 'names'):
                    names = self.model.names
                    # Ensure class_names is a dict mapping index -> name
                    if isinstance(names, dict):
                        self.class_names = names
                    else:
                        try:
                            # names may be a list-like
                            self.class_names = {i: n for i, n in enumerate(names)}
                        except Exception:
                            self.class_names = {}
                    print("YOLO class names:", self.class_names)
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

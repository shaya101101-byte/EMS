# services/model_loader.py
import os
import yaml
from config import MODEL_PATH, TFLITE_PATH, USE_TFLITE

class ModelWrapper:
    def __init__(self):
        self.model = None
        self.type = "mock"
        self.class_names = {}  # Store YOLO class names

    def _load_class_names_from_yaml(self):
        """Load class names from data.yaml in the models directory."""
        models_dir = os.path.dirname(MODEL_PATH)
        yaml_path = os.path.join(models_dir, "data.yaml")
        
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(
                f"data.yaml not found at {os.path.abspath(yaml_path)}. "
                f"Please ensure the YAML configuration file exists in the models directory."
            )
        
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if data is None or 'names' not in data:
                raise ValueError(
                    f"data.yaml at {os.path.abspath(yaml_path)} does not contain 'names' key. "
                    f"Ensure your YAML has a 'names' field with class names."
                )
            
            names = data['names']
            # Convert list to dict mapping index -> name
            if isinstance(names, list):
                self.class_names = {i: n for i, n in enumerate(names)}
            elif isinstance(names, dict):
                self.class_names = names
            else:
                raise ValueError(
                    f"'names' in data.yaml must be a list or dict, got {type(names).__name__}"
                )
            
            print("Loaded class names from data.yaml:", self.class_names)
        except yaml.YAMLError as e:
            raise ValueError(
                f"Error parsing data.yaml at {os.path.abspath(yaml_path)}: {e}"
            )

    def load(self):
        # Try to load a YOLO model (ultralytics) if available
        try:
            # If ultralytics is installed and a model file exists
            if os.path.exists(MODEL_PATH):
                from ultralytics import YOLO
                self.model = YOLO(MODEL_PATH)
                self.type = "yolov8"
                
                # Load class names from data.yaml
                try:
                    self._load_class_names_from_yaml()
                except (FileNotFoundError, ValueError) as e:
                    print(f"Warning: Could not load class names from data.yaml: {e}")
                    # Fallback to model's built-in names if available
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
                        print("Loaded class names from model:", self.class_names)
                
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

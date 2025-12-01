# config.py
import os

# Where to save annotated images (ensure folder exists)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
RESULTS_DIR = os.path.join(STATIC_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Demo sample image path from conversation (tool will convert to URL if needed)
SAMPLE_IMAGE_PATH = "/mnt/data/1a536a22-131f-497e-81ad-de0db239a6ec.png"

# Model settings
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")  # if you put a YOLO weight here
USE_TFLITE = False  # toggle if you use tflite path
TFLITE_PATH = os.path.join(BASE_DIR, "models", "model_int8.tflite")

#!/usr/bin/env python3
"""Quick test of /analyze-image endpoint"""
import requests
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

# Find a test image in uploaded_images or use a sample
test_image_path = None
uploaded_dir = Path("C:\\EMS_short\\uploaded_images")
if uploaded_dir.exists():
    images = list(uploaded_dir.glob("*.jpg")) + list(uploaded_dir.glob("*.png"))
    if images:
        test_image_path = str(images[0])
        print(f"Found test image: {test_image_path}")

if not test_image_path:
    print("No test image found. Upload an image first or provide a path.")
    exit(1)

# Upload to /analyze-image
print(f"\nTesting POST /analyze-image with {test_image_path}...")
with open(test_image_path, "rb") as f:
    files = {"file": f}
    response = requests.post(f"{BASE_URL}/analyze-image", files=files)

print(f"Status: {response.status_code}")
if response.ok:
    data = response.json()
    print(f"Response keys: {list(data.keys())}")
    print(f"Total detections: {data.get('total_detections')}")
    print(f"Per-class: {data.get('per_class')}")
    print(f"Overall verdict: {data.get('overall_verdict')}")
    print("\n✅ /analyze-image endpoint is WORKING!")
else:
    print(f"Error: {response.text}")

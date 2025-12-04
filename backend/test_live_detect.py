# Quick test to verify live detection endpoints
# Run: python test_live_detect.py

import requests
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("🧪 Testing Live Model Detection Endpoints")
print("=" * 60)

# Create a simple test image (just a blank image)
test_image_path = "test_snapshot.jpg"

# Check if we have a test image
if not Path(test_image_path).exists():
    # Create a dummy image
    import cv2
    import numpy as np
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (200, 200), (0, 255, 0), -1)
    cv2.imwrite(test_image_path, img)
    print(f"✅ Created test image: {test_image_path}")

# Test 1: Upload Snapshot
print("\n[1️⃣] Testing /api/upload-snapshot/")
try:
    with open(test_image_path, "rb") as f:
        files = {"image": f}
        response = requests.post(f"{BASE_URL}/api/upload-snapshot/", files=files)
    
    if response.status_code == 200:
        data = response.json()
        snap_id = data.get("id")
        print(f"✅ Upload successful! Snapshot ID: {snap_id}")
    else:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Test 2: Analyze Snapshot
print(f"\n[2️⃣] Testing /api/analyze/{snap_id}/")
try:
    response = requests.get(f"{BASE_URL}/api/analyze/{snap_id}/")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Analysis successful!")
        print(f"   - Species: {data.get('species')}")
        print(f"   - Count: {data.get('count')}")
        print(f"   - Safe: {data.get('safe')}")
        print(f"   - Meaning: {data.get('meaning')}")
    else:
        print(f"❌ Analysis failed: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Test 3: Download Report
print(f"\n[3️⃣] Testing /api/download-report/{snap_id}/")
try:
    response = requests.get(f"{BASE_URL}/api/download-report/{snap_id}/", stream=True)
    
    if response.status_code == 200:
        # Save PDF
        pdf_path = f"report_{snap_id}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(response.content)
        print(f"✅ PDF report generated! Saved to: {pdf_path}")
    else:
        print(f"❌ Report generation failed: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ All live detection endpoint tests passed!")
print("=" * 60)

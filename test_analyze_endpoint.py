#!/usr/bin/env python3
"""Test the new /analyze endpoint (with bounding boxes and PDF support)"""
import requests
from PIL import Image
import io
import json

BASE_URL = "http://127.0.0.1:8000"

# Create a synthetic test image
print("Creating synthetic test image...")
img = Image.new('RGB', (640, 480), color=(100, 150, 200))
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

# Test the new /analyze endpoint
print("\n[TEST] Uploading to POST /analyze endpoint...")
try:
    r = requests.post(f'{BASE_URL}/analyze', 
                     files={'image': ('test.jpg', img_bytes, 'image/jpeg')}, 
                     timeout=60)
    print(f"Status Code: {r.status_code}")
    data = r.json()
    
    if data.get('success'):
        print(f"\n✅ SUCCESS - /analyze endpoint is WORKING!")
        snap_id = data.get('id', 'N/A')
        print(f"  Snapshot ID: {snap_id}")
        print(f"  Detections count: {len(data.get('detections', []))}")
        print(f"  Class counts: {data.get('count', {})}")
        print(f"  Safety verdict: {data.get('safety_status', 'Unknown')}")
        b64_len = len(data.get('image_with_boxes', ''))
        print(f"  Annotated image (base64): {b64_len} chars {'✅' if b64_len > 0 else '❌'}")
        print(f"  Max confidence per class: {data.get('max_confidence', {})}")
        
        # Test PDF download if snapshot created
        if snap_id and snap_id != 'N/A':
            print(f"\n[TEST] Testing PDF download for snap_id={snap_id}...")
            pdf_url = f'{BASE_URL}/api/download-report/{snap_id}/'
            r_pdf = requests.get(pdf_url, timeout=30)
            if r_pdf.status_code == 200 and len(r_pdf.content) > 0:
                print(f"✅ PDF downloaded successfully: {len(r_pdf.content)} bytes")
            else:
                print(f"⚠️  PDF download status: {r_pdf.status_code}")
        print("\n🎉 All tests PASSED!")
    else:
        print(f"\n❌ FAILED - Response: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"\n❌ Request failed: {e}")

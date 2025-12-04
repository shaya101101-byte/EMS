import requests
import sys
from PIL import Image
import io

# Create simple test image
test_img = Image.new('RGB', (640, 480), color=(100, 150, 200))
img_bytes = io.BytesIO()
test_img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

# 1. UPLOAD
print("[1] Uploading test image...")
try:
    r_upload = requests.post('http://127.0.0.1:8000/api/upload-snapshot/', 
                             files={'image': ('test.jpg', img_bytes, 'image/jpeg')}, 
                             timeout=10)
    print(f"  Upload status: {r_upload.status_code}")
    if r_upload.status_code != 200:
        print(f"  ERROR: {r_upload.text}")
        sys.exit(1)
    snap_id = r_upload.json().get('id')
    print(f"  ✅ Snapshot ID: {snap_id}")
except Exception as e:
    print(f"  Upload failed: {e}")
    sys.exit(1)

# 2. ANALYZE
print(f"\n[2] Analyzing snapshot {snap_id}...")
try:
    r_analyze = requests.get(f'http://127.0.0.1:8000/api/analyze/{snap_id}/', timeout=60)
    print(f"  Analyze status: {r_analyze.status_code}")
    result = r_analyze.json()
    print(f"  ✅ Detections: {result.get('count', 0)}")
    print(f"  Species: {result.get('species', 'N/A')}")
    print(f"  Safety: {result.get('safe', 'N/A')}")
    print(f"  Confidence: {result.get('confidence', 'N/A')}")
except Exception as e:
    print(f"  Analyze failed: {e}")
    sys.exit(1)

# 3. REPORT
print(f"\n[3] Downloading report...")
try:
    r_report = requests.get(f'http://127.0.0.1:8000/api/download-report/{snap_id}/', timeout=30)
    print(f"  Report status: {r_report.status_code}")
    print(f"  Content-Type: {r_report.headers.get('content-type')}")
    print(f"  PDF Size: {len(r_report.content):,} bytes")
    if len(r_report.content) > 0:
        print(f"  ✅ PDF generated successfully")
except Exception as e:
    print(f"  Report failed: {e}")
    sys.exit(1)

print("\n✅ UNIFIED YOLO PIPELINE TEST PASSED!")

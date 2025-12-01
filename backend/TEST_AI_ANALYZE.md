# AquaSafe AI Endpoint - Testing Guide

## Endpoint Details

**POST** `/ai/analyze`

### Request
- **Content-Type**: `multipart/form-data`
- **Field**: `image` (file upload)

### Response Format
```json
{
  "status": "SAFE",
  "counts": {
    "Protozoa": 3,
    "Algae": 5,
    "Bacteria": 2,
    "Fungi": 0,
    "Cyanobacteria": 1,
    "Plant_Debris": 0,
    "Micro_Worm": 0
  },
  "percentages": {
    "Protozoa": 27.27,
    "Algae": 45.45,
    "Bacteria": 18.18,
    "Fungi": 0.0,
    "Cyanobacteria": 9.09,
    "Plant_Debris": 0.0,
    "Micro_Worm": 0.0
  },
  "annotated_image": "outputs/annotated_abc12345.jpg",
  "pie_chart": "outputs/pie_def67890.png",
  "bar_chart": "outputs/bar_ghi11111.png",
  "pdf": "outputs/report_jkl22222.pdf",
  "timestamp": "2025-11-30T15:30:45.123456"
}
```

### Safety Classification Rules
- **SAFE**: Total harmful species (Protozoa + Bacteria + Cyanobacteria) ≤ 10
- **UNSAFE**: Total harmful species > 10

### Testing with cURL
```bash
curl -X POST http://127.0.0.1:8000/ai/analyze \
  -F "image=@/path/to/test/image.jpg"
```

### Testing with Python
```python
import requests

with open('test_image.jpg', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:8000/ai/analyze',
        files={'image': f}
    )
    print(response.json())
```

### Testing with Frontend (JavaScript/Fetch)
```javascript
const formData = new FormData();
formData.append('image', imageFile); // File from input

fetch('http://127.0.0.1:8000/ai/analyze', {
    method: 'POST',
    body: formData
})
.then(res => res.json())
.then(data => {
    console.log('Analysis Result:', data);
    console.log('Status:', data.status);
    console.log('Counts:', data.counts);
})
.catch(err => console.error('Error:', err));
```

## Setup Steps

1. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Place Model Weights**:
   - Save your trained `best.pt` to `backend/models/best.pt`
   - If no model found, the system will use MOCK mode (generates dummy detections for testing)

3. **Create Output Directory**:
   - `backend/outputs/` is auto-created on first analysis

4. **Start Backend**:
   ```bash
   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. **Upload Image and Test**:
   - Use cURL, Python, or frontend to POST an image to `/ai/analyze`

## Output Files

All generated files are saved in `backend/outputs/`:

- `annotated_*.jpg` - Image with bounding boxes and labels
- `pie_*.png` - Species distribution pie chart
- `bar_*.png` - Species count bar chart
- `report_*.pdf` - Complete PDF report with all analysis

## History

Last 10 analyses are saved in `backend/history.json` for reference and auditing.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Model not found warning | Place `best.pt` in `backend/models/` or endpoint will use MOCK detections |
| YOLO not installed | Run: `pip install ultralytics opencv-python` |
| Charts not rendering | Ensure `matplotlib` is installed: `pip install matplotlib` |
| PDF generation fails | Install reportlab: `pip install reportlab` |
| No outputs folder | Runs auto-create; if permission denied, create manually: `mkdir backend/outputs` |

---

**Note**: The `/ai/analyze` endpoint is completely independent and does NOT affect existing routes like `/predict`, `/history`, `/stats`, etc.

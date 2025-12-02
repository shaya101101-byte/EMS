"""
YOLO-based microorganism analyzer service.

This module provides:
- initialize_model(): loads ultralytics YOLO model from backend/models/best.pt
- analyze_image_bytes(image_bytes): runs inference and returns structured results
- helpers for annotation, charts, and PDF generation

Customize `DEFAULT_SAFETY_MAP` and `SAFETY_DESCRIPTIONS` below.
"""
from typing import List, Dict, Any, Optional, Tuple
import os
import io
import base64
import datetime
import math
import uuid

# Image processing
from PIL import Image, ImageDraw, ImageFont

# Charts
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Model related imports are done lazily so the module can be imported
MODEL = None
MODEL_CONF = 0.10
MODEL_IOU = 0.45
MODEL_MAX_DET = 300

# Default safety mapping - edit as required
DEFAULT_SAFETY_MAP = {
    # 'class_name': 'Safe'|'Caution'|'Unsafe'
    'diatom': 'Safe',
    'rotifer': 'Caution',
    'copepod': 'Unsafe',
    'algae': 'Caution',
}

SAFETY_DESCRIPTIONS = {
    'Safe': 'No immediate concern detected for this class.',
    'Caution': 'Presence of this class may indicate moderate contamination; review recommended.',
    'Unsafe': 'High-risk organism detected. Immediate action recommended.'
}


def _model_path() -> str:
    # Resolve model path relative to backend root (not services subdir)
    base = os.path.dirname(os.path.dirname(__file__))  # Go up one level from services/
    return os.path.join(base, 'models', 'best.pt')


def initialize_model(confidence_threshold: float = 0.35, iou: float = 0.45, max_det: int = 300, device: Optional[str] = None):
    """Load ultralytics YOLO model. Raises ImportError with clear message if ultralytics is missing.
    Call this once at application startup.
    """
    global MODEL, MODEL_CONF, MODEL_IOU, MODEL_MAX_DET
    MODEL_CONF = confidence_threshold
    MODEL_IOU = iou
    MODEL_MAX_DET = max_det

    try:
        from ultralytics import YOLO
    except Exception as e:
        raise ImportError('ultralytics is required for YOLO inference. Install with `pip install ultralytics`.')

    path = _model_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f'YOLO model file not found at {path}. Place your weights at this path.')

    # Set deterministic seeds to make inference reproducible where possible
    try:
        import numpy as np
        import random
        np.random.seed(42)
        random.seed(42)
        # torch seed if available
        try:
            import torch
            torch.manual_seed(42)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(42)
        except Exception:
            pass
    except Exception:
        pass

    MODEL = YOLO(path)
    # Set some sensible default parameters if available
    return MODEL


def _decode_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert('RGB')


def _annotate_image_pil(image: Image.Image, boxes: List[Dict[str, Any]]) -> bytes:
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype('arial.ttf', 14)
    except Exception:
        font = ImageFont.load_default()

    for b in boxes:
        x1, y1, x2, y2 = b['box']
        conf = b.get('confidence', 0)
        cls = b.get('class', 'unknown')
        color = (255, 0, 0) if DEFAULT_SAFETY_MAP.get(cls, 'Safe') == 'Unsafe' else ((255,165,0) if DEFAULT_SAFETY_MAP.get(cls, 'Safe') == 'Caution' else (0,200,100))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        label = f"{cls} {conf:.2f}"
        draw.text((x1 + 4, y1 + 2), label, fill=color, font=font)

    buf = io.BytesIO()
    image.save(buf, format='PNG')
    return buf.getvalue()


def _image_bytes_to_base64(img_bytes: bytes) -> str:
    return base64.b64encode(img_bytes).decode('utf-8')


def _make_pie_chart(counts: Dict[str, int]) -> bytes:
    labels = list(counts.keys())
    sizes = [counts[k] for k in labels]
    fig, ax = plt.subplots(figsize=(4, 4))
    if sum(sizes) == 0:
        ax.text(0.5, 0.5, 'No detections', ha='center', va='center')
    else:
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    ax.axis('equal')
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='PNG')
    plt.close(fig)
    return buf.getvalue()


def _make_bar_chart(counts: Dict[str, int]) -> bytes:
    labels = list(counts.keys())
    sizes = [counts[k] for k in labels]
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(labels, sizes, color='tab:blue')
    ax.set_ylabel('Count')
    ax.set_xticklabels(labels, rotation=45, ha='right')
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='PNG')
    plt.close(fig)
    return buf.getvalue()


def _create_pdf_report(original_img_bytes: bytes, annotated_img_bytes: bytes, pie_bytes: bytes, bar_bytes: bytes, per_class: List[Dict[str, Any]], overall_verdict: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 40

    # Title
    c.setFont('Helvetica-Bold', 16)
    c.drawString(margin, height - margin, 'AquaSafe AI - Analysis Report')
    c.setFont('Helvetica', 10)
    c.drawString(margin, height - margin - 18, f'Time: {datetime.datetime.utcnow().isoformat()} UTC')

    y = height - margin - 50

    # Original image
    try:
        orig = ImageReader(io.BytesIO(original_img_bytes))
        c.drawImage(orig, margin, y - 180, width=220, height=180, preserveAspectRatio=True)
    except Exception:
        c.setFillColorRGB(0.8, 0.8, 0.8)
        c.rect(margin, y - 180, 220, 180, fill=1)
    
    # Annotated image
    try:
        ann = ImageReader(io.BytesIO(annotated_img_bytes))
        c.drawImage(ann, margin + 240, y - 180, width=220, height=180, preserveAspectRatio=True)
    except Exception:
        pass

    y = y - 200

    # Charts
    try:
        pie = ImageReader(io.BytesIO(pie_bytes))
        c.drawImage(pie, margin, y - 160, width=180, height=160, preserveAspectRatio=True)
    except Exception:
        pass
    try:
        bar = ImageReader(io.BytesIO(bar_bytes))
        c.drawImage(bar, margin + 200, y - 160, width=320, height=160, preserveAspectRatio=True)
    except Exception:
        pass

    y = y - 180

    # Table header
    c.setFont('Helvetica-Bold', 11)
    c.drawString(margin, y, 'Class')
    c.drawString(margin + 140, y, 'Count')
    c.drawString(margin + 200, y, 'Percentage')
    c.drawString(margin + 300, y, 'Avg Confidence')
    c.drawString(margin + 420, y, 'Safety')
    y = y - 18
    c.setFont('Helvetica', 10)

    for row in per_class:
        c.drawString(margin, y, str(row.get('class')))
        c.drawString(margin + 140, y, str(row.get('count')))
        c.drawString(margin + 200, y, f"{row.get('percentage'):.1f}%")
        c.drawString(margin + 300, y, f"{row.get('avg_confidence'):.2f}")
        c.drawString(margin + 420, y, row.get('safety', 'N/A'))
        y = y - 16
        if y < 80:
            c.showPage()
            y = height - margin

    # Overall verdict
    if y < 120:
        c.showPage()
        y = height - margin
    c.setFont('Helvetica-Bold', 12)
    c.drawString(margin, y - 10, f"Overall verdict: {overall_verdict.get('verdict')}")
    c.setFont('Helvetica', 10)
    c.drawString(margin, y - 28, f"Reason: {overall_verdict.get('reason')}")

    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


def analyze_image_bytes(image_bytes: bytes, conf_thresh: Optional[float] = None, iou: Optional[float] = None) -> Dict[str, Any]:
    """Run the full analysis pipeline and return structured JSON-compatible dict.
    """
    global MODEL, MODEL_CONF, MODEL_IOU
    if MODEL is None:
        raise RuntimeError('Model not initialized. Call initialize_model() first.')

    conf = conf_thresh if conf_thresh is not None else MODEL_CONF
    iou = iou if iou is not None else MODEL_IOU

    # Decode image for original bytes
    pil_img = _decode_image(image_bytes)
    w, h = pil_img.size

    # Run ultralytics inference
    try:
        # Use device default; ensure deterministic seeds set in initialize_model
        results = MODEL.predict(source=pil_img, conf=conf, iou=iou, max_det=MODEL_MAX_DET)
    except Exception as e:
        raise RuntimeError(f'Inference failed: {e}')

    res = results[0]
    boxes = []
    names = getattr(MODEL, 'names', {}) or {}
    for det in getattr(res, 'boxes', []):
        try:
            xyxy = det.xyxy[0].tolist()
            x1, y1, x2, y2 = map(int, xyxy)
        except Exception:
            continue
        conf_score = float(det.conf[0]) if hasattr(det, 'conf') else float(det.conf)
        cls_idx = int(det.cls[0]) if hasattr(det, 'cls') else int(det.cls)
        cls_name = names.get(cls_idx, f'class{cls_idx}')
        boxes.append({'box': [x1, y1, x2, y2], 'confidence': conf_score, 'class': cls_name})

    total = len(boxes)

    # Per-class aggregation
    counts = {}
    conf_sums = {}
    for b in boxes:
        cname = b['class']
        counts[cname] = counts.get(cname, 0) + 1
        conf_sums[cname] = conf_sums.get(cname, 0.0) + b.get('confidence', 0.0)

    per_class = []
    for cname, cnt in counts.items():
        avg_conf = (conf_sums.get(cname, 0.0) / cnt) if cnt > 0 else 0.0
        percentage = round((cnt / total * 100), 1) if total > 0 else 0.0
        safety = DEFAULT_SAFETY_MAP.get(cname, 'Safe')
        per_class.append({
            'class': cname,
            'count': cnt,
            'percentage': percentage,
            'avg_confidence': round(avg_conf, 3),
            'safety': safety,
            'description': SAFETY_DESCRIPTIONS.get(safety, '')
        })

    # Sort per_class by count desc
    per_class = sorted(per_class, key=lambda x: x['count'], reverse=True)

    # Overall verdict rules
    unsafe_classes = [p for p in per_class if p['safety'] == 'Unsafe']
    caution_classes = [p for p in per_class if p['safety'] == 'Caution']
    overall = {'verdict': 'Safe', 'reason': 'No concerning classes detected.'}
    if len(unsafe_classes) > 1 or any(p['percentage'] > 20.0 for p in unsafe_classes):
        overall = {'verdict': 'Unsafe', 'reason': 'Multiple or dominant unsafe classes detected.'}
    elif len(caution_classes) > 0:
        overall = {'verdict': 'Caution', 'reason': 'One or more cautionary classes detected.'}

    # Annotated image - save to disk and return URL instead of base64
    annotated_bytes = _annotate_image_pil(pil_img.copy(), boxes)
    # Create static/results directory if it doesn't exist
    os.makedirs('static/results', exist_ok=True)
    annotated_filename = f"annotated_{uuid.uuid4().hex[:8]}.png"
    annotated_path = os.path.join('static/results', annotated_filename)
    with open(annotated_path, 'wb') as f:
        f.write(annotated_bytes)
    # Return absolute URL to backend (frontend will use this from different port)
    annotated_image_url = f"http://127.0.0.1:8000/static/results/{annotated_filename}"

    # Charts
    pie_bytes = _make_pie_chart(counts)
    bar_bytes = _make_bar_chart(counts)
    pie_b64 = _image_bytes_to_base64(pie_bytes)
    bar_b64 = _image_bytes_to_base64(bar_bytes)

    # PDF
    try:
        pdf_bytes = _create_pdf_report(image_bytes, annotated_bytes, pie_bytes, bar_bytes, per_class, overall)
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
    except Exception as e:
        pdf_b64 = ''

    return {
        'total_detections': total,
        'per_class': per_class,
        'overall_verdict': overall,
        'annotated_image_url': annotated_image_url,
        'annotated_image_base64': '',  # Empty for compatibility; URL is used instead
        'pie_chart_base64': pie_b64,
        'bar_chart_base64': bar_b64,
        'pdf_base64': pdf_b64,
    }

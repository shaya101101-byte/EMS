# services/postprocessing.py
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from collections import Counter

# simple helper to draw boxes and produce base64
def annotate_image_bytes(image_bytes, boxes):
    """
    boxes: list of dicts: {x1,y1,x2,y2,score,class}
    returns: annotated bytes
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()

    for b in boxes:
        color = (0,200,100) if b.get("class") != "algae" else (220,80,80)
        draw.rectangle([b["x1"], b["y1"], b["x2"], b["y2"]], outline=color, width=2)
        label = f"{b.get('class')} {b.get('score'):.2f}"
        draw.text((b["x1"]+4, b["y1"]+2), label, fill=color, font=font)
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()

def to_base64(bytes_obj):
    return base64.b64encode(bytes_obj).decode("utf-8")

def summarize_counts(boxes):
    classes = [b.get("class") for b in boxes]
    c = Counter(classes)
    total = sum(c.values())
    dominant = c.most_common(1)[0][0] if c else None
    return dict(c), total, dominant

# ---- AquaSafe AI (Added Feature) ----
# AI-powered water analysis using YOLO detection
# Generates: annotated images, charts, PDF reports, and safety classification
# Copilot: Fix the YOLO model path. The current relative path ("backend/models/best.pt") fails
# because the backend working directory changes. Add a safe, additive-only fix:
#
# In __init__, resolve the model path relative to this file:
#   import os
#   file_dir = os.path.dirname(os.path.abspath(__file__))
#   self.model_path = os.path.join(file_dir, "models", "best.pt")
#
# Do NOT remove existing code — only add this path resolution block before checking exists().

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from io import BytesIO

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


# ---- Class Mapping ----
CLASS_MAP = {
    0: "Protozoa",
    1: "Algae",
    2: "Bacteria",
    3: "Fungi",
    4: "Cyanobacteria",
    5: "Plant_Debris",
    6: "Micro_Worm"
}

HARMFUL_SPECIES = ["Protozoa", "Bacteria", "Cyanobacteria"]


class AquaSafeAI:
    """
    AquaSafe AI Analyzer: YOLO-based water quality detection and reporting.
    """
    
    def __init__(self, model_path: str = None, output_dir: str = "backend/outputs"):
        """
        Initialize the AI analyzer.
        
        Args:
            model_path: Path to YOLO model weights (best.pt). If None, resolves to backend/models/best.pt relative to this file.
            output_dir: Directory to save outputs (images, charts, PDFs)
        """
        # Resolve model path relative to this file if not provided
        if model_path is None:
            file_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(file_dir, "models", "best.pt")
        self.model_path = model_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.history_file = Path("backend/history.json")
        
        # Load YOLO model if available
        if YOLO_AVAILABLE and os.path.exists(model_path):
            try:
                self.model = YOLO(model_path)
            except Exception as e:
                print(f"Warning: Could not load YOLO model from {model_path}: {e}")
        elif YOLO_AVAILABLE:
            print(f"Warning: Model file not found at {model_path}. Using mock mode.")
        else:
            print("Warning: Ultralytics YOLO not installed. Install with: pip install ultralytics")
    
    def _mock_inference(self, image_array: np.ndarray) -> Dict:
        """
        Generate mock detections for testing when model is not available.
        """
        h, w = image_array.shape[:2]
        mock_detections = {
            "boxes": [
                [0.1*w, 0.1*h, 0.3*w, 0.3*h, 0, 0.9],  # class 0 (Protozoa)
                [0.5*w, 0.2*h, 0.7*w, 0.4*h, 1, 0.85],  # class 1 (Algae)
                [0.2*w, 0.6*h, 0.4*w, 0.8*h, 2, 0.88],  # class 2 (Bacteria)
            ]
        }
        return mock_detections
    
    def run_detection(self, image_array: np.ndarray) -> Dict:
        """
        Run YOLO detection on image.
        
        Args:
            image_array: numpy array (BGR from OpenCV or RGB from PIL)
        
        Returns:
            Dictionary with detection results
        """
        if not YOLO_AVAILABLE:
            return self._mock_inference(image_array)
        
        if self.model is None:
            return self._mock_inference(image_array)
        
        try:
            # Use lower confidence threshold (0.10) to detect more organisms
            results = self.model(image_array, conf=0.10, iou=0.45)
            detections = {
                "boxes": [],
                "raw_results": results
            }
            
            if len(results) > 0:
                result = results[0]
                if result.boxes is not None:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        cls = int(box.cls[0].cpu().numpy())
                        conf = float(box.conf[0].cpu().numpy())
                        detections["boxes"].append([x1, y1, x2, y2, cls, conf])
            
            return detections
        except Exception as e:
            print(f"Error during detection: {e}")
            return self._mock_inference(image_array)
    
    def annotate_image(self, image_array: np.ndarray, detections: Dict) -> np.ndarray:
        """
        Draw bounding boxes and labels on image.
        
        Args:
            image_array: Input image (BGR)
            detections: Detection results from run_detection
        
        Returns:
            Annotated image (BGR)
        """
        if not CV2_AVAILABLE:
            return image_array.copy()
        
        annotated = image_array.copy()
        
        # Get class names from YOLO model if available
        class_names = {}
        if self.model is not None and hasattr(self.model, 'names'):
            class_names = self.model.names if isinstance(self.model.names, dict) else {i: n for i, n in enumerate(self.model.names)}
        
        for box_data in detections.get("boxes", []):
            x1, y1, x2, y2, cls_id, conf = box_data
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            cls_id = int(cls_id)
            
            # Use class name from model, fallback to CLASS_MAP, then generic label
            class_name = class_names.get(cls_id, CLASS_MAP.get(cls_id, f"Unknown_{cls_id}"))
            label = f"{class_name} ({conf:.2f})"
            
            # Draw bounding box
            color = (0, 255, 0) if class_name not in HARMFUL_SPECIES else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
            text_x, text_y = x1, max(y1 - 5, text_size[1] + 5)
            cv2.rectangle(annotated, (text_x, text_y - text_size[1] - 5), 
                         (text_x + text_size[0], text_y), color, -1)
            cv2.putText(annotated, label, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)
        
        return annotated
    
    def compute_statistics(self, detections: Dict) -> Tuple[Dict, Dict, str]:
        """
        Compute species counts, percentages, and safety status.
        
        Args:
            detections: Detection results
        
        Returns:
            (counts_dict, percentages_dict, safety_status)
        """
        # Get class names from YOLO model if available
        class_names = {}
        if self.model is not None and hasattr(self.model, 'names'):
            class_names = self.model.names if isinstance(self.model.names, dict) else {i: n for i, n in enumerate(self.model.names)}
        
        # Initialize counts with all possible class names (from model or CLASS_MAP)
        counts = {}
        for cls_id in range(max(7, len(class_names))):  # At least 7 classes from CLASS_MAP
            cls_name = class_names.get(cls_id, CLASS_MAP.get(cls_id, f"Unknown_{cls_id}"))
            counts[cls_name] = 0
        
        # Count detections
        for box_data in detections.get("boxes", []):
            cls_id = int(box_data[4])
            class_name = class_names.get(cls_id, CLASS_MAP.get(cls_id, f"Unknown_{cls_id}"))
            counts[class_name] = counts.get(class_name, 0) + 1
        
        # Remove zero counts for cleaner output
        counts = {k: v for k, v in counts.items() if v > 0}
        
        total = sum(counts.values())
        percentages = {k: (v / total * 100) if total > 0 else 0 for k, v in counts.items()}
        
        # Safety classification
        harmful_count = sum(counts.get(sp, 0) for sp in HARMFUL_SPECIES)
        safety_status = "UNSAFE" if harmful_count > 10 else "SAFE"
        
        return counts, percentages, safety_status
    
    def generate_pie_chart(self, counts: Dict) -> str:
        """
        Generate pie chart and save as PNG.
        
        Args:
            counts: Species count dictionary
        
        Returns:
            Path to saved pie chart PNG
        """
        if not MPL_AVAILABLE:
            return ""
        
        try:
            non_zero = {k: v for k, v in counts.items() if v > 0}
            if not non_zero:
                return ""
            
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.pie(non_zero.values(), labels=non_zero.keys(), autopct='%1.1f%%', startangle=90)
            ax.set_title("Species Distribution (Pie Chart)")
            
            pie_file = self.output_dir / f"pie_{uuid.uuid4().hex[:8]}.png"
            plt.savefig(pie_file, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            return str(pie_file.relative_to(Path("backend")))
        except Exception as e:
            print(f"Error generating pie chart: {e}")
            return ""
    
    def generate_bar_chart(self, counts: Dict) -> str:
        """
        Generate bar chart and save as PNG.
        
        Args:
            counts: Species count dictionary
        
        Returns:
            Path to saved bar chart PNG
        """
        if not MPL_AVAILABLE:
            return ""
        
        try:
            non_zero = {k: v for k, v in counts.items() if v > 0}
            if not non_zero:
                return ""
            
            fig, ax = plt.subplots(figsize=(10, 6))
            species = list(non_zero.keys())
            values = list(non_zero.values())
            colors_bar = ['red' if sp in HARMFUL_SPECIES else 'green' for sp in species]
            ax.bar(species, values, color=colors_bar)
            ax.set_title("Species Count (Bar Chart)")
            ax.set_ylabel("Count")
            ax.set_xlabel("Species")
            plt.xticks(rotation=45, ha='right')
            
            bar_file = self.output_dir / f"bar_{uuid.uuid4().hex[:8]}.png"
            plt.savefig(bar_file, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            return str(bar_file.relative_to(Path("backend")))
        except Exception as e:
            print(f"Error generating bar chart: {e}")
            return ""
    
    def generate_pdf_report(self, annotated_image: np.ndarray, counts: Dict, percentages: Dict, 
                           pie_chart_path: str, bar_chart_path: str, safety_status: str) -> str:
        """
        Generate PDF report with all analysis results.
        
        Args:
            annotated_image: Annotated image array
            counts: Species count dictionary
            percentages: Species percentages dictionary
            pie_chart_path: Path to pie chart PNG
            bar_chart_path: Path to bar chart PNG
            safety_status: "SAFE" or "UNSAFE"
        
        Returns:
            Path to saved PDF
        """
        if not PDF_AVAILABLE or not CV2_AVAILABLE:
            return ""
        
        try:
            pdf_file = self.output_dir / f"report_{uuid.uuid4().hex[:8]}.pdf"
            
            # Save annotated image temporarily
            temp_img_path = self.output_dir / f"temp_annotated_{uuid.uuid4().hex[:8]}.png"
            cv2.imwrite(str(temp_img_path), annotated_image)
            
            doc = SimpleDocTemplate(str(pdf_file), pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f77b4'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            story.append(Paragraph("AquaSafe AI - Water Analysis Report", title_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Timestamp and Safety Status
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Use explicit hex strings for font color to avoid relying on reportlab internals
            status_color_hex = '00aa00' if safety_status == "SAFE" else 'ff0000'

            story.append(Paragraph(f"<b>Analysis Time:</b> {timestamp}", styles['Normal']))
            story.append(Paragraph(f"<b>Safety Status:</b> <font color='#{status_color_hex}'>{safety_status}</font>", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            # Annotated Image
            if os.path.exists(temp_img_path):
                story.append(Paragraph("<b>Annotated Image:</b>", styles['Heading2']))
                img = Image(str(temp_img_path), width=5*inch, height=4*inch)
                story.append(img)
                story.append(Spacer(1, 0.2*inch))
            
            # Species Counts and Percentages Table
            story.append(Paragraph("<b>Species Analysis:</b>", styles['Heading2']))
            table_data = [["Species", "Count", "Percentage"]]
            for species, count in counts.items():
                pct = percentages.get(species, 0)
                table_data.append([species, str(count), f"{pct:.1f}%"])
            
            table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
            story.append(Spacer(1, 0.2*inch))
            
            # Add charts if available
            if pie_chart_path and os.path.exists(self.output_dir / pie_chart_path.split('/')[-1]):
                story.append(PageBreak())
                story.append(Paragraph("<b>Charts:</b>", styles['Heading2']))
                pie_img = Image(str(self.output_dir / pie_chart_path.split('/')[-1]), width=4*inch, height=3*inch)
                story.append(pie_img)
                story.append(Spacer(1, 0.2*inch))
            
            if bar_chart_path and os.path.exists(self.output_dir / bar_chart_path.split('/')[-1]):
                bar_img = Image(str(self.output_dir / bar_chart_path.split('/')[-1]), width=5*inch, height=3*inch)
                story.append(bar_img)
            
            doc.build(story)
            
            # Clean up temp image
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
            
            return str(pdf_file.relative_to(Path("backend")))
        except Exception as e:
            print(f"Error generating PDF: {e}")
            return ""
    
    def save_to_history(self, analysis_result: Dict) -> None:
        """
        Save analysis to history.json (keep last 10).
        
        Args:
            analysis_result: Complete analysis result dictionary
        """
        try:
            history = []
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            
            # Add new result
            history.append({
                "timestamp": datetime.now().isoformat(),
                **analysis_result
            })
            
            # Keep only last 10
            history = history[-10:]
            
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Error saving to history: {e}")
    
    def analyze_image(self, image_array: np.ndarray) -> Dict:
        """
        Complete analysis pipeline: detect, annotate, generate charts/PDF, compute stats.
        
        Args:
            image_array: Input image (BGR or RGB)
        
        Returns:
            Complete analysis result dictionary
        """
        # Run detection
        detections = self.run_detection(image_array)
        
        # Annotate image
        annotated_img = self.annotate_image(image_array, detections)
        
        # Save annotated image
        annotated_filename = f"annotated_{uuid.uuid4().hex[:8]}.jpg"
        annotated_path = self.output_dir / annotated_filename
        if CV2_AVAILABLE:
            cv2.imwrite(str(annotated_path), annotated_img)
        
        # Compute statistics
        counts, percentages, safety_status = self.compute_statistics(detections)
        
        # Generate charts
        pie_chart = self.generate_pie_chart(counts)
        bar_chart = self.generate_bar_chart(counts)
        
        # Generate PDF
        pdf_report = self.generate_pdf_report(annotated_img, counts, percentages, pie_chart, bar_chart, safety_status)
        
        # Prepare response
        result = {
            "status": safety_status,
            "counts": counts,
            "percentages": percentages,
            "annotated_image": f"outputs/{annotated_filename}",
            "pie_chart": pie_chart,
            "bar_chart": bar_chart,
            "pdf": pdf_report,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to history
        self.save_to_history(result)
        
        return result


# ---- Singleton Instance ----
_ai_analyzer = None

def get_ai_analyzer():
    """Get or create singleton AI analyzer instance."""
    global _ai_analyzer
    if _ai_analyzer is None:
        _ai_analyzer = AquaSafeAI()
    return _ai_analyzer

from fastapi import APIRouter
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import datetime

router = APIRouter()

@router.get("/analytics-report-pdf")
def generate_pdf_report():

    filename = "water_quality_report.pdf"

    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['BodyText']

    # Title
    elements.append(Paragraph("Water Quality Report", title_style))
    elements.append(Spacer(1, 12))

    # Date
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph(f"Generated On: {now}", normal_style))
    elements.append(Spacer(1, 12))

    # Water Safety
    safety_status = "Safe"
    safety_text = f"Overall Water Safety Status: <b>{safety_status}</b>"
    elements.append(Paragraph(safety_text, normal_style))
    elements.append(Spacer(1, 12))

    # Table Data
    table_data = [
        ["Organism Name", "Type", "Count"],
        ["None", "None", "0"]
    ]

    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold")
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    doc.build(elements)

    return FileResponse(filename, media_type="application/pdf", filename=filename)

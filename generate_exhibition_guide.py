from __future__ import annotations

from pathlib import Path
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "RetinAI_Exhibition_Guide.pdf"

PRIMARY = colors.HexColor("#1B3A5C")
ACCENT = colors.HexColor("#2C7BE5")
TEXT = colors.HexColor("#111827")
MUTED = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#F1F5F9")
SOFT_BLUE = colors.HexColor("#EAF2FF")
SOFT_GREEN = colors.HexColor("#ECFDF5")


def build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            alignment=TA_CENTER,
            textColor=PRIMARY,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=PRIMARY,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=10.2,
            leading=15,
            alignment=TA_JUSTIFY,
            textColor=TEXT,
            spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName="Helvetica",
            fontSize=10.1,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT,
            leftIndent=10,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small",
            fontName="Helvetica",
            fontSize=8.8,
            leading=11,
            alignment=TA_LEFT,
            textColor=MUTED,
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            fontName="Helvetica-Bold",
            fontSize=9.2,
            leading=11,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),
        "table_body": ParagraphStyle(
            "TableBody",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=TEXT,
        ),
    }


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(15 * mm, 10 * mm, "RetinAI - Exhibition Guide")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def section(title: str, style):
    return Paragraph(title, style["section"])


def bullet_list(items, style):
    flowables = []
    for item in items:
        flowables.append(Paragraph(f"- {item}", style["bullet"]))
    return flowables


def make_table(rows, col_widths):
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9.2),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def color_box(text, bg_color, style):
    return Table(
        [[Paragraph(text, style["body"])]],
        colWidths=[170 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        ),
    )


def build_pdf():
    style = build_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
    )

    story = []

    story.append(Spacer(1, 8))
    story.append(Paragraph("RETINAI", style["title"]))
    story.append(Paragraph("Diabetic Retinopathy Detection System - Exhibition Guide", style["subtitle"]))
    story.append(Paragraph(
        "Final Year Project for the University of Haripur, Department of Information Technology. "
        "This guide is written for exhibition presentation, viva preparation, and quick revision.",
        style["body"],
    ))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceBefore=4, spaceAfter=10))

    story.append(section("1. Project Overview", style))
    story.append(Paragraph(
        "RetinAI is a web-based medical AI system that analyzes retinal fundus images to detect diabetic retinopathy. "
        "It helps doctors upload a fundus image, enter patient information, receive a severity prediction, view confidence values, "
        "generate an explainable Grad-CAM heatmap, save the scan to a database, and send a report to the patient by email.",
        style["body"],
    ))
    story.append(Paragraph(
        "The system focuses on five diabetic retinopathy stages: No DR, Mild, Moderate, Severe, and Proliferative. "
        "The interface is designed for practical clinic use and exhibition demos rather than only model experimentation.",
        style["body"],
    ))

    story.append(section("2. Problem Statement", style))
    story.append(Paragraph(
        "Diabetic retinopathy is a serious eye complication caused by diabetes. Early detection is important because vision loss "
        "can often be reduced if the condition is identified and referred on time. Manual screening is slow, requires specialists, "
        "and may be difficult in busy clinics. This project solves that problem by automating the first screening step with AI.",
        style["body"],
    ))

    story.append(section("3. Basic Concepts You Should Know", style))
    for item in bullet_list([
        "Diabetic retinopathy is damage to retinal blood vessels caused by diabetes.",
        "A fundus image is a photograph of the inside of the eye, especially the retina.",
        "A CNN is a deep learning model used for image classification.",
        "Transfer learning reuses a pretrained model architecture and adapts it to a new task.",
        "Ensemble learning combines predictions from multiple models to improve stability.",
        "Grad-CAM is a visualization method that highlights image regions affecting the prediction.",
        "Confidence score means how certain the model is about the chosen class.",
        "Flask is the Python web framework used for the app backend and routing.",
        "Jinja2 templates render HTML pages dynamically from Flask.",
        "SQLite stores doctors, scans, and prediction history locally in the project.",
    ], style):
        story.append(item)

    story.append(section("4. Technology Stack", style))
    tech_rows = [
        [Paragraph("Layer", style["table_head"]), Paragraph("Technology", style["table_head"]), Paragraph("Purpose", style["table_head"])],
        [Paragraph("Frontend", style["table_body"]), Paragraph("HTML, CSS, JavaScript, Jinja2", style["table_body"]), Paragraph("Builds the landing page, dashboard, scan form, history page, and report pages.", style["table_body"])],
        [Paragraph("Backend", style["table_body"]), Paragraph("Flask", style["table_body"]), Paragraph("Handles routing, sessions, authentication, and API responses.", style["table_body"])],
        [Paragraph("AI Models", style["table_body"]), Paragraph("PyTorch, EfficientNet-B5, ResNet-101", style["table_body"]), Paragraph("Performs image classification on retinal scans.", style["table_body"])],
        [Paragraph("Image Processing", style["table_body"]), Paragraph("OpenCV, PIL, CLAHE", style["table_body"]), Paragraph("Improves contrast and prepares images for inference.", style["table_body"])],
        [Paragraph("Storage", style["table_body"]), Paragraph("SQLite", style["table_body"]), Paragraph("Stores users, patient details, scan records, and results.", style["table_body"])],
        [Paragraph("Reports", style["table_body"]), Paragraph("ReportLab, HTML email", style["table_body"]), Paragraph("Creates PDF reports and sends result emails.", style["table_body"])],
        [Paragraph("UI Assets", style["table_body"]), Paragraph("Font Awesome, Google Fonts", style["table_body"]), Paragraph("Provides icons and the visual style used in the pages.", style["table_body"])],
    ]
    story.append(make_table(tech_rows, [28 * mm, 60 * mm, 82 * mm]))

    story.append(section("5. Methodology", style))
    methodology_steps = [
        "Image input: The doctor uploads a retinal fundus image and fills in patient details such as name, age, email, eye side, and medical notes.",
        "Preprocessing: The image is converted to RGB, enhanced with CLAHE, resized to 256 x 256, normalized, and transformed into a tensor.",
        "Model inference: EfficientNet-B5 and ResNet-101 are loaded from the models folder when available.",
        "Ensemble decision: The system averages the probability outputs of both models to produce the final class.",
        "Interpretability: Grad-CAM is generated to show where the network looked while making the prediction.",
        "Decision support: The app maps the result to one of five severity levels and attaches clinical recommendations.",
        "Storage and reporting: The scan is saved in SQLite, can be viewed in history, and can be exported or emailed as a report.",
    ]
    for item in methodology_steps:
        story.append(Paragraph(f"- {item}", style["bullet"]))

    story.append(section("6. System Workflow", style))
    workflow = [
        [Paragraph("Step", style["table_head"]), Paragraph("What happens", style["table_head"])],
        [Paragraph("1", style["table_body"]), Paragraph("Doctor logs in or signs up through the Flask authentication pages.", style["table_body"])],
        [Paragraph("2", style["table_body"]), Paragraph("Doctor opens the New Scan page and enters patient details.", style["table_body"])],
        [Paragraph("3", style["table_body"]), Paragraph("A fundus image is uploaded from the local system or camera source.", style["table_body"])],
        [Paragraph("4", style["table_body"]), Paragraph("The backend preprocesses the image and runs both CNN models.", style["table_body"])],
        [Paragraph("5", style["table_body"]), Paragraph("The ensemble result produces a severity label, confidence, and class probabilities.", style["table_body"])],
        [Paragraph("6", style["table_body"]), Paragraph("Grad-CAM is generated to make the prediction explainable.", style["table_body"])],
        [Paragraph("7", style["table_body"]), Paragraph("The result is stored in SQLite and a detailed report can be viewed or emailed.", style["table_body"])],
        [Paragraph("8", style["table_body"]), Paragraph("The dashboard and history pages let the doctor review previous scans and delete records if required.", style["table_body"])],
    ]
    story.append(make_table(workflow, [18 * mm, 142 * mm]))

    story.append(section("7. Problems Solved by the Project", style))
    for item in bullet_list([
        "Slow manual screening by giving an instant first-level decision.",
        "Lack of explainability by showing Grad-CAM heatmaps.",
        "Single-model instability by combining two deep models in an ensemble.",
        "Poor follow-up tracking by storing scan history in SQLite.",
        "Poor communication with patients by generating reports and email output.",
        "Clinic workflow fragmentation by putting upload, analysis, history, and reporting in one web system.",
    ], style):
        story.append(item)

    story.append(section("8. Results and Outcomes", style))
    story.append(Paragraph(
        "The repository documents the system as an AI-powered five-class diabetic retinopathy detector with a dark-themed web interface, "
        "patient record storage, PDF reporting, email delivery, and Grad-CAM explainability. The README states that the trained project "
        "targets 90%+ accuracy with the ensemble of EfficientNet-B5 and ResNet-101. If the model files are not available, the app falls "
        "back to a demo mode so the full workflow can still be demonstrated during an exhibition.",
        style["body"],
    ))
    story.append(color_box(
        "Practical outcome: the doctor can demonstrate an end-to-end screening workflow, show the prediction confidence, explain the result visually, and generate a patient-ready report in one session.",
        SOFT_BLUE,
        style,
    ))
    story.append(Spacer(1, 4))
    story.append(color_box(
        "Project result summary: automated screening, explainable AI, patient record management, and report generation were all integrated into one working platform.",
        SOFT_GREEN,
        style,
    ))

    story.append(section("9. Conclusion", style))
    story.append(Paragraph(
        "RetinAI is a complete final-year project that combines computer vision, deep learning, web development, and medical reporting. "
        "It addresses the need for quick diabetic retinopathy screening and presents the findings in a form that is easy for doctors to use and "
        "easy for examiners to understand. For exhibition purposes, the key message is simple: the system helps detect retinal disease early, "
        "explains its prediction, stores the result, and communicates it clearly.",
        style["body"],
    ))

    story.append(section("10. Short Viva Talking Points", style))
    for item in bullet_list([
        "Why did you choose diabetic retinopathy? Because early detection is critical and AI can help with screening.",
        "Why two models? To improve robustness through ensemble averaging.",
        "Why Grad-CAM? To show that the model is focusing on medically relevant regions.",
        "Why Flask? It is lightweight and fast for building the web application.",
        "Why SQLite? It is simple, local, and enough for a final-year project prototype.",
        "What happens if the model files are missing? The app still runs in demo mode for presentation.",
    ], style):
        story.append(item)

    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceBefore=6, spaceAfter=6))
    story.append(Paragraph(
        f"Prepared for exhibition use on {datetime.now().strftime('%d %B %Y')}. This PDF was generated from the project workspace.",
        style["small"],
    ))

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)


if __name__ == "__main__":
    build_pdf()
    print(f"Created {OUTPUT}")
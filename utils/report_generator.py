"""
PDF Report Generator for Diabetic Retinopathy Analysis.
Uses ReportLab to produce professional clinical reports.
"""

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# ─── Brand Colors ────────────────────────────────────────
PRIMARY    = colors.HexColor('#1B3A5C')   # Deep navy
ACCENT     = colors.HexColor('#2C7BE5')   # Medical blue
SUCCESS    = colors.HexColor('#1A7F5A')   # Green
WARNING    = colors.HexColor('#D97706')   # Amber
DANGER     = colors.HexColor('#C0392B')   # Red
DARK       = colors.HexColor('#111827')   # Near black
LIGHT_GRAY = colors.HexColor('#F1F5F9')
MID_GRAY   = colors.HexColor('#94A3B8')
WHITE      = colors.white

SEVERITY_COLOR_MAP = {
    0: SUCCESS,
    1: colors.HexColor('#0EA5E9'),
    2: WARNING,
    3: colors.HexColor('#EA580C'),
    4: DANGER,
}

SEVERITY_LABEL_MAP = {
    0: 'No DR',
    1: 'Mild DR',
    2: 'Moderate DR',
    3: 'Severe DR',
    4: 'Proliferative DR',
}

PAGE_W, PAGE_H = A4


def _styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=18,
                                textColor=WHITE, alignment=TA_CENTER, spaceAfter=2),
        'subtitle': ParagraphStyle('subtitle', fontName='Helvetica', fontSize=10,
                                   textColor=colors.HexColor('#CBD5E1'), alignment=TA_CENTER),
        'section': ParagraphStyle('section', fontName='Helvetica-Bold', fontSize=11,
                                  textColor=PRIMARY, spaceBefore=10, spaceAfter=4),
        'body': ParagraphStyle('body', fontName='Helvetica', fontSize=9.5,
                               textColor=DARK, leading=14, spaceAfter=3,
                               alignment=TA_JUSTIFY),
        'label': ParagraphStyle('label', fontName='Helvetica-Bold', fontSize=9,
                                textColor=MID_GRAY),
        'value': ParagraphStyle('value', fontName='Helvetica', fontSize=9.5,
                                textColor=DARK),
        'small': ParagraphStyle('small', fontName='Helvetica', fontSize=8,
                                textColor=MID_GRAY, alignment=TA_CENTER),
        'severity': ParagraphStyle('severity', fontName='Helvetica-Bold', fontSize=14,
                                   alignment=TA_CENTER, textColor=WHITE),
        'severity_sub': ParagraphStyle('severity_sub', fontName='Helvetica', fontSize=9,
                                       alignment=TA_CENTER, textColor=colors.HexColor('#E2E8F0')),
        'rec': ParagraphStyle('rec', fontName='Helvetica', fontSize=9.5,
                              textColor=DARK, leading=15, spaceAfter=4,
                              leftIndent=8),
    }


def _header_table(doctor):
    s = _styles()
    left = [
        Paragraph('DIABETIC RETINOPATHY', s['title']),
        Paragraph('DETECTION REPORT', s['title']),
        Spacer(1, 2),
        Paragraph('AI-Powered Retinal Analysis System', s['subtitle']),
    ]
    # Use safe .get() to tolerate missing keys from older DB schemas
    doc_name = doctor.get('full_name') if isinstance(doctor, dict) else None
    right_text = (
        f"<b>Physician:</b> Dr. {doc_name or '—'}<br/>"
        f"<b>Report Date:</b> {datetime.now().strftime('%d %B %Y, %H:%M')}"
    )
    right_style = ParagraphStyle('rh', fontName='Helvetica', fontSize=8.5,
                                 textColor=colors.HexColor('#CBD5E1'), alignment=TA_RIGHT,
                                 leading=13)
    data = [[left, Paragraph(right_text, right_style)]]
    t = Table(data, colWidths=[110*mm, 70*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
        ('TOPPADDING',    (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING',   (0, 0), (0, 0),  14),
        ('RIGHTPADDING',  (-1, 0), (-1, 0), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def _patient_info_table(patient, analysis):
    s = _styles()
    rows = [
        ['Patient Name', patient['patient_name'],
         'Patient ID',   patient['patient_id']],
        ['Age',          f"{patient['age']} years",
         'Gender',       patient['gender'] or '—'],
        ['Contact',      patient['phone'] or '—',
         'Email',        patient['email'] or '—'],
        ['Diabetes Since', patient['diabetes_duration'] or '—',
         'Eye Examined',   analysis['eye_side'] + ' Eye'],
        ['Analysis Date', datetime.fromisoformat(analysis['analyzed_at']).strftime('%d %b %Y %H:%M'),
         'Analysis ID',   f"#{analysis['id']:05d}"],
    ]

    def make_row(r):
        return [
            Paragraph(r[0], s['label']), Paragraph(str(r[1]), s['value']),
            Paragraph(r[2], s['label']), Paragraph(str(r[3]), s['value']),
        ]

    table_data = [make_row(r) for r in rows]
    t = Table(table_data, colWidths=[38*mm, 55*mm, 38*mm, 49*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('BACKGROUND', (2, 0), (2, -1), LIGHT_GRAY),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
        ('ROUNDEDCORNERS', [3]),
    ]))
    return t


def _severity_banner(level, label, confidence):
    sev_color = SEVERITY_COLOR_MAP.get(level, DANGER)
    s = _styles()
    data = [[
        Paragraph(label.upper(), s['severity']),
        Paragraph(f"Confidence: {confidence:.1f}%", s['severity_sub']),
    ]]
    t = Table(data, colWidths=[100*mm, 80*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), sev_color),
        ('TOPPADDING',    (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def _probability_table(probabilities):
    s = _styles()
    label_style = ParagraphStyle('pl', fontName='Helvetica', fontSize=9, textColor=DARK)
    rows = [['Grade', 'Class', 'Probability', 'Bar']]
    grade_map = {'No DR': 0, 'Mild DR': 1, 'Moderate DR': 2,
                 'Severe DR': 3, 'Proliferative DR': 4}
    bar_colors = [SUCCESS, colors.HexColor('#0EA5E9'), WARNING,
                  colors.HexColor('#EA580C'), DANGER]

    for cls_name, pct in probabilities.items():
        grade = grade_map.get(cls_name, 0)
        bar_width = max(int(pct * 0.8), 1)  # max ~80mm
        bar = Table([['']], colWidths=[bar_width * mm], rowHeights=[5*mm])
        bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bar_colors[grade]),
        ]))
        rows.append([
            Paragraph(f"Grade {grade}", label_style),
            Paragraph(cls_name, label_style),
            Paragraph(f"{pct:.2f}%", label_style),
            bar,
        ])

    t = Table(rows, colWidths=[22*mm, 45*mm, 22*mm, 91*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR',  (0, 0), (-1, 0), WHITE),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 9),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def generate_pdf_report(output_path, patient, analysis, doctor, probabilities, single_page=True):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=10*mm,  bottomMargin=15*mm,
    )
    s = _styles()
    story = []

    # ── Header ──────────────────────────────
    story.append(_header_table(doctor))
    story.append(Spacer(1, 5*mm))

    # ── Patient Information ──────────────────
    story.append(Paragraph('PATIENT INFORMATION', s['section']))
    story.append(_patient_info_table(patient, analysis))
    story.append(Spacer(1, 4*mm))

    # ── Diagnosis Result ─────────────────────
    story.append(Paragraph('DIAGNOSIS RESULT', s['section']))
    story.append(_severity_banner(
        analysis['severity_level'], analysis['severity_label'], analysis['confidence']
    ))
    story.append(Spacer(1, 4*mm))

    # ── Images ───────────────────────────────
    # For single-page output, use smaller thumbnails to avoid overflow
    img_path = os.path.join('uploads', analysis['image_filename'])
    gcam_path = (os.path.join('uploads', analysis['gradcam_filename'])
                 if analysis['gradcam_filename'] else None)

    if os.path.exists(img_path) or (gcam_path and os.path.exists(gcam_path)):
        cols = []
        # choose compact sizes when single_page requested
        img_w = 70*mm if single_page else 80*mm
        img_h = 70*mm if single_page else 80*mm
        if os.path.exists(img_path):
            cols.append(Table([[Paragraph('Original Retinal Image', s['label'])],
                               [RLImage(img_path, width=img_w, height=img_h, kind='proportional')]], colWidths=[90*mm]))
        if gcam_path and os.path.exists(gcam_path):
            cols.append(Table([[Paragraph('Grad-CAM Activation Map', s['label'])],
                               [RLImage(gcam_path, width=img_w, height=img_h, kind='proportional')]], colWidths=[90*mm]))
        # ensure two columns for layout
        if len(cols) < 2:
            cols.append(Paragraph('', s['body']))
        img_table = Table([cols], colWidths=[90*mm, 90*mm])
        img_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(img_table)
        story.append(Spacer(1, 3*mm))

    # ── Probability Distribution ─────────────
    story.append(Paragraph('SEVERITY CLASS PROBABILITIES', s['section']))
    story.append(_probability_table(probabilities))
    story.append(Spacer(1, 4*mm))

    # ── Clinical Recommendation ──────────────
    story.append(Paragraph('CLINICAL RECOMMENDATION', s['section']))
    rec_text = analysis.get('recommendation', '') or analysis.get('recommendations', '') or ''
    # Truncate recommendations when producing a single-page report
    if single_page:
        # take first 3 sentences
        rec_parts = rec_text.replace('\n', ' ').split('. ')
        rec_text = '. '.join(rec_parts[:3]).rstrip('.') + ('.' if rec_parts else '')
    rec_lines = rec_text.split('. ')
    for line in rec_lines:
        if line.strip():
            story.append(Paragraph('• ' + line.strip().rstrip('.') + '.', s['rec']))
    story.append(Spacer(1, 4*mm))

    # For single-page output, omit extended medical history and notes to keep report compact.
    if not single_page:
        if patient.get('medical_history'):
            story.append(Paragraph('MEDICAL HISTORY & NOTES', s['section']))
            story.append(Paragraph(patient['medical_history'], s['body']))
            story.append(Spacer(1, 3*mm))

        if analysis.get('notes'):
            story.append(Paragraph('PHYSICIAN NOTES', s['section']))
            story.append(Paragraph(analysis['notes'], s['body']))
            story.append(Spacer(1, 3*mm))

        # ── Disclaimer ───────────────────────────
        story.append(HRFlowable(width='100%', thickness=0.5, color=MID_GRAY, spaceAfter=4))
        disclaimer = (
            "<b>DISCLAIMER:</b> This report is generated by an AI-assisted diagnostic tool intended "
            "to support clinical decision-making. It does not replace the professional judgment of a "
            "licensed ophthalmologist or retinal specialist. All findings must be reviewed and confirmed "
            "by a qualified medical professional before any treatment decisions are made."
        )
        story.append(Paragraph(disclaimer, s['small']))
    else:
        # compact footer for single page
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph('This report is AI-assisted and intended for clinical support only.', s['small']))

    doc.build(story)
    print(f"[Report] Generated: {output_path}")
    return output_path

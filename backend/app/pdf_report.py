from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from backend.app.models import Case

def generate_case_pdf_report(case: Case, output_pdf_path: str) -> str:
    """Generates an official downloadable PDF audit report for a MediShield case."""
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#0f172a") # Slate dark
    accent_color = colors.HexColor("#2563eb") # Royal blue
    status_color = colors.HexColor("#16a34a") if case.status == "APPROVE" else (colors.HexColor("#dc2626") if case.status == "REJECT" else colors.HexColor("#d97706"))

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=primary_color,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=accent_color,
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1e293b")
    )

    story = []

    # Header Title
    story.append(Paragraph("MediShield Health Insurance Ltd.", title_style))
    story.append(Paragraph(f"Official Claims Processing Audit Report — Case ID: {case.case_id}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=15))

    # Case Overview Grid
    overview_data = [
        [Paragraph("<b>Patient Name:</b>", body_style), Paragraph(case.patient_name or "N/A", body_style),
         Paragraph("<b>Submission Date:</b>", body_style), Paragraph(case.created_at, body_style)],
        [Paragraph("<b>Policy Number:</b>", body_style), Paragraph(case.policy_number or "N/A", body_style),
         Paragraph("<b>Document Type:</b>", body_style), Paragraph(case.doc_type.value, body_style)],
        [Paragraph("<b>Final Decision:</b>", body_style), 
         Paragraph(f"<font color='{status_color.hexval()}'><b>{case.status.value}</b></font>", body_style),
         Paragraph("<b>Confidence Score:</b>", body_style), 
         Paragraph(f"<b>{int((case.orchestrator_result.confidence if case.orchestrator_result else 0.9)*100)}%</b>", body_style)]
    ]

    t_overview = Table(overview_data, colWidths=[110, 160, 110, 160])
    t_overview.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_overview)
    story.append(Spacer(1, 15))

    # Agent Breakdown Section
    story.append(Paragraph("Multi-Agent Analysis Breakdown", heading_style))

    if case.orchestrator_result:
        story.append(Paragraph(f"<b>Orchestrator Justification:</b>", body_style))
        story.append(Paragraph(case.orchestrator_result.justification.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 10))

    # Agent Findings Summary Table
    agent_table_data = [
        [Paragraph("<b>Agent</b>", body_style), Paragraph("<b>Status / Metrics</b>", body_style), Paragraph("<b>Key Output Summary</b>", body_style)]
    ]

    if case.classifier_result:
        agent_table_data.append([
            Paragraph("Classifier Agent", body_style),
            Paragraph(f"Confidence: {int(case.classifier_result.confidence*100)}%", body_style),
            Paragraph(case.classifier_result.reasoning, body_style)
        ])

    if case.kyc_result:
        agent_table_data.append([
            Paragraph("KYC Identity Agent", body_style),
            Paragraph(f"Passed: {case.kyc_result.kyc_passed}<br/>ELA Score: {case.kyc_result.ela_tamper_score:.2f}", body_style),
            Paragraph(f"Flags: {', '.join(case.kyc_result.flags) if case.kyc_result.flags else 'None'}", body_style)
        ])

    if case.claims_result:
        agent_table_data.append([
            Paragraph("Claims Extraction Agent", body_style),
            Paragraph(f"Schema Valid: {case.claims_result.schema_valid}", body_style),
            Paragraph(f"Amount: ${case.claims_result.extracted_fields.claim_amount or 0:,.2f}<br/>CPT: {', '.join(case.claims_result.extracted_fields.cpt_codes)}", body_style)
        ])

    if case.policy_result:
        agent_table_data.append([
            Paragraph("Policy RAG Agent", body_style),
            Paragraph(f"Covered: {case.policy_result.covered} ({case.policy_result.coverage_percentage:.0f}%)", body_style),
            Paragraph(f"Plan: {case.policy_result.policy_plan}<br/>Exclusions: {', '.join(case.policy_result.exclusions) if case.policy_result.exclusions else 'None'}", body_style)
        ])

    if case.fraud_result:
        agent_table_data.append([
            Paragraph("Fraud Detection Agent", body_style),
            Paragraph(f"Risk: {case.fraud_result.risk_level.value}<br/>Score: {case.fraud_result.fraud_score:.2f}", body_style),
            Paragraph(f"Anomalies: {'; '.join(case.fraud_result.anomalies) if case.fraud_result.anomalies else 'None'}", body_style)
        ])

    t_agents = Table(agent_table_data, colWidths=[120, 130, 290])
    t_agents.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_agents)
    story.append(Spacer(1, 15))

    # Audit Trail Table
    story.append(Paragraph("System Execution Audit Log", heading_style))
    audit_data = [[Paragraph("<b>Timestamp</b>", body_style), Paragraph("<b>Agent / Action</b>", body_style), Paragraph("<b>Details</b>", body_style)]]
    
    for log in case.audit_trail:
        audit_data.append([
            Paragraph(log.timestamp, body_style),
            Paragraph(f"{log.agent} ({log.action})", body_style),
            Paragraph(log.details, body_style)
        ])

    t_audit = Table(audit_data, colWidths=[110, 130, 300])
    t_audit.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_audit)

    doc.build(story)
    return output_pdf_path

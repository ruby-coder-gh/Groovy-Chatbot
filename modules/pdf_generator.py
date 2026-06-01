"""
PDF report generator using ReportLab.
Produces a 4-section gap analysis report for ISO 27001 readiness assessment.
"""

import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, PageBreak, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_gap_report(
    company_name: str,
    domain_scores: dict,
    session_results: list[dict],
    control_map: dict,
    output_path: str,
    priority_matrix: dict | None = None,
) -> str:
    """
    Generates PDF at output_path.
    Sections:
      1. Cover: Company name, date, overall score
      2. Executive Summary: Table of 7 domains + scores
      3. Gap Analysis: Per-domain, list missed controls + descriptions + next steps
      4. Remediation Priority Matrix (if data available): 2x2 grid of gap priorities
      5. Full Response Log: Q&A transcript
    Returns output_path.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        title=f"ISO 27001 Readiness Report — {company_name}",
        author="ISO 27001 Self-Assessment Chatbot",
    )

    styles = getSampleStyleSheet()
    # Custom styles
    title_style = ParagraphStyle(
        "CoverTitle", parent=styles["Title"],
        fontSize=26, leading=32, alignment=TA_CENTER,
        spaceAfter=20,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle", parent=styles["Normal"],
        fontSize=14, alignment=TA_CENTER, spaceAfter=10,
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading1"],
        fontSize=18, spaceAfter=12, spaceBefore=20,
    )
    subheading_style = ParagraphStyle(
        "SubHeading", parent=styles["Heading2"],
        fontSize=14, spaceAfter=8, spaceBefore=14,
    )
    body_style = ParagraphStyle(
        "BodyText2", parent=styles["Normal"],
        fontSize=10, leading=14, spaceAfter=6,
    )
    gap_style = ParagraphStyle(
        "GapText", parent=styles["Normal"],
        fontSize=10, leading=14, leftIndent=20, spaceAfter=4,
    )
    small_style = ParagraphStyle(
        "SmallText", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=colors.grey,
    )

    # Calculate overall score
    scores_list = [v["score"] for v in domain_scores.values()]
    overall_score = round(sum(scores_list) / len(scores_list)) if scores_list else 0

    # Build story
    story = []

    # ===== SECTION 1: COVER PAGE =====
    story.append(Spacer(1, 80 * mm))
    story.append(Paragraph("ISO 27001:2022", title_style))
    story.append(Paragraph("Readiness Self-Assessment Report", title_style))
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph(f"<b>Company:</b> {company_name}", subtitle_style))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %B %Y')}", subtitle_style))
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph(f"<b>Overall Readiness: {overall_score}%</b>", subtitle_style))
    story.append(Spacer(1, 10 * mm))

    # Status indicator
    if overall_score >= 70:
        status_text = "🟢 Good — Your organization shows strong ISO 27001 readiness."
    elif overall_score >= 40:
        status_text = "🟡 Moderate — Several gaps identified. Priority improvements recommended."
    else:
        status_text = "🔴 Needs Improvement — Significant gaps exist across multiple domains."

    story.append(Paragraph(status_text, ParagraphStyle(
        "StatusLine", parent=styles["Normal"],
        fontSize=12, alignment=TA_CENTER, textColor=colors.HexColor("#555555"),
    )))
    story.append(PageBreak())

    # ===== SECTION 2: EXECUTIVE SUMMARY =====
    story.append(Paragraph("Executive Summary", heading_style))
    story.append(Paragraph(
        "The following table shows the readiness score for each of the 7 Annex A domains. "
        "Scores are calculated as the percentage of controls within each domain that are "
        "adequately addressed based on your responses.",
        body_style
    ))
    story.append(Spacer(1, 6 * mm))

    # Build score table
    table_data = [["Domain", "Score", "Status", "Coverage"]]
    for domain, info in domain_scores.items():
        score = info["score"]
        if score >= 70:
            status = "🟢"
        elif score >= 40:
            status = "🟡"
        else:
            status = "🔴"
        coverage = f"{info['matched']}/{info['total']}"
        table_data.append([domain, f"{score}%", status, coverage])

    col_widths = [120 * mm, 30 * mm, 20 * mm, 30 * mm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"<b>Overall Score: {overall_score}%</b>", body_style))
    story.append(PageBreak())

    # ===== SECTION 3: GAP ANALYSIS =====
    story.append(Paragraph("Gap Analysis by Domain", heading_style))
    story.append(Paragraph(
        "For each domain, controls that were not adequately addressed are listed below "
        "with their description and suggested next steps.",
        body_style
    ))
    story.append(Spacer(1, 4 * mm))

    for domain, info in domain_scores.items():
        gaps = info["gaps"]
        score = info["score"]

        # Domain header
        if score >= 70:
            status_icon = "🟢"
        elif score >= 40:
            status_icon = "🟡"
        else:
            status_icon = "🔴"

        story.append(Paragraph(
            f"{status_icon} <b>{domain}</b> — Score: {score}% ({info['matched']}/{info['total']} covered)",
            subheading_style
        ))

        if not gaps:
            story.append(Paragraph(
                "<i>✓ All controls in this domain are adequately addressed.</i>",
                body_style
            ))
        else:
            for gap_id in gaps:
                # Find the description from control_map
                desc = ""
                next_step = ""
                for q_id, q_data in control_map.items():
                    if q_data.get("domain") == domain:
                        ctrl_desc = q_data.get("descriptions", {})
                        if gap_id in ctrl_desc:
                            desc = ctrl_desc[gap_id]
                            break

                # Generate next step suggestion
                next_step = _generate_next_step(gap_id, domain)

                story.append(Paragraph(
                    f"<b>{gap_id}</b>",
                    gap_style
                ))
                if desc:
                    story.append(Paragraph(
                        f"<i>Description:</i> {desc}",
                        ParagraphStyle("DescText", parent=body_style, fontSize=9, leftIndent=30, spaceAfter=2)
                    ))
                story.append(Paragraph(
                    f"<i>Recommended Action:</i> {next_step}",
                    ParagraphStyle("ActionText", parent=body_style, fontSize=9, leftIndent=30, spaceAfter=8)
                ))

        story.append(Spacer(1, 3 * mm))

    # ===== SECTION 4: REMEDIATION PRIORITY MATRIX =====
    if priority_matrix:
        story.append(Paragraph("Remediation Priority Matrix", heading_style))
        story.append(Paragraph(
            "The following matrix classifies identified gap controls into four quadrants "
            "based on implementation effort and security impact. This helps prioritize "
            "remediation activities.",
            body_style
        ))
        story.append(Spacer(1, 4 * mm))

        quadrants = [
            ("fix_now", "Fix Now", "High impact, low effort", "#fee2e2"),
            ("plan_for_it", "Plan For It", "High impact, high effort", "#fef9c3"),
            ("quick_wins", "Quick Wins", "Low impact, low effort", "#dcfce7"),
            ("deprioritize", "Deprioritize", "Low impact, high effort", "#f3f4f6"),
        ]

        # Use a 2-column table layout for the matrix
        quadrant_labels = {
            "fix_now": "🔴 Fix Now — High impact, low effort",
            "plan_for_it": "🟡 Plan For It — High impact, high effort",
            "quick_wins": "🟢 Quick Wins — Low impact, low effort",
            "deprioritize": "⚪ Deprioritize — Low impact, high effort",
        }

        for q_key, q_title, q_subtitle, q_color in quadrants:
            items = priority_matrix.get(q_key, [])
            label = quadrant_labels.get(q_key, q_title)

            # Build cell content
            cell_lines = [f"<b>{label}</b>"]
            if items:
                for item in items:
                    cid = item.get("id", "")
                    label_text = item.get("label", "")
                    cell_lines.append(f"• <b>{cid}</b> — {label_text}")
            else:
                cell_lines.append("<i>None — good job!</i>")

            cell_html = "<br/>".join(cell_lines)

            story.append(Paragraph(
                cell_html,
                ParagraphStyle(
                    "MatrixCell", parent=body_style,
                    fontSize=9, leading=13,
                    backColor=colors.HexColor(q_color),
                    borderPadding=8,
                    spaceBefore=6, spaceAfter=6,
                )
            ))

        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(
            "<i>Quadrant definitions: Fix Now = high impact + low effort, "
            "Plan For It = high impact + high effort, Quick Wins = low impact + low effort, "
            "Deprioritize = low impact + high effort.</i>",
            small_style
        ))
        story.append(PageBreak())

    # ===== SECTION 5: FULL RESPONSE LOG =====
    story.append(Paragraph("Full Q&A Transcript", heading_style))
    story.append(Paragraph(
        "The complete list of all 30 questions and the responses provided during the assessment.",
        body_style
    ))
    story.append(Spacer(1, 4 * mm))

    for i, result in enumerate(session_results, 1):
        q_id = result["question_id"]
        q_text = result.get("question_text", "")
        answer = result.get("user_answer", "")
        matched = result.get("matched_controls", [])

        # Question
        story.append(Paragraph(
            f"<b>Q{i}. [{q_id}]</b> {q_text}",
            ParagraphStyle("QText", parent=body_style, fontSize=10, spaceBefore=8, spaceAfter=2)
        ))
        # Answer
        story.append(Paragraph(
            f"<i>Answer:</i> {answer}",
            ParagraphStyle("AText", parent=body_style, fontSize=9, leftIndent=15, textColor=colors.HexColor("#333333"), spaceAfter=2)
        ))
        # Matched controls
        if matched:
            controls_str = ", ".join(matched)
            story.append(Paragraph(
                f"<i>Matched Controls:</i> {controls_str}",
                ParagraphStyle("MText", parent=body_style, fontSize=9, leftIndent=15, textColor=colors.HexColor("#1a237e"), spaceAfter=6)
            ))
        else:
            story.append(Paragraph(
                "<i>Matched Controls:</i> None",
                ParagraphStyle("MText", parent=body_style, fontSize=9, leftIndent=15, textColor=colors.HexColor("#888888"), spaceAfter=6)
            ))

    # Build PDF
    doc.build(story)
    return output_path


def _generate_next_step(control_id: str, domain: str) -> str:
    """Generate a recommended next step for a given gap control ID."""
    next_steps = {
        "A.5.1": "Develop and approve a formal Information Security Policy. Ensure it is reviewed annually and communicated to all staff.",
        "A.5.2": "Define and document information security roles (e.g., CISO, security team). Assign responsibilities in job descriptions.",
        "A.5.8": "Establish a formal risk assessment process. Create a risk register and define risk treatment plans.",
        "A.5.9": "Implement an asset management system (e.g., CMDB) to maintain a current inventory of all information assets.",
        "A.5.10": "Identify data flows and implement encryption for sensitive data in transit and at rest.",
        "A.5.11": "Create a secure disposal policy. Use certified data destruction services for media and devices.",
        "A.5.12": "Implement an information classification scheme (labels: Confidential, Internal, Public). Train staff on handling each class.",
        "A.5.19": "Define security requirements for supplier contracts. Conduct risk assessments for critical vendors.",
        "A.5.20": "Establish a regular review process for supplier compliance with security requirements.",
        "A.5.24": "Develop and document an Incident Response Plan covering preparation, detection, containment, eradication, and recovery.",
        "A.5.25": "Assign incident response roles and ensure the team receives appropriate training.",
        "A.5.27": "Implement a security incident logging system. Ensure all incidents are documented with timestamps and evidence.",
        "A.5.28": "Establish a post-incident review process. Document lessons learned and update security controls accordingly.",
        "A.5.29": "Develop a Business Continuity Plan that covers IT systems and data recovery.",
        "A.5.30": "Schedule regular testing of business continuity plans (at least annually). Document test results.",
        "A.5.31": "Create a legal and compliance register. Monitor changes in data protection regulations (e.g., GDPR).",
        "A.5.34": "Implement privacy controls for personal data. Appoint a Data Protection Officer if required.",
        "A.5.35": "Create an internal audit programme. Conduct audits at planned intervals and track remediation.",
        "A.6.1": "Implement a formal background check process for all new hires, including criminal record and reference checks.",
        "A.6.2": "Ensure all employees sign confidentiality agreements as part of the onboarding process.",
        "A.6.3": "Develop a security awareness training programme including induction and annual refresher courses.",
        "A.6.5": "Create an offboarding checklist that ensures all access is revoked within 24 hours of termination.",
        "A.7.1": "Define physical security perimeters. Install access control systems (e.g., card readers, biometrics) for sensitive areas.",
        "A.7.2": "Implement secure entry controls, including visitor management and after-hours access restrictions.",
        "A.7.3": "Establish a visitor access policy. Require visitor registration, badges, and escorts to sensitive areas.",
        "A.7.7": "Adopt a clear desk policy requiring all sensitive documents to be locked away and screens locked when unattended.",
        "A.7.8": "Install environmental protections: fire suppression, UPS, climate control, and flood detection in equipment rooms.",
        "A.7.14": "Implement secure media disposal procedures including secure erase, physical destruction, and certificate of destruction.",
        "A.8.2": "Implement a process to promptly revoke or modify access when personnel change roles or leave the organization.",
        "A.8.3": "Conduct quarterly access rights reviews. Verify that user permissions align with current job requirements.",
        "A.8.5": "Implement multi-factor authentication (MFA) for email, VPN, admin accounts, and remote access.",
        "A.8.7": "Deploy endpoint protection (EDR/antivirus) on all devices. Ensure definitions are updated automatically.",
        "A.8.8": "Establish a patch management policy. Apply critical patches within 14 days and maintain a patch schedule.",
        "A.8.13": "Implement automated backup solutions. Test restore procedures at least quarterly.",
        "A.8.16": "Deploy network monitoring tools (SIEM/IDS/IPS) to detect and alert on unusual traffic patterns.",
        "A.8.20": "Implement network security controls including firewalls, network segmentation, and access control lists.",
        "A.8.21": "Deploy a Web Application Firewall (WAF) and implement security headers for web applications.",
        "A.8.24": "Enable full-disk encryption (e.g., BitLocker, FileVault) on all laptops and mobile devices.",
        "A.8.25": "Schedule regular penetration tests and vulnerability scans. Remediate findings based on severity.",
    }
    return next_steps.get(control_id, f"Review and address the requirements for control {control_id} in the {domain} domain.")

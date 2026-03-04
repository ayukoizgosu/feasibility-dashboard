from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def money(v: int) -> str:
    return f"${v:,.0f}"


def build_pdf(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Site Due Diligence Report (Sample)",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1", parent=styles["Heading1"], fontSize=18, leading=22))
    styles.add(ParagraphStyle(name="H2", parent=styles["Heading2"], fontSize=12, leading=15))
    styles.add(ParagraphStyle(name="BodyTight", parent=styles["BodyText"], fontSize=9.5, leading=13))

    story = []
    story.append(Paragraph("Site Due Diligence Report (Sample)", styles["H1"]))
    story.append(Paragraph("Prepared for: Antigravity Projects Pty Ltd", styles["BodyText"]))
    story.append(Paragraph(f"Date: {date.today().isoformat()}", styles["BodyText"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Executive Summary", styles["H2"]))
    story.append(
        Paragraph(
            "This sample report demonstrates a comprehensive due diligence pack for a townhouse development "
            "site in metropolitan Melbourne. The project is conditionally viable subject to planning risk "
            "controls, civil servicing confirmation, and conservative debt assumptions.",
            styles["BodyTight"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("Subject Property", styles["H2"]))
    subject = [
        ["Address", "123 Example Street, Doncaster East VIC 3109"],
        ["Site Area", "1,025 m² (title)"],
        ["Current Zone", "GRZ1 - General Residential Zone"],
        ["Proposed Scheme", "4 x 3-bed townhouses"],
        ["Assessed Highest & Best Use", "Low-rise townhouse infill"],
    ]
    t = Table(subject, colWidths=[45 * mm, 125 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2FF")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Planning and Statutory Review", styles["H2"]))
    planning_bullets = [
        "- Zone supports medium density housing (subject to local policy and design controls).",
        "- No absolute prohibition identified from preliminary overlay scan.",
        "- Likely permit triggers: demolition, multi-dwelling development, crossover/vehicle access changes.",
        "- Recommended: pre-application meeting with council and concept envelope test before contract becomes unconditional.",
    ]
    for b in planning_bullets:
        story.append(Paragraph(b, styles["BodyTight"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Infrastructure and Services", styles["H2"]))
    infra = [
        "- Confirm sewer depth/capacity and legal point of discharge before settlement.",
        "- Obtain electricity pit/pillar upgrade advice and lead-time estimate.",
        "- Validate stormwater outfall strategy and on-site detention requirements.",
        "- Confirm NBN and water authority augmentation contributions.",
    ]
    for b in infra:
        story.append(Paragraph(b, styles["BodyTight"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Risk Matrix", styles["H2"]))
    risk = [
        ["Risk Item", "Likelihood", "Impact", "Mitigation"],
        ["Planning delay / redesign", "Medium", "High", "Pre-app + compliant concept envelope"],
        ["Civil servicing constraints", "Medium", "High", "Early authority checks + contingency"],
        ["Construction escalation", "Medium", "Medium", "Fixed-price tender + value engineering"],
        ["Sales softening", "Medium", "High", "Conservative GRV + staged release"],
    ]
    rt = Table(risk, colWidths=[44 * mm, 25 * mm, 23 * mm, 78 * mm])
    rt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(rt)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Financial Feasibility Snapshot", styles["H2"]))
    acq = 1_160_000 + 63_800 + 3_000
    hard = 2_600 * 750
    soft = 45_000 + 25_000 + int((hard + 45_000 + 25_000) * 0.05)
    fin_sell = 220_000
    total_cost = acq + hard + soft + fin_sell
    grv = 4_560_000
    profit = grv - total_cost
    margin = profit / total_cost * 100
    feas = [
        ["Metric", "Amount"],
        ["Gross Realisation Value (GRV)", money(grv)],
        ["Acquisition", money(acq)],
        ["Construction (Hard)", money(hard)],
        ["Soft Costs", money(soft)],
        ["Finance + Selling", money(fin_sell)],
        ["Total Development Cost", money(total_cost)],
        ["Net Profit (Before Tax)", money(profit)],
        ["Development Margin", f"{margin:.1f}%"],
    ]
    ft = Table(feas, colWidths=[90 * mm, 80 * mm])
    ft.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(ft)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Decision and Next Actions", styles["H2"]))
    actions = [
        "- Proceed to conditional offer only (planning and servicing conditions precedent).",
        "- Commission feature-survey, soil test, and concept architectural package.",
        "- Obtain civil servicing desk-top and authority advice letters.",
        "- Re-run feasibility at ±5% GRV and +10% construction sensitivity before finance application.",
    ]
    for b in actions:
        story.append(Paragraph(b, styles["BodyTight"]))
    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "Appendix note: This is a sample report format for stakeholder communication and does not "
            "replace statutory, legal, valuation, or engineering advice.",
            styles["BodyTight"],
        )
    )

    doc.build(story)


if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "examples" / "sample_due_diligence_report.pdf"
    build_pdf(output)
    print(output)

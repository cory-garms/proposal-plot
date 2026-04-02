"""
Convert a draft's markdown-style content to a PDF in memory using ReportLab.

Handles:
  ## Section Title  -> bold large heading
  ### Sub-title     -> bold medium heading
  - bullet item     -> indented bullet paragraph
  blank line        -> vertical spacer
  everything else   -> normal body paragraph
"""
import io
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable
)


def _build_styles():
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DraftTitle",
        parent=base["Title"],
        fontSize=16,
        leading=20,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "DraftMeta",
        parent=base["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#666666"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "DraftH1",
        parent=base["Heading1"],
        fontSize=13,
        leading=16,
        spaceBefore=14,
        spaceAfter=4,
        textColor=colors.HexColor("#1a1a2e"),
    )
    h2_style = ParagraphStyle(
        "DraftH2",
        parent=base["Heading2"],
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=3,
        textColor=colors.HexColor("#16213e"),
    )
    body_style = ParagraphStyle(
        "DraftBody",
        parent=base["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "DraftBullet",
        parent=base["Normal"],
        fontSize=10,
        leading=14,
        leftIndent=18,
        bulletIndent=6,
        spaceAfter=3,
        bulletText="\u2022",
    )
    return title_style, meta_style, h1_style, h2_style, body_style, bullet_style


def build_pdf(title: str, agency: str, content: str) -> bytes:
    """
    Build a PDF document and return its bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=1.25 * inch,
        rightMargin=1.25 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        title=title,
    )

    title_s, meta_s, h1_s, h2_s, body_s, bullet_s = _build_styles()

    story = [
        Paragraph(_escape(title), title_s),
        Paragraph(f"Agency: {_escape(agency)}", meta_s),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")),
        Spacer(1, 10),
    ]

    prev_empty = False
    for line in content.splitlines():
        stripped = line.rstrip()

        if stripped.startswith("## "):
            prev_empty = False
            story.append(Paragraph(_escape(stripped[3:].strip()), h1_s))
        elif stripped.startswith("### "):
            prev_empty = False
            story.append(Paragraph(_escape(stripped[4:].strip()), h2_s))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            prev_empty = False
            story.append(Paragraph(_escape(stripped[2:].strip()), bullet_s))
        elif stripped == "":
            if not prev_empty:
                story.append(Spacer(1, 6))
            prev_empty = True
        else:
            prev_empty = False
            story.append(Paragraph(_escape(stripped), body_s))

    doc.build(story)
    return buf.getvalue()


def _escape(text: str) -> str:
    """Escape characters that break ReportLab's XML parser."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )

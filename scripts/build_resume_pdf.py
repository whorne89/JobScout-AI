"""
build_resume_pdf.py — Generate a formatted 2-page PDF resume using reportlab.

Reads a JSON content file with all resume sections and produces a professionally
formatted PDF matching the JobScout resume template.

Features:
- Adaptive spacing system with continuous interpolation between anchor points
- Binary search fit loop to target exactly 2 pages with >=85% page 2 fill
- Last-resort content trimming for overflow

Usage:
    python scripts/build_resume_pdf.py content.json --output resumes/William_Horne_SE_Ramp.pdf
    python scripts/build_resume_pdf.py content.json  # auto-names from content

Input JSON schema:
{
    "variant": "SE" or "SC",
    "company": "Ramp",
    "name": "William Horne",
    "email": "whorne89@gmail.com",
    "linkedin": "www.linkedin.com/in/williamahorne",
    "location": "Jersey City, NJ",
    "phone": "(908)-419-5628",
    "summary": "...",
    "achievements": [
        {"lead": "Sales Enablement Innovation", "text": "Built CEO-mandated..."},
        ...
    ],
    "skills": [
        {"lead": "Sales Engineering", "text": "Technical Demonstrations • POC Delivery • ..."},
        ...
    ],
    "tech_proficiencies": [
        {"lead": "AI & Automation", "text": "ChatGPT (Custom GPTs) • Claude..."},
        ...
    ],
    "experience": [
        {
            "title": "Product & Business Consultant",
            "company": "iObeya",
            "location": "New York, NY",
            "dates": "March 2025 - Present",
            "bullets": ["Lead technical discovery...", ...]
        },
        ...
    ],
    "additional_experience": [
        {
            "title": "Project Manager",
            "company": "Diversified",
            "location": "Kenilworth, NJ",
            "dates": "June 2019 - July 2022",
            "bullets": ["Managed concurrent portfolio...", ...]
        },
        ...
    ],
    "education": {
        "degree": "Bachelor of Science in Marketing",
        "date": "May 2014",
        "school": "Rutgers University, Rutgers Business School, Newark, NJ"
    },
    "interests": "Automotive Enthusiast, PC Building, ..."
}
"""

import argparse
import json
import math
import os
import re
import sys

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, pica
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import LayoutError

# ─── Colors ──────────────────────────────────────────────────────────────────
ACCENT = HexColor("#1F4E79")
BLACK = HexColor("#000000")
GRAY = HexColor("#404040")
LGRAY = HexColor("#666666")
WHITE = HexColor("#FFFFFF")

# ─── Font Registration ───────────────────────────────────────────────────────
# Arial is available on Windows. Reportlab uses it by name.
FONT_NAME = "Helvetica"  # Reportlab's built-in, visually similar to Arial
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_BOLD_ITALIC = "Helvetica-BoldOblique"

# Try to register Arial if available on system
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Windows font paths
    WINDOWS_FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    arial_path = os.path.join(WINDOWS_FONTS, "arial.ttf")
    arial_bold_path = os.path.join(WINDOWS_FONTS, "arialbd.ttf")
    arial_italic_path = os.path.join(WINDOWS_FONTS, "ariali.ttf")
    arial_bi_path = os.path.join(WINDOWS_FONTS, "arialbi.ttf")

    if os.path.exists(arial_path):
        pdfmetrics.registerFont(TTFont("Arial", arial_path))
        pdfmetrics.registerFont(TTFont("Arial-Bold", arial_bold_path))
        pdfmetrics.registerFont(TTFont("Arial-Italic", arial_italic_path))
        pdfmetrics.registerFont(TTFont("Arial-BoldItalic", arial_bi_path))

        from reportlab.pdfbase.pdfmetrics import registerFontFamily

        registerFontFamily(
            "Arial",
            normal="Arial",
            bold="Arial-Bold",
            italic="Arial-Italic",
            boldItalic="Arial-BoldItalic",
        )
        FONT_NAME = "Arial"
        FONT_BOLD = "Arial-Bold"
        FONT_ITALIC = "Arial-Italic"
        FONT_BOLD_ITALIC = "Arial-BoldItalic"
except Exception:
    pass  # Fall back to Helvetica


# ─── Adaptive Spacing System ─────────────────────────────────────────────────

# Anchor points: level -> parameter values
# Parameters: bullet_before, bullet_after (pts), section_before (pts),
#             section_after (pts), job_spacer_pct, line_spacing,
#             body_font (pts), margin (inches)
ANCHORS = {
    -2: {
        "bullet_before": 0.5,
        "bullet_after": 0.5,
        "section_before": 2,
        "section_after": 1,
        "job_spacer_pct": 0.6,
        "line_spacing": 1.0,
        "body_font": 8.5,
        "margin": 0.5,
    },
    -1: {
        "bullet_before": 0.75,
        "bullet_after": 0.75,
        "section_before": 3,
        "section_after": 1.5,
        "job_spacer_pct": 0.8,
        "line_spacing": 1.0,
        "body_font": 9,
        "margin": 0.55,
    },
    0: {
        "bullet_before": 1.0,
        "bullet_after": 1.0,
        "section_before": 4,
        "section_after": 2,
        "job_spacer_pct": 1.0,
        "line_spacing": 1.0,
        "body_font": 9,
        "margin": 0.6,
    },
    1: {
        "bullet_before": 2.0,
        "bullet_after": 2.0,
        "section_before": 6,
        "section_after": 3,
        "job_spacer_pct": 1.4,
        "line_spacing": 1.05,
        "body_font": 9,
        "margin": 0.65,
    },
    2: {
        "bullet_before": 3.0,
        "bullet_after": 3.0,
        "section_before": 8,
        "section_after": 4,
        "job_spacer_pct": 1.8,
        "line_spacing": 1.1,
        "body_font": 9.5,
        "margin": 0.7,
    },
    3: {
        "bullet_before": 4.0,
        "bullet_after": 4.0,
        "section_before": 10,
        "section_after": 5,
        "job_spacer_pct": 2.2,
        "line_spacing": 1.15,
        "body_font": 10,
        "margin": 0.75,
    },
    4: {
        "bullet_before": 5.0,
        "bullet_after": 5.0,
        "section_before": 12,
        "section_after": 6,
        "job_spacer_pct": 2.6,
        "line_spacing": 1.22,
        "body_font": 10,
        "margin": 0.8,
    },
    5: {
        "bullet_before": 6.5,
        "bullet_after": 6.5,
        "section_before": 14,
        "section_after": 7,
        "job_spacer_pct": 3.0,
        "line_spacing": 1.3,
        "body_font": 10.5,
        "margin": 0.85,
    },
}


def get_spacing_params(level):
    """Get interpolated spacing parameters for a given level (float)."""
    level = max(-2, min(5, level))
    anchor_keys = sorted(ANCHORS.keys())

    # Find bounding anchors
    lo_key = anchor_keys[0]
    hi_key = anchor_keys[-1]
    for i, k in enumerate(anchor_keys):
        if k <= level:
            lo_key = k
        if k >= level and (i == 0 or anchor_keys[i - 1] < level):
            hi_key = k
            if lo_key == hi_key and i > 0 and level < k:
                lo_key = anchor_keys[i - 1]
            break

    if lo_key == hi_key:
        return dict(ANCHORS[lo_key])

    fraction = (level - lo_key) / (hi_key - lo_key)
    lo_vals = ANCHORS[lo_key]
    hi_vals = ANCHORS[hi_key]

    result = {}
    for param in lo_vals:
        lo_v = lo_vals[param]
        hi_v = hi_vals[param]
        val = lo_v + (hi_v - lo_v) * fraction
        # Round appropriately
        if param in ("body_font", "margin"):
            val = round(val, 2)
        elif param in ("line_spacing", "job_spacer_pct"):
            val = round(val, 3)
        else:
            val = round(val, 1)
        result[param] = val
    return result


# ─── Style Factory ───────────────────────────────────────────────────────────


def make_styles(sp):
    """Create paragraph styles from spacing parameters."""
    body_size = sp["body_font"]
    leading = body_size * sp["line_spacing"] * 1.2

    styles = {}

    styles["Name"] = ParagraphStyle(
        "Name",
        fontName=FONT_BOLD,
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        textColor=BLACK,
        spaceAfter=0,
    )

    styles["Contact"] = ParagraphStyle(
        "Contact",
        fontName=FONT_NAME,
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=LGRAY,
        spaceAfter=2,
    )

    styles["Summary"] = ParagraphStyle(
        "Summary",
        fontName=FONT_NAME,
        fontSize=body_size,
        leading=leading,
        alignment=TA_LEFT,
        textColor=GRAY,
        spaceBefore=sp["section_after"],
        spaceAfter=0,
    )

    styles["SectionHeader"] = ParagraphStyle(
        "SectionHeader",
        fontName=FONT_BOLD,
        fontSize=10,
        leading=12,
        alignment=TA_LEFT,
        textColor=ACCENT,
        spaceBefore=sp["section_before"],
        spaceAfter=0,
    )

    styles["Bullet"] = ParagraphStyle(
        "Bullet",
        fontName=FONT_NAME,
        fontSize=body_size,
        leading=leading,
        alignment=TA_LEFT,
        textColor=GRAY,
        leftIndent=18,
        firstLineIndent=-12,
        spaceBefore=sp["bullet_before"],
        spaceAfter=sp["bullet_after"],
        bulletFontName=FONT_NAME,
        bulletFontSize=body_size,
    )

    styles["JobTitle"] = ParagraphStyle(
        "JobTitle",
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=13,
        alignment=TA_LEFT,
        textColor=BLACK,
    )

    styles["JobDates"] = ParagraphStyle(
        "JobDates",
        fontName=FONT_ITALIC,
        fontSize=9,
        leading=11,
        alignment=TA_RIGHT,
        textColor=LGRAY,
    )

    styles["Education"] = ParagraphStyle(
        "Education",
        fontName=FONT_NAME,
        fontSize=body_size,
        leading=leading,
        alignment=TA_LEFT,
        textColor=GRAY,
        leftIndent=18,
    )

    styles["Interests"] = ParagraphStyle(
        "Interests",
        fontName=FONT_NAME,
        fontSize=body_size,
        leading=leading,
        alignment=TA_LEFT,
        textColor=LGRAY,
    )

    return styles


# ─── Document Building ───────────────────────────────────────────────────────


def escape_xml(text):
    """Escape text for use in reportlab Paragraph XML markup."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def format_bold_lead_bullet(lead, text, styles):
    """Format a bullet with bold lead phrase."""
    lead_esc = escape_xml(lead)
    text_esc = escape_xml(text)
    body_color = GRAY.hexval()[2:]  # strip '0x' prefix
    xml = (
        f'<font name="{FONT_NAME}" color="#000000">\u2022 </font>'
        f'<font name="{FONT_BOLD}" color="#000000">{lead_esc}:</font> '
        f'<font color="#{body_color}">{text_esc}</font>'
    )
    return Paragraph(xml, styles["Bullet"])


def format_plain_bullet(text, styles):
    """Format a plain bullet point."""
    text_esc = escape_xml(text)
    body_color = GRAY.hexval()[2:]
    xml = (
        f'<font name="{FONT_NAME}" color="#000000">\u2022 </font>'
        f'<font color="#{body_color}">{text_esc}</font>'
    )
    return Paragraph(xml, styles["Bullet"])


def build_section_header(title, sp, styles):
    """Build a section header with thin rule below."""
    elements = []
    header_text = title.upper()
    elements.append(Paragraph(header_text, styles["SectionHeader"]))
    elements.append(Spacer(1, sp["section_after"]))
    elements.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=ACCENT,
            spaceBefore=0,
            spaceAfter=sp["section_after"],
        )
    )
    return elements


def build_job_header(job, sp, styles, content_width):
    """Build a two-column job header: Title|Company|Location left, Dates right."""
    # Left side: Title | Company, Location
    company_color = ACCENT.hexval()[2:]
    loc_color = LGRAY.hexval()[2:]

    title_esc = escape_xml(job["title"])
    company_esc = escape_xml(job["company"])
    location_esc = escape_xml(job.get("location", ""))

    left_xml = (
        f'<font name="{FONT_BOLD}" size="10.5" color="#000000">{title_esc}</font>'
        f' <font name="{FONT_NAME}" size="9" color="#{loc_color}">|</font> '
        f'<font name="{FONT_BOLD}" size="10" color="#{company_color}">{company_esc}</font>'
    )
    if location_esc:
        left_xml += (
            f'<font name="{FONT_NAME}" size="9" color="#{loc_color}">, </font>'
            f'<font name="{FONT_ITALIC}" size="9" color="#{loc_color}">{location_esc}</font>'
        )

    left_style = ParagraphStyle(
        "JobLeft", fontName=FONT_NAME, fontSize=10.5, leading=13, alignment=TA_LEFT
    )
    right_style = ParagraphStyle(
        "JobRight",
        fontName=FONT_ITALIC,
        fontSize=9,
        leading=11,
        alignment=TA_RIGHT,
        textColor=LGRAY,
    )

    left_para = Paragraph(left_xml, left_style)
    right_para = Paragraph(escape_xml(job.get("dates", "")), right_style)

    # 75/25 split
    col1_w = content_width * 0.75
    col2_w = content_width * 0.25

    table = Table(
        [[left_para, right_para]],
        colWidths=[col1_w, col2_w],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def build_story(content, sp, styles, page_width, margin):
    """Build the full document story (list of flowables)."""
    content_width = page_width - 2 * margin
    story = []

    # ── Name ──
    story.append(Paragraph(escape_xml(content["name"]), styles["Name"]))

    # ── Contact Line ──
    contact_parts = [
        content.get("email", ""),
        content.get("linkedin", ""),
        content.get("location", ""),
        content.get("phone", ""),
    ]
    contact_line = " | ".join(p for p in contact_parts if p)
    story.append(Paragraph(escape_xml(contact_line), styles["Contact"]))

    # ── Thick Navy Rule ──
    story.append(Spacer(1, 2))
    story.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=ACCENT,
            spaceBefore=0,
            spaceAfter=4,
        )
    )

    # ── Summary ──
    story.append(Paragraph(escape_xml(content["summary"]), styles["Summary"]))

    # ── Selected Achievements ──
    story.extend(build_section_header("SELECTED ACHIEVEMENTS", sp, styles))
    for ach in content.get("achievements", []):
        if isinstance(ach, dict):
            story.append(format_bold_lead_bullet(ach["lead"], ach["text"], styles))
        else:
            story.append(format_plain_bullet(str(ach), styles))

    # ── Skills & Expertise ──
    story.extend(build_section_header("SKILLS & EXPERTISE", sp, styles))
    for skill in content.get("skills", []):
        if isinstance(skill, dict):
            story.append(format_bold_lead_bullet(skill["lead"], skill["text"], styles))
        else:
            story.append(format_plain_bullet(str(skill), styles))

    # ── Technical Proficiencies ──
    story.extend(build_section_header("TECHNICAL PROFICIENCIES", sp, styles))
    for tech in content.get("tech_proficiencies", []):
        if isinstance(tech, dict):
            story.append(format_bold_lead_bullet(tech["lead"], tech["text"], styles))
        else:
            story.append(format_plain_bullet(str(tech), styles))

    # ── Professional Experience ──
    story.extend(build_section_header("PROFESSIONAL EXPERIENCE", sp, styles))
    for i, job in enumerate(content.get("experience", [])):
        if i > 0:
            # Job spacer
            spacer_pts = 6 * sp["job_spacer_pct"]
            story.append(Spacer(1, spacer_pts))
        story.append(build_job_header(job, sp, styles, content_width))
        story.append(Spacer(1, sp["bullet_before"]))
        for bullet in job.get("bullets", []):
            story.append(format_plain_bullet(bullet, styles))

    # ── Additional Experience (PROFESSIONAL EXPERIENCE CONT'D) ──
    if content.get("additional_experience"):
        story.extend(
            build_section_header("PROFESSIONAL EXPERIENCE CONT'D", sp, styles)
        )
        for i, job in enumerate(content["additional_experience"]):
            if i > 0:
                spacer_pts = 6 * sp["job_spacer_pct"]
                story.append(Spacer(1, spacer_pts))
            story.append(build_job_header(job, sp, styles, content_width))
            story.append(Spacer(1, sp["bullet_before"]))
            for bullet in job.get("bullets", []):
                story.append(format_plain_bullet(bullet, styles))

    # ── Education ──
    story.extend(build_section_header("EDUCATION & CERTIFICATIONS", sp, styles))
    edu = content.get("education", {})
    if edu:
        degree = escape_xml(edu.get("degree", ""))
        date = escape_xml(edu.get("date", ""))
        school = escape_xml(edu.get("school", ""))
        edu_xml = f'<font name="{FONT_BOLD}">{degree}</font> | {date}'
        story.append(
            Paragraph(
                edu_xml,
                ParagraphStyle(
                    "EduDegree",
                    fontName=FONT_NAME,
                    fontSize=sp["body_font"],
                    leading=sp["body_font"] * 1.3,
                    leftIndent=18,
                    textColor=GRAY,
                ),
            )
        )
        story.append(
            Paragraph(
                school,
                ParagraphStyle(
                    "EduSchool",
                    fontName=FONT_NAME,
                    fontSize=sp["body_font"],
                    leading=sp["body_font"] * 1.3,
                    leftIndent=18,
                    textColor=LGRAY,
                ),
            )
        )

    # ── Interests ──
    story.extend(build_section_header("INTERESTS", sp, styles))
    interests_text = content.get("interests", "")
    if interests_text:
        story.append(Paragraph(escape_xml(interests_text), styles["Interests"]))

    return story


# ─── Page Measurement ────────────────────────────────────────────────────────


def measure_story(story, avail_width, avail_height_per_page):
    """Calculate total content height by wrapping all flowables.
    Returns (page_count, page2_fill_ratio)."""
    total_height = 0
    for flowable in story:
        w, h = flowable.wrap(avail_width, avail_height_per_page)
        total_height += h
        # Account for spaceBefore/spaceAfter on paragraphs
        if hasattr(flowable, "style"):
            style = flowable.style
            total_height += getattr(style, "spaceBefore", 0)
            total_height += getattr(style, "spaceAfter", 0)

    pages = max(1, math.ceil(total_height / avail_height_per_page))
    if pages >= 2:
        page2_used = total_height - avail_height_per_page
        page2_fill = min(page2_used / avail_height_per_page, 1.0)
    else:
        page2_fill = 0

    return pages, page2_fill


def build_pdf(content, output_path, level=0.0):
    """Build the PDF at a given spacing level. Returns (page_count, page2_fill)."""
    sp = get_spacing_params(level)
    styles = make_styles(sp)
    margin = sp["margin"] * inch
    page_width, page_height = letter
    avail_width = page_width - 2 * margin
    avail_height = page_height - 2 * margin

    story = build_story(content, sp, styles, page_width, margin)

    # Measure content to get page count and fill
    pages, page2_fill = measure_story(story, avail_width, avail_height)

    # Build the actual PDF
    from reportlab.platypus import SimpleDocTemplate

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    try:
        # Re-create story since wrap() may have mutated flowables
        story = build_story(content, sp, styles, page_width, margin)
        doc.build(story)
    except LayoutError:
        return (99, 0)

    return (pages, page2_fill)


# ─── Binary Search Fit Loop ──────────────────────────────────────────────────


def fit_to_pages(content, output_path, target_pages=2, max_iterations=10):
    """Binary search for the spacing level that produces exactly target_pages
    with page 2 >= 85% filled."""
    lo = -2.0
    hi = 5.0
    level = 0.0
    best = None  # (level, fill_ratio, abs_diff_from_target)

    for iteration in range(max_iterations):
        pages, fill = build_pdf(content, output_path, level)
        print(f"  Iteration {iteration + 1}: level={level:.2f} -> {pages} pages, page2 fill={fill:.1%}")

        if pages == target_pages and fill >= 0.85:
            print(f"  Converged! level={level:.2f}, fill={fill:.1%}")
            return level, pages, fill

        if pages == target_pages:
            # 2 pages but underfilled — record and try expanding
            diff = abs(fill - 0.85)
            if best is None or diff < best[2]:
                best = (level, fill, diff)
            lo = level
            level = (lo + hi) / 2

        elif pages > target_pages:
            # Overflow — compress
            hi = level
            level = (lo + hi) / 2

        elif pages < target_pages:
            # Underflow — expand
            lo = level
            level = min((lo + hi) / 2, lo + 2.0)

        if hi - lo < 0.05:
            print(f"  Search range exhausted (hi-lo={hi - lo:.3f})")
            break

    # Use best 2-page result if we have one
    if best:
        level, fill, _ = best
        print(f"  Using best result: level={level:.2f}, fill={fill:.1%}")
        build_pdf(content, output_path, level)
        return level, target_pages, fill

    # Last resort: try at lo
    pages, fill = build_pdf(content, output_path, lo)
    return lo, pages, fill


def try_trim_and_fit(content, output_path):
    """Last resort: trim one Additional Experience bullet and retry at level -2."""
    # Only trim from additional_experience, and only the least important bullets
    additional = content.get("additional_experience", [])
    for job in reversed(additional):
        bullets = job.get("bullets", [])
        if len(bullets) > 1:
            removed = bullets.pop()
            print(f"  TRIM: Removed bullet from {job['company']}: {removed[:60]}...")
            level, pages, fill = fit_to_pages(content, output_path)
            if pages == 2:
                return level, pages, fill
            # If still too long, trim another
    return None


# ─── Markdown Parser ─────────────────────────────────────────────────────────


def parse_markdown_resume(md_path):
    """Parse a base-resume markdown file into content JSON structure."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    content = {}
    lines = text.split("\n")
    i = 0

    # Parse header
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("# "):
            content["name"] = line[2:].strip()
            i += 1
            break
        i += 1

    # Parse contact line
    while i < len(lines):
        line = lines[i].strip()
        if line and not line.startswith("#"):
            parts = [p.strip() for p in line.split("|")]
            for p in parts:
                if "@" in p:
                    content["email"] = p
                elif "linkedin" in p.lower():
                    content["linkedin"] = p
                elif re.search(r"\(\d{3}\)", p):
                    content["phone"] = p
                elif "," in p and len(p) < 30:
                    content["location"] = p
            i += 1
            break
        i += 1

    # Parse sections
    current_section = None
    section_lines = []

    def flush_section():
        nonlocal current_section, section_lines
        if current_section:
            _process_section(content, current_section, section_lines)
        section_lines = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("## "):
            flush_section()
            current_section = stripped[3:].strip()
            i += 1
            continue

        if stripped.startswith("### "):
            # Job header within a section
            section_lines.append(line)
            i += 1
            continue

        section_lines.append(line)
        i += 1

    flush_section()
    return content


def _process_section(content, header, lines):
    """Process a section's lines into the content structure."""
    header_upper = header.upper()
    text = "\n".join(lines).strip()

    if "SUMMARY" in header_upper:
        content["summary"] = text

    elif "ACHIEVEMENT" in header_upper:
        content["achievements"] = _parse_bold_lead_bullets(lines)

    elif "SKILLS" in header_upper and "EXPERTISE" in header_upper:
        content["skills"] = _parse_bold_lead_bullets(lines)

    elif "PROFICIEN" in header_upper:
        content["tech_proficiencies"] = _parse_bold_lead_bullets(lines)

    elif "CONT" in header_upper and "EXPERIENCE" in header_upper:
        content["additional_experience"] = _parse_jobs(lines)

    elif "EXPERIENCE" in header_upper:
        content["experience"] = _parse_jobs(lines)

    elif "EDUCATION" in header_upper:
        content["education"] = _parse_education(lines)

    elif "INTEREST" in header_upper:
        content["interests"] = text


def _parse_bold_lead_bullets(lines):
    """Parse bullets with **Bold Lead:** text format."""
    bullets = []
    current = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                bullets.append(current)
                current = ""
            continue
        if stripped.startswith("- "):
            if current:
                bullets.append(current)
            current = stripped[2:]
        else:
            if current:
                current += " " + stripped
            else:
                current = stripped
    if current:
        bullets.append(current)

    result = []
    for b in bullets:
        # Match **Lead:** text pattern
        match = re.match(r"\*\*(.+?)\*\*\s*:?\s*(.*)", b, re.DOTALL)
        if match:
            lead = match.group(1).rstrip(":")
            text = match.group(2).strip()
            result.append({"lead": lead, "text": text})
        else:
            result.append({"lead": "", "text": b})
    return result


def _parse_jobs(lines):
    """Parse job entries from ### headers and bullet lists."""
    jobs = []
    current_job = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("### "):
            if current_job:
                jobs.append(current_job)
            # Parse: ### Title | Company | Location | Dates
            parts = [p.strip() for p in stripped[4:].split("|")]
            current_job = {
                "title": parts[0] if len(parts) > 0 else "",
                "company": parts[1] if len(parts) > 1 else "",
                "location": parts[2] if len(parts) > 2 else "",
                "dates": parts[3] if len(parts) > 3 else "",
                "bullets": [],
            }
        elif stripped.startswith("- ") and current_job is not None:
            current_job["bullets"].append(stripped[2:])
        elif stripped and current_job is not None and current_job["bullets"]:
            # Continuation of previous bullet
            current_job["bullets"][-1] += " " + stripped

    if current_job:
        jobs.append(current_job)
    return jobs


def _parse_education(lines):
    """Parse education section."""
    text = "\n".join(lines).strip()
    edu = {"degree": "", "date": "", "school": ""}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Match: **Degree** | Date
        match = re.match(r"\*\*(.+?)\*\*\s*\|\s*(.*)", stripped)
        if match:
            edu["degree"] = match.group(1).strip()
            edu["date"] = match.group(2).strip()
        elif "University" in stripped or "Rutgers" in stripped:
            edu["school"] = stripped
    return edu


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Build a formatted PDF resume")
    parser.add_argument(
        "input",
        help="Input JSON content file OR markdown base resume file (.md)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output PDF path (default: auto-generated from content)",
    )
    parser.add_argument(
        "--level", "-l",
        type=float,
        default=None,
        help="Fixed spacing level (-2 to +3). If omitted, uses adaptive fit loop.",
    )
    parser.add_argument(
        "--no-fit",
        action="store_true",
        help="Skip adaptive fit loop, build at level 0 (or --level value)",
    )
    args = parser.parse_args()

    # Load content
    input_path = args.input
    if input_path.endswith(".md"):
        print(f"Parsing markdown: {input_path}")
        content = parse_markdown_resume(input_path)
    elif input_path.endswith(".json"):
        print(f"Loading JSON: {input_path}")
        with open(input_path, "r", encoding="utf-8") as f:
            content = json.load(f)
    else:
        print(f"ERROR: Unsupported input format: {input_path}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        variant = content.get("variant", "SE")
        company = content.get("company", "Base")
        safe_company = re.sub(r"[^\w]", "_", company)
        output_path = f"resumes/William_Horne_{variant}_{safe_company}.pdf"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print(f"Building PDF: {output_path}")

    if args.no_fit or args.level is not None:
        level = args.level if args.level is not None else 0.0
        pages, fill = build_pdf(content, output_path, level)
        print(f"  Built at level {level:.2f}: {pages} pages, page2 fill={fill:.1%}")
    else:
        level, pages, fill = fit_to_pages(content, output_path)
        if pages != 2:
            print("  WARNING: Could not achieve 2 pages. Attempting content trim...")
            result = try_trim_and_fit(content, output_path)
            if result:
                level, pages, fill = result
            else:
                print("  ERROR: Could not fit to 2 pages even after trimming.")

    print(f"\nDone! Output: {output_path}")
    print(f"  Pages: {pages}, Level: {level:.2f}, Page 2 Fill: {fill:.1%}")
    return output_path


if __name__ == "__main__":
    main()

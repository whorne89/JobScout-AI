"""
extract_resume_pdf.py — Extract text from base resume PDFs and write structured markdown.

Reads PDF files from profile/ directory and outputs base-resume-SE.md and base-resume-SC.md.
Uses PyPDF2 for text extraction with manual structure detection.

Usage: python scripts/extract_resume_pdf.py
"""

import os
import re
import sys

try:
    from PyPDF2 import PdfReader
except ImportError:
    print("ERROR: PyPDF2 is required. Install with: pip install PyPDF2")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
PROFILE_DIR = os.path.join(PROJECT_DIR, "profile")

# Map PDF filenames to variant keys
PDF_VARIANTS = {
    "William Horne - Sales Engineer.pdf": "SE",
    "William Horne - Solutions Consultant.pdf": "SC",
}

# Section headers we expect to find (normalized to uppercase for matching)
SECTION_HEADERS = [
    "SELECTED ACHIEVEMENTS",
    "SKILLS & EXPERTISE",
    "TECHNICAL PROFICIENCIES",
    "PROFESSIONAL EXPERIENCE",
    "PROFESSIONAL EXPERIENCE CONT'D",
    "EDUCATION & CERTIFICATIONS",
    "EDUCATION",
    "INTERESTS",
    "PERSONAL INTERESTS",
]


def extract_pdf_text(pdf_path):
    """Extract all text from a PDF, page by page."""
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)


def parse_contact_line(lines):
    """Extract name and contact info from the first few lines."""
    name = ""
    contact_parts = []

    for line in lines[:5]:
        line = line.strip()
        if not line:
            continue
        # Name is usually the first substantial line
        if not name and not any(c in line for c in ["@", "www.", "linkedin"]):
            # Check if it looks like a name (short, no special chars except spaces)
            if len(line.split()) <= 4 and not any(c in line for c in ["•", "|", ":"]):
                name = line
                continue
        # Contact info contains email, linkedin, phone
        if "@" in line or "linkedin" in line or re.search(r"\(\d{3}\)", line):
            contact_parts.append(line)

    # Combine contact parts
    contact = " | ".join(contact_parts) if contact_parts else ""

    # Try to parse individual contact fields
    email = ""
    linkedin = ""
    location = ""
    phone = ""

    full_text = " ".join(contact_parts)
    # Email
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", full_text)
    if email_match:
        email = email_match.group()
    # LinkedIn
    li_match = re.search(r"(?:www\.)?linkedin\.com/in/\w+", full_text)
    if li_match:
        linkedin = li_match.group()
        if not linkedin.startswith("www."):
            linkedin = "www." + linkedin
    # Phone
    phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", full_text)
    if phone_match:
        phone = phone_match.group()
    # Location — typically "City, ST" pattern
    loc_match = re.search(r"([A-Z][a-z]+ [A-Z][a-z]+,\s*[A-Z]{2})", full_text)
    if not loc_match:
        loc_match = re.search(r"([A-Z][a-z]+,\s*[A-Z]{2})", full_text)
    if loc_match:
        location = loc_match.group()

    return name, email, linkedin, location, phone


def detect_sections(text):
    """Split text into sections based on known headers."""
    lines = text.split("\n")
    sections = []
    current_section = {"header": "HEADER", "lines": []}

    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()

        # Check if this line is a section header
        is_header = False
        for header in SECTION_HEADERS:
            if upper == header or upper.startswith(header):
                is_header = True
                # Save current section
                if current_section["lines"] or current_section["header"] != "HEADER":
                    sections.append(current_section)
                current_section = {"header": stripped, "lines": []}
                break

        if not is_header:
            current_section["lines"].append(line)

    # Don't forget last section
    if current_section["lines"]:
        sections.append(current_section)

    return sections


def is_bullet(line):
    """Check if a line starts with a bullet marker."""
    stripped = line.strip()
    return stripped.startswith(("● ", "• ", "- ", "✔ ", "✔️ ", "○ "))


def clean_bullet(line):
    """Remove bullet marker from line start."""
    stripped = line.strip()
    for prefix in ["● ", "• ", "- ", "✔ ", "✔️ ", "○ "]:
        if stripped.startswith(prefix):
            return stripped[len(prefix):]
    return stripped


def detect_bold_lead(text):
    """Detect and format bold lead phrases like 'Sales Engineering: ...'"""
    match = re.match(r"^([A-Z][\w\s&/]+(?:[\w&]))\s*[:]\s*(.+)", text)
    if match:
        lead = match.group(1).strip()
        rest = match.group(2).strip()
        return f"**{lead}:** {rest}"
    return text


def parse_job_entry(lines):
    """Parse a job entry: title, company, location, dates, bullets."""
    title = ""
    company = ""
    location = ""
    dates = ""
    bullets = []

    i = 0
    # First non-empty line(s) should be the job header
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if is_bullet(line):
            break

        # Try to parse job header line
        # Pattern: "Title | Date Range" or "Title | Company, Location  Date Range"
        # Or multi-line: "Title | Month Year - Month Year\nCompany, Location"
        if not title:
            # Check for "Title | Month Year" pattern
            date_match = re.search(
                r"[|]\s*((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\s*[-–]\s*(?:Present|\w+\s+\d{4}))",
                line,
            )
            if date_match:
                dates = date_match.group(1).strip()
                title = line[: date_match.start()].strip().rstrip("|").strip()
            else:
                title = line
        elif not company:
            # Second line might be "Company, Location"
            company_line = line
            # Check if dates are on this line
            date_match = re.search(
                r"((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\s*[-–]\s*(?:Present|\w+\s+\d{4}))",
                company_line,
            )
            if date_match:
                dates = date_match.group(1).strip()
                company_line = company_line[: date_match.start()].strip()

            # Split company and location
            parts = company_line.split(",")
            if len(parts) >= 2:
                company = parts[0].strip()
                location = ",".join(parts[1:]).strip()
            else:
                company = company_line.strip()
        i += 1

    # Collect bullets
    current_bullet = ""
    for line in lines[i:]:
        stripped = line.strip()
        if not stripped:
            if current_bullet:
                bullets.append(current_bullet)
                current_bullet = ""
            continue
        if is_bullet(stripped):
            if current_bullet:
                bullets.append(current_bullet)
            current_bullet = clean_bullet(stripped)
        else:
            # Continuation of previous bullet
            if current_bullet:
                current_bullet += " " + stripped
            else:
                current_bullet = stripped

    if current_bullet:
        bullets.append(current_bullet)

    return title, company, location, dates, bullets


def build_markdown(name, email, linkedin, location, phone, sections, variant):
    """Build structured markdown from parsed sections."""
    lines = []

    # Header
    lines.append(f"# {name}")
    lines.append("")
    contact = " | ".join(
        filter(None, [email, linkedin, location, phone])
    )
    lines.append(contact)
    lines.append("")

    for section in sections:
        header = section["header"]
        header_upper = header.upper()
        content_lines = section["lines"]

        # Skip the header section (already handled)
        if header == "HEADER":
            # Check if there's a summary paragraph in the header lines
            text = "\n".join(content_lines).strip()
            if text and len(text) > 100:
                # This is likely the summary
                lines.append("## SUMMARY")
                lines.append("")
                lines.append(text)
                lines.append("")
            continue

        # Normalize section header
        if "ACHIEVEMENT" in header_upper:
            lines.append("## SELECTED ACHIEVEMENTS")
        elif "SKILLS" in header_upper and "EXPERTISE" in header_upper:
            lines.append("## SKILLS & EXPERTISE")
        elif "TECHNICAL PROFICIEN" in header_upper:
            lines.append("## TECHNICAL PROFICIENCIES")
        elif "CONT" in header_upper and "EXPERIENCE" in header_upper:
            lines.append("## PROFESSIONAL EXPERIENCE CONT'D")
        elif "PROFESSIONAL EXPERIENCE" in header_upper:
            lines.append("## PROFESSIONAL EXPERIENCE")
        elif "EDUCATION" in header_upper:
            lines.append("## EDUCATION & CERTIFICATIONS")
        elif "INTEREST" in header_upper:
            lines.append("## INTERESTS")
        else:
            lines.append(f"## {header_upper}")
        lines.append("")

        # Parse content based on section type
        content_text = "\n".join(content_lines)

        if "ACHIEVEMENT" in header_upper:
            # Bullets with bold leads
            bullets = []
            current = ""
            for line in content_lines:
                stripped = line.strip()
                if not stripped:
                    if current:
                        bullets.append(current)
                        current = ""
                    continue
                if is_bullet(stripped):
                    if current:
                        bullets.append(current)
                    current = clean_bullet(stripped)
                else:
                    current += " " + stripped
            if current:
                bullets.append(current)

            for b in bullets:
                b = detect_bold_lead(b)
                lines.append(f"- {b}")
            lines.append("")

        elif "SKILLS" in header_upper or "PROFICIEN" in header_upper:
            # Category bullets with bold leads
            bullets = []
            current = ""
            for line in content_lines:
                stripped = line.strip()
                if not stripped:
                    if current:
                        bullets.append(current)
                        current = ""
                    continue
                if is_bullet(stripped):
                    if current:
                        bullets.append(current)
                    current = clean_bullet(stripped)
                else:
                    current += " " + stripped
            if current:
                bullets.append(current)

            for b in bullets:
                b = detect_bold_lead(b)
                lines.append(f"- {b}")
            lines.append("")

        elif "EXPERIENCE" in header_upper:
            # Job entries with bullets
            # Split into individual jobs
            job_blocks = []
            current_block = []

            for line in content_lines:
                stripped = line.strip()
                # Detect job header: contains "|" and a date range
                if (
                    "|" in stripped
                    and re.search(
                        r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}",
                        stripped,
                    )
                    and not is_bullet(stripped)
                ):
                    if current_block:
                        job_blocks.append(current_block)
                    current_block = [line]
                elif (
                    not is_bullet(stripped)
                    and stripped
                    and re.match(r"^[A-Z]", stripped)
                    and ("," in stripped or "New York" in stripped or "Kenilworth" in stripped)
                    and not current_block
                ):
                    # Company line without preceding title
                    current_block = [line]
                else:
                    current_block.append(line)

            if current_block:
                job_blocks.append(current_block)

            for block in job_blocks:
                title, company, loc, dates, bullets = parse_job_entry(block)
                if title or company:
                    lines.append(f"### {title} | {company} | {loc} | {dates}")
                    lines.append("")
                    for b in bullets:
                        lines.append(f"- {b}")
                    lines.append("")

        elif "EDUCATION" in header_upper:
            text = content_text.strip()
            # Try to find degree line
            degree_match = re.search(
                r"(Bachelor[^|]*)\s*\|\s*(\w+\s+\d{4})", text
            )
            if degree_match:
                lines.append(f"**{degree_match.group(1).strip()}** | {degree_match.group(2).strip()}")
            else:
                for line in content_lines:
                    stripped = line.strip()
                    if stripped:
                        lines.append(stripped)
            # University line
            for line in content_lines:
                stripped = line.strip()
                if "University" in stripped or "Rutgers" in stripped:
                    if "Bachelor" not in stripped:
                        lines.append(stripped)
            lines.append("")

        elif "INTEREST" in header_upper:
            text = content_text.strip()
            # Remove any prefix like "PERSONAL INTERESTS -"
            text = re.sub(r"^PERSONAL\s+INTERESTS\s*[-–—]\s*", "", text, flags=re.IGNORECASE)
            lines.append(text)
            lines.append("")

        else:
            # Generic section
            for line in content_lines:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
            lines.append("")

    return "\n".join(lines)


def process_pdf(pdf_path, variant):
    """Process a single PDF and return markdown content."""
    print(f"  Extracting: {os.path.basename(pdf_path)} ({variant} variant)")

    text = extract_pdf_text(pdf_path)
    if not text.strip():
        print(f"  WARNING: No text extracted from {pdf_path}")
        return None

    lines = text.split("\n")
    name, email, linkedin, location, phone = parse_contact_line(lines)
    sections = detect_sections(text)

    md = build_markdown(name, email, linkedin, location, phone, sections, variant)
    return md


def main():
    print("=== Resume PDF Extractor ===")
    print(f"Profile directory: {PROFILE_DIR}")

    # Find PDF files
    found = {}
    for filename, variant in PDF_VARIANTS.items():
        pdf_path = os.path.join(PROFILE_DIR, filename)
        if os.path.exists(pdf_path):
            found[variant] = pdf_path
        else:
            print(f"  WARNING: {filename} not found in profile/")

    if not found:
        # Try to find any PDF files
        for f in os.listdir(PROFILE_DIR):
            if f.lower().endswith(".pdf"):
                print(f"  Found PDF: {f}")
                if "sales engineer" in f.lower() or "SE" in f:
                    found["SE"] = os.path.join(PROFILE_DIR, f)
                elif "solutions consultant" in f.lower() or "SC" in f:
                    found["SC"] = os.path.join(PROFILE_DIR, f)

    if not found:
        print("ERROR: No resume PDFs found in profile/ directory.")
        print("Expected files:")
        for filename in PDF_VARIANTS:
            print(f"  - {filename}")
        sys.exit(1)

    # Process each PDF
    for variant, pdf_path in sorted(found.items()):
        md = process_pdf(pdf_path, variant)
        if md:
            output_path = os.path.join(PROFILE_DIR, f"base-resume-{variant}.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"  Written: {output_path}")

    print("\nDone! Markdown files updated.")


if __name__ == "__main__":
    main()

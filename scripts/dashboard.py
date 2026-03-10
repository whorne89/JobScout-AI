"""
dashboard.py — Generates HTML pages from jobs.json.

Usage: python scripts/dashboard.py
Output: dashboard.html, applied.html, jobs_log.html in the project root
"""

import json
import os
import sys
from datetime import datetime
from html import escape

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
JOBS_FILE = os.path.join(PROJECT_DIR, "data", "jobs.json")
OUTPUT_FILE = os.path.join(PROJECT_DIR, "dashboard.html")
OUTPUT_APPLIED = os.path.join(PROJECT_DIR, "applied.html")
OUTPUT_JOBS_LOG = os.path.join(PROJECT_DIR, "jobs_log.html")

TIER_CONFIG = {
    "apply_now": {
        "label": "Apply Now",
        "emoji": "\u2b50",
        "color": "#2e7d32",
        "bg": "#e8f5e9",
        "border": "#4caf50",
    },
    "worth_reviewing": {
        "label": "Worth Reviewing",
        "emoji": "\u2705",
        "color": "#1565c0",
        "bg": "#e3f2fd",
        "border": "#42a5f5",
    },
    "applied": {
        "label": "Applied",
        "emoji": "\U0001f4ec",
        "color": "#5e35b1",
        "bg": "#f3e5f5",
        "border": "#ab47bc",
    },
    "low_priority": {
        "label": "Low Priority",
        "emoji": "\u26a0\ufe0f",
        "color": "#e65100",
        "bg": "#fff3e0",
        "border": "#ff9800",
    },
    "filtered_out": {
        "label": "Filtered Out",
        "emoji": "\u274c",
        "color": "#b71c1c",
        "bg": "#ffebee",
        "border": "#ef5350",
    },
    "could_not_retrieve": {
        "label": "Could Not Retrieve",
        "emoji": "\u2753",
        "color": "#616161",
        "bg": "#f5f5f5",
        "border": "#9e9e9e",
    },
}

# Tier rendering order for sections and archives
TIER_ORDER = ["apply_now", "worth_reviewing", "applied", "low_priority", "filtered_out", "could_not_retrieve"]


def load_jobs():
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def format_date(iso_str):
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone()  # convert to local timezone
        return dt.strftime("%b %d, %Y %I:%M %p")
    except (ValueError, TypeError):
        return str(iso_str)


def short_date(iso_str):
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%b %d")
    except (ValueError, TypeError):
        return str(iso_str)


def build_badges(job):
    badges = []
    if job.get("is_new"):
        badges.append('<span class="badge badge-new">NEW</span>')
    count = job.get("seen_count", 1)
    if count and count > 1:
        source = escape(job.get("source_platform") or job.get("source") or "")
        date = short_date(job.get("first_seen"))
        # Tooltip shows repeat sighting dates (excluding first_seen), up to 5
        sightings = job.get("sightings", [])
        first_seen = job.get("first_seen", "")
        repeat_lines = []
        if sightings:
            for s in sightings:
                s_date = s.get("date", "")
                # Skip sightings on the same day as first_seen
                if first_seen and s_date[:10] == first_seen[:10]:
                    continue
                repeat_lines.append(f"{short_date(s_date)} — {escape(s.get('source') or 'Unknown')}")
            # Deduplicate and limit to 5
            seen_lines = []
            for line in repeat_lines:
                if line not in seen_lines:
                    seen_lines.append(line)
            repeat_lines = seen_lines[:5]
        if not repeat_lines and job.get("last_seen") and job.get("last_seen") != first_seen:
            repeat_lines.append(f"{short_date(job['last_seen'])}")
        tooltip = ("Also seen: " + ", ".join(repeat_lines)) if repeat_lines else ""
        tooltip_attr = escape(tooltip, quote=True)
        badges.append(f'<span class="badge badge-repeat" title="{tooltip_attr}">REPEAT x{count}</span>')
        # Date first (right next to REPEAT), then source
        if date:
            badges.append(f'<span class="badge badge-date">{date}</span>')
        if source:
            badges.append(f'<span class="badge badge-source">{source}</span>')
    if job.get("unconfirmed"):
        badges.append('<span class="badge badge-unconfirmed">UNCONFIRMED</span>')
    return " ".join(badges)


def build_evaluation_html(evaluation):
    if not evaluation:
        return ""

    score = evaluation.get("score", "?")
    summary = escape(evaluation.get("score_summary", ""))
    decision = escape(evaluation.get("apply_decision", ""))
    reason = escape(evaluation.get("apply_reason", ""))
    chance = evaluation.get("interview_chance", "?")
    buyer = escape(evaluation.get("buyer_type", ""))

    strong = evaluation.get("strong_matches", [])
    partial = evaluation.get("partial_matches", [])
    missing = evaluation.get("missing_qualifications", [])
    concerns = evaluation.get("key_concerns", [])

    def list_html(items, css_class=""):
        if not items:
            return "<p><em>None</em></p>"
        html = f'<ul class="{css_class}">'
        for item in items:
            html += f"<li>{escape(str(item))}</li>"
        html += "</ul>"
        return html

    decision_class = ""
    if "YES" in decision.upper() and "CAVEAT" not in decision.upper():
        decision_class = "decision-yes"
    elif "CAVEAT" in decision.upper():
        decision_class = "decision-caveats"
    elif "NO" in decision.upper():
        decision_class = "decision-no"

    return f"""
    <div class="accordion">
        <button class="accordion-toggle" onclick="toggleAccordion(this)">
            Evaluation Details (Score: {score}/10)
        </button>
        <div class="accordion-content">
            <p><strong>Summary:</strong> {summary}</p>
            <p><strong>Apply Decision:</strong> <span class="decision {decision_class}">{decision}</span></p>
            <p><strong>Reason:</strong> {reason}</p>
            <p><strong>Interview Chance:</strong> {chance}% | <strong>Buyer Type:</strong> {buyer}</p>

            <h4>Strong Matches</h4>
            {list_html(strong, "matches-strong")}

            <h4>Partial Matches</h4>
            {list_html(partial, "matches-partial")}

            <h4>Missing Qualifications</h4>
            {list_html(missing, "matches-missing")}

            <h4>Key Concerns</h4>
            {list_html(concerns, "concerns")}
        </div>
    </div>"""


def build_resume_changes_html(resume, evaluation=None):
    if not resume:
        return ""

    changes = resume.get("changes", [])
    if not changes:
        return ""

    filename = escape(resume.get("filename", ""))
    variant = escape(resume.get("variant", ""))
    generated_at = format_date(resume.get("generated_at"))

    # Score-based match label for the accordion header
    score = evaluation.get("score", 0) if evaluation else 0
    if score >= 7:
        match_label = "Strong Match"
        match_class = "score-high"
    elif score >= 5:
        match_label = "Moderate Match"
        match_class = "score-mid"
    else:
        match_label = "Weak Match"
        match_class = "score-low"

    # Build qualitative summary — why the tailored resume is strong for this role
    tailoring_summary = ""
    if evaluation:
        apply_reason = escape(evaluation.get("apply_reason") or "")
        decision = evaluation.get("apply_decision", "")
        chance = evaluation.get("interview_chance", "?")

        if apply_reason:
            tailoring_summary = f"<p>{apply_reason}</p>"
            tailoring_summary += (
                f"<p>Estimated interview chance: <strong>{chance}%</strong></p>"
            )

    changes_html = ""
    for change in changes:
        section = escape(change.get("section", ""))
        change_type = escape(change.get("change_type", ""))
        before = escape(change.get("before", ""))
        after = escape(change.get("after", ""))
        reason = escape(change.get("reason", ""))

        changes_html += f"""
        <div class="change-item">
            <div class="change-header">
                <strong>{section}</strong>
                <span class="change-type">{change_type}</span>
            </div>
            <div class="diff-view">
                <div class="diff-before">
                    <span class="diff-label">BEFORE</span>
                    <p>{before}</p>
                </div>
                <div class="diff-after">
                    <span class="diff-label">AFTER</span>
                    <p>{after}</p>
                </div>
            </div>
            <p class="change-reason"><em>Why: {reason}</em></p>
        </div>"""

    return f"""
    <div class="accordion">
        <button class="accordion-toggle" onclick="toggleAccordion(this)">
            Resume: {variant} variant, {len(changes)} modifications
            &mdash; <span class="{match_class}" style="font-size:12px; padding:1px 6px; border-radius:4px;">{match_label}</span>
        </button>
        <div class="accordion-content">
            <div class="resume-summary">{tailoring_summary}</div>
            <p><strong>File:</strong> {filename} | <strong>Generated:</strong> {generated_at}</p>
            {changes_html}
        </div>
    </div>"""


def build_copy_prompt(slug, job):
    """Build a comprehensive context prompt for copying to Claude."""
    company = job.get("company", "Unknown")
    title = job.get("title", "Unknown")
    location = job.get("location") or "Not listed"
    salary = job.get("salary") or "Not listed"
    apply_url = job.get("apply_url") or "N/A"
    source = job.get("source_platform") or job.get("source") or "Unknown"
    tier = job.get("tier") or "unknown"
    tier_reason = job.get("tier_reason") or ""

    tier_label = TIER_CONFIG.get(tier, {}).get("label", tier)

    lines = [
        f'Title this conversation: "{company} — {title}"',
        "",
        f"## Job Context: {company} — {title}",
        "",
        f"**Location:** {location}",
        f"**Salary:** {salary}",
        f"**Apply URL:** {apply_url}",
        f"**Source:** {source}",
        f"**Tier:** {tier_label} — {tier_reason}",
    ]

    evaluation = job.get("evaluation")
    if evaluation:
        score = evaluation.get("score", "?")
        decision = evaluation.get("apply_decision", "")
        chance = evaluation.get("interview_chance", "?")
        buyer = evaluation.get("buyer_type", "")
        summary = evaluation.get("score_summary", "")

        lines += [
            "",
            f"### Evaluation (Score: {score}/10)",
            f"**Decision:** {decision} | **Interview Chance:** {chance}%",
            f"**Buyer Type:** {buyer}",
            "",
            f"**Summary:** {summary}",
            "",
        ]

        for label, key in [
            ("Strong Matches", "strong_matches"),
            ("Partial Matches", "partial_matches"),
            ("Missing Qualifications", "missing_qualifications"),
            ("Key Concerns", "key_concerns"),
        ]:
            items = evaluation.get(key, [])
            lines.append(f"**{label}:**")
            if items:
                for item in items:
                    lines.append(f"- {item}")
            else:
                lines.append("- None")
            lines.append("")

    resume = job.get("resume")
    if resume and resume.get("filename"):
        variant = resume.get("variant", "")
        filename = resume.get("filename", "")
        lines += ["### Resume", f"**Variant:** {variant} | **File:** {filename}"]

        changes = resume.get("changes", [])
        if changes:
            lines += ["", "**Changes made:**"]
            for change in changes:
                section = change.get("section", "")
                change_type = change.get("change_type", "")
                before = change.get("before", "")
                after = change.get("after", "")
                reason = change.get("reason", "")
                lines.append(f"- **{section}** ({change_type}): {reason}")
                lines.append(f"  - Before: {before}")
                lines.append(f"  - After: {after}")

    lines += [
        "",
        "---",
        "Candidate profile: profile/candidate-profile.md",
        "Base resumes: profile/base-resume-SE.md, profile/base-resume-SC.md",
        "",
        "What would you like to do with this job? (e.g., write a cover letter, tweak the resume, re-evaluate, prep for interview)",
    ]

    return "\n".join(lines)


def escape_for_attr(text):
    """Escape text for use in an HTML data attribute, including newlines."""
    return escape(text, quote=True).replace("\n", "&#10;")


def build_jd_button(slug, job):
    """Build a View JD button if jd_text is available, otherwise link to apply URL."""
    jd_text = job.get("jd_text")
    apply_url = job.get("apply_url", "")
    if jd_text:
        safe_slug = escape(slug, quote=True)
        return f'<button class="btn btn-jd" onclick="showJD(\'{safe_slug}\')">View JD</button>'
    elif apply_url:
        return f'<a href="{escape(apply_url)}" target="_blank" class="btn btn-apply">Job Posting</a>'
    return ""


def build_jd_button_sm(slug, job):
    """Build a small View JD button for compact cards and tables."""
    jd_text = job.get("jd_text")
    apply_url = job.get("apply_url") or ""
    if jd_text:
        safe_slug = escape(slug, quote=True)
        return f'<button class="btn-sm btn-jd" onclick="showJD(\'{safe_slug}\')">View JD</button>'
    elif apply_url:
        return f'<a href="{escape(apply_url)}" target="_blank" class="btn-sm btn-jd">View JD</a>'
    return ""


def build_dropdown_html(slug, tier_key):
    """Build a kebab menu dropdown with Mark Applied action."""
    safe_slug = escape(slug, quote=True)
    if tier_key == "applied":
        return f"""<div class="card-dropdown">
            <button class="dropdown-toggle" onclick="toggleDropdown(this)" title="More actions">&#8942;</button>
            <div class="dropdown-menu">
                <button class="dropdown-item" disabled>&#10003; Applied</button>
            </div>
        </div>"""
    return f"""<div class="card-dropdown">
            <button class="dropdown-toggle" onclick="toggleDropdown(this)" title="More actions">&#8942;</button>
            <div class="dropdown-menu">
                <button class="dropdown-item" onclick="markApplied('{safe_slug}')" data-applied-slug="{safe_slug}">Mark Applied</button>
            </div>
        </div>"""


def build_job_card(slug, job, tier_key, queued_slugs=None):
    tc = TIER_CONFIG[tier_key]
    company = escape(job.get("company", "Unknown"))
    title = escape(job.get("title", "Unknown"))
    location = escape(job.get("location", "Not listed"))
    salary = escape(job.get("salary") or "Not listed")
    source = escape(job.get("source_platform") or job.get("source") or "")
    first_seen = short_date(job.get("first_seen"))
    apply_url = job.get("apply_url", "")
    badges = build_badges(job)

    # Only show source/date in meta-items if NOT already shown in badges
    has_repeat = job.get("seen_count", 1) and job.get("seen_count", 1) > 1

    score_badge = ""
    if job.get("evaluation") and job["evaluation"].get("score") is not None:
        score = job["evaluation"]["score"]
        score_class = "score-high" if score >= 7 else "score-mid" if score >= 5 else "score-low"
        score_badge = f'<span class="score-badge {score_class}">{score}/10</span>'

    jd_btn = build_jd_button(slug, job)

    apply_link = ""
    if apply_url:
        apply_link = f'<a href="{escape(apply_url)}" target="_blank" class="btn btn-apply">Apply</a>'

    resume_link = ""
    if job.get("resume") and job["resume"].get("filename"):
        fname = escape(job["resume"]["filename"])
        resume_link = f'<a href="resumes/{fname}" target="_blank" class="btn btn-resume">Resume PDF</a>'

    # "Create Resume" button for worth_reviewing jobs with evaluation but no resume
    create_resume_btn = ""
    if (
        tier_key == "worth_reviewing"
        and job.get("evaluation")
        and not job.get("resume")
    ):
        safe_slug = escape(slug)
        if queued_slugs and slug in queued_slugs:
            create_resume_btn = f'<button class="btn btn-queue queued" disabled>Queued</button>'
        else:
            create_resume_btn = f'<button class="btn btn-queue" data-slug="{safe_slug}" onclick="queueResume(this)">Add to Queue</button>'

    copy_prompt = escape_for_attr(build_copy_prompt(slug, job))
    copy_btn = f'<button class="btn btn-copy" onclick="copyPrompt(this)" data-prompt="{copy_prompt}">Copy to Claude</button>'

    dropdown = build_dropdown_html(slug, tier_key)

    eval_html = build_evaluation_html(job.get("evaluation"))
    resume_html = build_resume_changes_html(job.get("resume"), job.get("evaluation"))
    tier_reason = escape(job.get("tier_reason") or "")

    return f"""
    <div class="job-card" style="border-left-color: {tc['border']}"
         data-tier="{tier_key}" data-company="{company.lower()}"
         data-title="{title.lower()}" data-score="{job.get('evaluation', {}).get('score', 0) if job.get('evaluation') else 0}"
         data-first-seen="{job.get('first_seen', '')}">
        <div class="card-header">
            <div class="card-title-row">
                <h3>{company} &mdash; {title}</h3>
                {score_badge}
            </div>
            <div class="card-meta">
                {badges}
                <span class="meta-item">{location}</span>
                <span class="meta-item">{salary}</span>
                {"" if has_repeat else f'<span class="meta-item">{source}</span>'}
                {"" if has_repeat else f'<span class="meta-item">{first_seen}</span>'}
            </div>
            <p class="tier-reason">{tier_reason}</p>
        </div>
        <div class="card-actions">
            {jd_btn}
            {apply_link}
            <div class="actions-right">
                {copy_btn}
                {resume_link}
                {create_resume_btn}
                {dropdown}
            </div>
        </div>
        {eval_html}
        {resume_html}
    </div>"""


def build_compact_card(slug, job, tier_key):
    tc = TIER_CONFIG[tier_key]
    company = escape(job.get("company", "Unknown"))
    title = escape(job.get("title", "Unknown"))
    location = escape(job.get("location") or "")
    salary = escape(job.get("salary") or "")
    tier_reason = escape(job.get("tier_reason") or "")
    badges = build_badges(job)

    jd_link = build_jd_button_sm(slug, job)

    copy_prompt = escape_for_attr(build_copy_prompt(slug, job))
    copy_btn = f'<button class="btn-sm btn-copy" onclick="copyPrompt(this)" data-prompt="{copy_prompt}">Copy to Claude</button>'

    dropdown = build_dropdown_html(slug, tier_key)

    return f"""
    <div class="job-card compact" style="border-left-color: {tc['border']}"
         data-tier="{tier_key}" data-company="{company.lower()}"
         data-title="{title.lower()}" data-score="0"
         data-first-seen="{job.get('first_seen', '')}">
        <div class="compact-row">
            <span class="compact-text">
                <strong>{company}</strong> &mdash; {title}
                {badges}
                <span class="meta-inline">{location}</span>
                <span class="meta-inline">{salary}</span>
            </span>
            <span class="compact-spacer"></span>
            <span class="compact-actions">
                {jd_link}
                {copy_btn}
                {dropdown}
            </span>
        </div>
        <p class="tier-reason compact-reason">{tier_reason}</p>
    </div>"""


def build_applied_card(slug, job):
    """Build a compact card for applied jobs with applied date and resume info."""
    tc = TIER_CONFIG["applied"]
    company = escape(job.get("company", "Unknown"))
    title = escape(job.get("title", "Unknown"))
    application = job.get("application") or {}
    applied_date = short_date(application.get("applied_at"))
    badges = build_badges(job)

    score_badge = ""
    if job.get("evaluation") and job["evaluation"].get("score") is not None:
        score = job["evaluation"]["score"]
        score_class = "score-high" if score >= 7 else "score-mid" if score >= 5 else "score-low"
        score_badge = f'<span class="score-badge {score_class}" style="font-size:12px;padding:2px 6px;">{score}/10</span>'

    jd_link = build_jd_button_sm(slug, job)

    resume_link = ""
    if job.get("resume") and job["resume"].get("filename"):
        fname = escape(job["resume"]["filename"])
        variant = escape(job["resume"].get("variant", ""))
        resume_link = f'<a href="resumes/{fname}" target="_blank" class="btn-sm btn-resume">{variant} PDF</a>'

    copy_prompt = escape_for_attr(build_copy_prompt(slug, job))
    copy_btn = f'<button class="btn-sm btn-copy" onclick="copyPrompt(this)" data-prompt="{copy_prompt}">Copy to Claude</button>'

    return f"""
    <div class="job-card compact" style="border-left-color: {tc['border']}"
         data-tier="applied" data-company="{company.lower()}"
         data-title="{title.lower()}" data-score="{job.get('evaluation', {}).get('score', 0) if job.get('evaluation') else 0}"
         data-first-seen="{job.get('first_seen', '')}">
        <div class="compact-row">
            <span class="compact-text">
                <strong>{company}</strong> &mdash; {title}
                <span class="badge badge-applied">Applied {applied_date}</span>
                {score_badge}
                {badges}
            </span>
            <span class="compact-spacer"></span>
            <span class="compact-actions">
                {jd_link}
                {resume_link}
                {copy_btn}
            </span>
        </div>
    </div>"""


def build_filtered_row(slug, job):
    company = escape(job.get("company", "Unknown"))
    title = escape(job.get("title", "Unknown"))
    reason = escape(job.get("tier_reason") or "")
    jd_btn = build_jd_button_sm(slug, job)
    return f"<tr><td>{company}</td><td>{title}</td><td>{reason}</td><td>{jd_btn}</td></tr>"


def build_cnr_row(slug, job):
    company = escape(job.get("company") or "Unknown")
    title = escape(job.get("title") or "Unknown")
    source = escape(job.get("source_platform") or job.get("source") or "")
    first_seen = short_date(job.get("first_seen"))
    jd_btn = build_jd_button_sm(slug, job)
    return f"<tr><td>{company}</td><td>{title}</td><td>{source}</td><td>{first_seen}</td><td>{jd_btn}</td></tr>"


def get_queued_slugs():
    """Check resumes/queue/ for pending trigger files."""
    queue_dir = os.path.join(PROJECT_DIR, "resumes", "queue")
    if not os.path.isdir(queue_dir):
        return set()
    slugs = set()
    for f in os.listdir(queue_dir):
        if f.endswith(".json"):
            slugs.add(f[:-5])  # strip .json
    return slugs


def sort_tier_jobs(jobs_list):
    """Sort jobs: new first, then newest first_seen."""
    new_jobs = [(s, j) for s, j in jobs_list if j.get("is_new")]
    old_jobs = [(s, j) for s, j in jobs_list if not j.get("is_new")]
    new_jobs.sort(key=lambda x: x[1].get("first_seen", ""), reverse=True)
    old_jobs.sort(key=lambda x: x[1].get("first_seen", ""), reverse=True)
    return new_jobs + old_jobs


def get_month_label(month_str):
    """Convert '2026-03' to 'March 2026'."""
    try:
        dt = datetime.strptime(month_str + "-01", "%Y-%m-%d")
        return dt.strftime("%B %Y")
    except (ValueError, TypeError):
        return month_str


def build_archive_section(month_str, month_jobs, queued_slugs):
    """Build a collapsed accordion for an archive month's jobs."""
    month_label = get_month_label(month_str)
    count = len(month_jobs)

    # Group by tier
    tier_groups = {key: [] for key in TIER_ORDER}
    for slug, job in month_jobs.items():
        tier = job.get("tier", "could_not_retrieve")
        if tier in tier_groups:
            tier_groups[tier].append((slug, job))

    content_html = ""
    for tier_key in TIER_ORDER:
        tier_jobs = tier_groups[tier_key]
        if not tier_jobs:
            continue
        tc = TIER_CONFIG[tier_key]
        tier_jobs = sort_tier_jobs(tier_jobs)

        if tier_key == "applied":
            cards = "\n".join(build_applied_card(s, j) for s, j in tier_jobs)
        else:
            cards = "\n".join(build_compact_card(s, j, tier_key) for s, j in tier_jobs)

        content_html += f"""
            <h3 style="color: {tc['color']}; margin: 12px 0 8px; font-size: 15px;">
                {tc['emoji']} {tc['label']} ({len(tier_jobs)})
            </h3>
            {cards}"""

    return f"""
    <div class="archive-section">
        <div class="accordion">
            <button class="accordion-toggle archive-toggle" onclick="toggleAccordion(this)">
                &#128193; {month_label} ({count} jobs)
            </button>
            <div class="accordion-content">
                {content_html}
            </div>
        </div>
    </div>"""


def generate_dashboard():
    data = load_jobs()
    jobs = data.get("jobs", {})
    stats = data.get("stats", {})
    queued_slugs = get_queued_slugs()
    last_scan = format_date(data.get("last_scan"))

    current_month = datetime.now().strftime("%Y-%m")

    # Separate current month jobs from archive jobs
    current_month_jobs = {}
    archive_months = {}  # month_str -> {slug: job}
    for slug, job in jobs.items():
        job_month = (job.get("first_seen") or "")[:7]
        if job_month == current_month or not job_month:
            current_month_jobs[slug] = job
        else:
            archive_months.setdefault(job_month, {})[slug] = job

    # Group current month jobs by tier
    tiers = {key: [] for key in TIER_CONFIG}
    for slug, job in current_month_jobs.items():
        tier = job.get("tier", "could_not_retrieve")
        if tier in tiers:
            tiers[tier].append((slug, job))

    # Sort each tier
    for tier_key in tiers:
        tiers[tier_key] = sort_tier_jobs(tiers[tier_key])

    # Count stats (across ALL jobs)
    total = len(jobs)
    new_count = sum(1 for j in jobs.values() if j.get("is_new"))
    eval_count = sum(1 for j in jobs.values() if j.get("evaluation"))
    resume_count = sum(1 for j in jobs.values() if j.get("resume"))
    applied_count = sum(1 for j in jobs.values() if j.get("tier") == "applied")

    # Run summary
    run_summary = data.get("last_run_summary", "")

    # Build tier sections for current month
    sections_html = ""

    # Apply Now — full cards, expanded by default
    if tiers["apply_now"]:
        cards = "\n".join(build_job_card(s, j, "apply_now", queued_slugs) for s, j in tiers["apply_now"])
        sections_html += f"""
        <div class="tier-section" id="tier-apply_now">
            <div class="accordion">
                <button class="accordion-toggle tier-toggle open" onclick="toggleAccordion(this)" style="color: {TIER_CONFIG['apply_now']['color']}">
                    {TIER_CONFIG['apply_now']['emoji']} Apply Now ({len(tiers['apply_now'])})
                </button>
                <div class="accordion-content" style="display:block">
                    {cards}
                </div>
            </div>
        </div>"""

    # Worth Reviewing — full cards, expanded by default
    if tiers["worth_reviewing"]:
        cards = "\n".join(build_job_card(s, j, "worth_reviewing", queued_slugs) for s, j in tiers["worth_reviewing"])
        sections_html += f"""
        <div class="tier-section" id="tier-worth_reviewing">
            <div class="accordion">
                <button class="accordion-toggle tier-toggle open" onclick="toggleAccordion(this)" style="color: {TIER_CONFIG['worth_reviewing']['color']}">
                    {TIER_CONFIG['worth_reviewing']['emoji']} Worth Reviewing ({len(tiers['worth_reviewing'])})
                </button>
                <div class="accordion-content" style="display:block">
                    {cards}
                </div>
            </div>
        </div>"""

    # Applied — compact applied cards, expanded by default
    if tiers["applied"]:
        cards = "\n".join(build_applied_card(s, j) for s, j in tiers["applied"])
        sections_html += f"""
        <div class="tier-section" id="tier-applied">
            <div class="accordion">
                <button class="accordion-toggle tier-toggle open" onclick="toggleAccordion(this)" style="color: {TIER_CONFIG['applied']['color']}">
                    {TIER_CONFIG['applied']['emoji']} Applied ({len(tiers['applied'])})
                </button>
                <div class="accordion-content" style="display:block">
                    {cards}
                </div>
            </div>
        </div>"""

    # Low Priority — compact cards, expanded by default
    if tiers["low_priority"]:
        cards = "\n".join(build_compact_card(s, j, "low_priority") for s, j in tiers["low_priority"])
        sections_html += f"""
        <div class="tier-section" id="tier-low_priority">
            <div class="accordion">
                <button class="accordion-toggle tier-toggle open" onclick="toggleAccordion(this)" style="color: {TIER_CONFIG['low_priority']['color']}">
                    {TIER_CONFIG['low_priority']['emoji']} Low Priority ({len(tiers['low_priority'])})
                </button>
                <div class="accordion-content" style="display:block">
                    {cards}
                </div>
            </div>
        </div>"""

    # Filtered Out — collapsed by default
    if tiers["filtered_out"]:
        rows = "\n".join(build_filtered_row(s, j) for s, j in tiers["filtered_out"])
        sections_html += f"""
        <div class="tier-section" id="tier-filtered_out">
            <div class="accordion">
                <button class="accordion-toggle tier-toggle" onclick="toggleAccordion(this)">
                    {TIER_CONFIG['filtered_out']['emoji']} Filtered Out ({len(tiers['filtered_out'])})
                </button>
                <div class="accordion-content">
                    <table class="filtered-table">
                        <thead><tr><th>Company</th><th>Title</th><th>Reason</th><th>JD</th></tr></thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
            </div>
        </div>"""

    # Could Not Retrieve — collapsed by default
    if tiers["could_not_retrieve"]:
        rows = "\n".join(build_cnr_row(s, j) for s, j in tiers["could_not_retrieve"])
        sections_html += f"""
        <div class="tier-section" id="tier-could_not_retrieve">
            <div class="accordion">
                <button class="accordion-toggle tier-toggle" onclick="toggleAccordion(this)">
                    {TIER_CONFIG['could_not_retrieve']['emoji']} Could Not Retrieve ({len(tiers['could_not_retrieve'])})
                </button>
                <div class="accordion-content">
                    <table class="filtered-table">
                        <thead><tr><th>Company</th><th>Title</th><th>Source</th><th>First Seen</th><th>JD</th></tr></thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
            </div>
        </div>"""

    # Archive sections for previous months
    archive_html = ""
    if archive_months:
        archive_html = '<div id="archive-sections"><h2 class="tier-header" style="color: var(--text-muted); margin-top: 32px;">Previous Months</h2>'
        for month in sorted(archive_months.keys(), reverse=True):
            archive_html += build_archive_section(month, archive_months[month], queued_slugs)
        archive_html += "</div>"

    # Empty state
    if not jobs:
        sections_html = """
        <div class="empty-state">
            <h2>No jobs scanned yet</h2>
            <p>Run the pipeline to scan your Gmail for job alerts.</p>
        </div>"""

    # Build JD text data for inline JS
    jd_data = {}
    for slug, job in jobs.items():
        jd_text = job.get("jd_text")
        if jd_text:
            jd_data[slug] = jd_text
    jd_data_json = json.dumps(jd_data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JobScout Dashboard</title>
<style>
:root {{
    --bg: #f8f9fa;
    --card-bg: #ffffff;
    --text: #212529;
    --text-muted: #6c757d;
    --border: #dee2e6;
    --accent: #1f4e79;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 20px;
    max-width: 1100px;
    margin: 0 auto;
}}
.header {{
    background: var(--accent);
    color: white;
    padding: 24px 32px;
    border-radius: 12px;
    margin-bottom: 20px;
}}
.header h1 {{ font-size: 24px; margin-bottom: 8px; }}
.header-meta {{ font-size: 14px; opacity: 0.9; }}
.stats {{
    display: flex;
    gap: 16px;
    margin-top: 12px;
    flex-wrap: wrap;
}}
.stat {{
    background: rgba(255,255,255,0.15);
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 14px;
}}
.stat strong {{ font-size: 20px; display: block; }}
.run-summary {{
    margin-top: 14px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.12);
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.6;
    border-left: 3px solid rgba(255,255,255,0.4);
    white-space: pre-line;
}}
.nav-links {{
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
    font-size: 14px;
}}
.nav-link {{
    color: var(--accent);
    text-decoration: none;
    padding: 4px 0;
    border-bottom: 2px solid transparent;
}}
.nav-link:hover {{ border-bottom-color: var(--accent); }}
.nav-link.active {{
    font-weight: 600;
    border-bottom-color: var(--accent);
}}
.filter-bar {{
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    align-items: center;
}}
.filter-btn {{
    padding: 6px 14px;
    border: 2px solid var(--border);
    border-radius: 20px;
    background: white;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
}}
.filter-btn:hover {{ border-color: var(--accent); }}
.filter-btn.active {{
    background: var(--accent);
    color: white;
    border-color: var(--accent);
}}
.search-box {{
    padding: 8px 14px;
    border: 2px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    flex-grow: 1;
    min-width: 200px;
}}
.sort-select {{
    padding: 8px 14px;
    border: 2px solid var(--border);
    border-radius: 8px;
    font-size: 13px;
    background: white;
}}
.tier-section {{ margin-bottom: 24px; }}
.tier-header {{
    font-size: 18px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--border);
}}
.job-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-left: 5px solid;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
    transition: box-shadow 0.2s;
}}
.job-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
.job-card.compact {{ padding: 10px 16px; }}
.card-header {{ margin-bottom: 8px; }}
.card-title-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
}}
.card-title-row h3 {{ font-size: 16px; }}
.card-meta {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 6px;
    font-size: 13px;
    color: var(--text-muted);
}}
.meta-item {{ white-space: nowrap; }}
.meta-inline {{
    font-size: 12px;
    color: var(--text-muted);
    margin-left: 8px;
}}
.tier-reason {{
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 4px;
    font-style: italic;
}}
.compact-reason {{ margin-top: 2px; }}
.compact-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}}
.badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}}
.badge-new {{ background: #e8f5e9; color: #2e7d32; }}
.badge-repeat {{ background: #fff3e0; color: #e65100; cursor: help; }}
.badge-source {{ background: #e3f2fd; color: #1565c0; }}
.badge-date {{ background: #f3e5f5; color: #6a1b9a; }}
.badge-unconfirmed {{ background: #f5f5f5; color: #616161; }}
.badge-applied {{ background: #f3e5f5; color: #5e35b1; }}
.score-badge {{
    font-size: 14px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 8px;
    white-space: nowrap;
}}
.score-high {{ background: #e8f5e9; color: #2e7d32; }}
.score-mid {{ background: #fff3e0; color: #e65100; }}
.score-low {{ background: #ffebee; color: #b71c1c; }}
.card-actions {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin: 8px 0;
}}
.actions-right {{
    display: flex;
    gap: 8px;
    margin-left: auto;
    align-items: center;
}}
.btn, .btn-sm {{
    display: inline-block;
    padding: 6px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    transition: opacity 0.2s;
}}
.btn:hover, .btn-sm:hover {{ opacity: 0.85; }}
.btn-apply {{ background: var(--accent); color: white; }}
.btn-resume {{ background: #e8f5e9; color: #2e7d32; border: 1px solid #4caf50; }}
.btn-copy {{ background: #f3e5f5; color: #6a1b9a; border: 1px solid #ab47bc; cursor: pointer; }}
.btn-copy:hover {{ background: #e1bee7; }}
.btn-copy.copied {{ background: #e8f5e9; color: #2e7d32; border-color: #4caf50; }}
.btn-queue {{ background: #e3f2fd; color: #1565c0; border: 1px solid #42a5f5; cursor: pointer; }}
.btn-queue:hover {{ background: #bbdefb; }}
.btn-queue.queued {{ background: #f5f5f5; color: #9e9e9e; border-color: #bdbdbd; cursor: default; }}
.btn-sm {{
    padding: 3px 10px;
    font-size: 12px;
    background: var(--accent);
    color: white;
}}
.btn-sm.btn-resume {{ background: #e8f5e9; color: #2e7d32; border: 1px solid #4caf50; }}
.accordion {{ margin-top: 8px; }}
.accordion-toggle {{
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 14px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    width: 100%;
    text-align: left;
    transition: background 0.2s;
}}
.accordion-toggle:hover {{ background: #e9ecef; }}
.accordion-toggle::before {{ content: "\\25B6 "; font-size: 10px; }}
.accordion-toggle.open::before {{ content: "\\25BC "; }}
.tier-toggle {{
    font-size: 16px;
    padding: 12px 16px;
    border-radius: 8px;
}}
.archive-toggle {{
    font-size: 15px;
    padding: 10px 16px;
    border-radius: 8px;
    background: #eef2f7;
}}
.accordion-content {{
    display: none;
    padding: 12px 16px;
    border: 1px solid var(--border);
    border-top: none;
    border-radius: 0 0 6px 6px;
    background: white;
    font-size: 13px;
}}
.accordion-content h4 {{
    margin-top: 12px;
    margin-bottom: 4px;
    font-size: 13px;
    color: var(--accent);
}}
.accordion-content ul {{ padding-left: 20px; margin-bottom: 8px; }}
.accordion-content li {{ margin-bottom: 2px; }}
.matches-strong li::marker {{ color: #2e7d32; }}
.matches-partial li::marker {{ color: #e65100; }}
.matches-missing li::marker {{ color: #b71c1c; }}
.decision {{
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}}
.decision-yes {{ background: #e8f5e9; color: #2e7d32; }}
.decision-caveats {{ background: #fff3e0; color: #e65100; }}
.decision-no {{ background: #ffebee; color: #b71c1c; }}
.change-item {{
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    margin: 8px 0;
}}
.change-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}}
.change-type {{
    font-size: 11px;
    padding: 2px 8px;
    background: #e3f2fd;
    color: #1565c0;
    border-radius: 10px;
    text-transform: uppercase;
    font-weight: 600;
}}
.diff-view {{ display: flex; gap: 12px; flex-wrap: wrap; }}
.diff-before, .diff-after {{
    flex: 1;
    min-width: 250px;
    padding: 10px;
    border-radius: 6px;
    font-size: 12px;
    line-height: 1.5;
}}
.diff-before {{ background: #ffebee; border-left: 3px solid #ef5350; }}
.diff-after {{ background: #e8f5e9; border-left: 3px solid #4caf50; }}
.diff-label {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    opacity: 0.6;
    display: block;
    margin-bottom: 4px;
}}
.change-reason {{
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 6px;
}}
.resume-summary {{
    background: #f3e5f5;
    border-left: 3px solid #ab47bc;
    padding: 10px 14px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 12px;
    font-size: 13px;
    line-height: 1.6;
    color: var(--text);
}}
.compact-text {{
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.compact-actions {{
    display: flex;
    gap: 6px;
    align-items: center;
    flex-shrink: 0;
    white-space: nowrap;
}}
.compact-spacer {{ flex-grow: 1; }}
.filtered-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
.filtered-table th, .filtered-table td {{
    padding: 6px 12px;
    border-bottom: 1px solid var(--border);
    text-align: left;
}}
.filtered-table th {{ font-weight: 600; background: var(--bg); }}
.empty-state {{
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
}}
.empty-state h2 {{ margin-bottom: 8px; }}
.hidden {{ display: none !important; }}
.btn-jd {{ background: #e8eaf6; color: #283593; border: 1px solid #5c6bc0; cursor: pointer; }}
.btn-jd:hover {{ background: #c5cae9; }}
.btn-sm.btn-jd {{ padding: 3px 10px; font-size: 12px; border-radius: 6px; font-weight: 600; cursor: pointer; background: #e8eaf6; color: #283593; border: 1px solid #5c6bc0; }}
.btn-sm.btn-jd:hover {{ background: #c5cae9; }}
.btn-sm.btn-copy {{ cursor: pointer; background: #f3e5f5; color: #6a1b9a; border: 1px solid #ab47bc; }}
/* Dropdown menu */
.card-dropdown {{ position: relative; display: inline-block; }}
.dropdown-toggle {{
    background: none;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px 8px;
    cursor: pointer;
    font-size: 18px;
    line-height: 1;
    color: var(--text-muted);
    transition: background 0.2s;
}}
.dropdown-toggle:hover {{ background: var(--bg); }}
.dropdown-menu {{
    display: none;
    position: absolute;
    right: 0;
    top: 100%;
    background: white;
    border: 1px solid var(--border);
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 100;
    min-width: 160px;
    padding: 4px 0;
}}
.dropdown-menu.show {{ display: block; }}
.dropdown-item {{
    display: block;
    width: 100%;
    padding: 8px 16px;
    border: none;
    background: none;
    cursor: pointer;
    text-align: left;
    font-size: 13px;
    color: var(--text);
}}
.dropdown-item:hover {{ background: var(--bg); }}
.dropdown-item:disabled {{ color: var(--text-muted); cursor: default; }}
.dropdown-item:disabled:hover {{ background: none; }}
/* Archive sections */
.archive-section {{ margin-bottom: 12px; }}
/* JD Modal */
.jd-modal-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    padding: 20px;
}}
.jd-modal-overlay.active {{ display: flex; }}
.jd-modal {{
    background: white;
    border-radius: 12px;
    max-width: 800px;
    width: 100%;
    max-height: 85vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}}
.jd-modal-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
}}
.jd-modal-header h3 {{ font-size: 16px; }}
.jd-modal-close {{
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: var(--text-muted);
    padding: 4px 8px;
    border-radius: 4px;
}}
.jd-modal-close:hover {{ background: var(--bg); color: var(--text); }}
.jd-modal-body {{
    padding: 20px 24px;
    overflow-y: auto;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
</style>
</head>
<body>

<div class="header">
    <h1>JobScout Dashboard</h1>
    <div class="header-meta">Last scan: {last_scan}</div>
    <div class="stats">
        <div class="stat"><strong>{total}</strong> Total Jobs</div>
        <div class="stat"><strong>{new_count}</strong> New</div>
        <div class="stat"><strong>{eval_count}</strong> Evaluated</div>
        <div class="stat"><strong>{resume_count}</strong> Resumes</div>
        <div class="stat"><strong>{applied_count}</strong> Applied</div>
    </div>
    {"<div class='run-summary'>" + escape(run_summary) + "</div>" if run_summary else ""}
</div>

<div class="nav-links">
    <a href="dashboard.html" class="nav-link active">Dashboard</a>
    <a href="jobs_log.html" class="nav-link">Jobs Log</a>
    <a href="applied.html" class="nav-link">Applied Tracker</a>
</div>

<div class="filter-bar">
    <button class="filter-btn active" data-tier="all" onclick="filterTier('all', this)">All</button>
    <button class="filter-btn" data-tier="apply_now" onclick="filterTier('apply_now', this)">&#11088; Apply Now</button>
    <button class="filter-btn" data-tier="worth_reviewing" onclick="filterTier('worth_reviewing', this)">&#9989; Worth Reviewing</button>
    <button class="filter-btn" data-tier="applied" onclick="filterTier('applied', this)">&#128236; Applied</button>
    <button class="filter-btn" data-tier="low_priority" onclick="filterTier('low_priority', this)">&#9888;&#65039; Low Priority</button>
    <input type="text" class="search-box" placeholder="Search company or title..." oninput="searchJobs(this.value)">
    <select class="sort-select" onchange="sortJobs(this.value)">
        <option value="newest">Newest First</option>
        <option value="company">Company A-Z</option>
        <option value="score">Score (High-Low)</option>
    </select>
</div>

{sections_html}

{archive_html}

<div class="jd-modal-overlay" id="jdModal" onclick="if(event.target===this)closeJD()">
    <div class="jd-modal">
        <div class="jd-modal-header">
            <h3 id="jdModalTitle">Job Description</h3>
            <button class="jd-modal-close" onclick="closeJD()">&times;</button>
        </div>
        <div class="jd-modal-body" id="jdModalBody"></div>
    </div>
</div>

<script>
var JD_DATA = {jd_data_json};
function toggleAccordion(btn) {{
    btn.classList.toggle('open');
    var content = btn.nextElementSibling;
    content.style.display = content.style.display === 'block' ? 'none' : 'block';
}}

function filterTier(tier, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.tier-section').forEach(s => {{
        if (tier === 'all') {{
            s.classList.remove('hidden');
        }} else {{
            var sectionId = s.id || '';
            s.classList.toggle('hidden', !sectionId.includes(tier));
        }}
    }});
    // Archives: show only when All is selected
    document.querySelectorAll('.archive-section').forEach(s => {{
        s.classList.toggle('hidden', tier !== 'all');
    }});
    // Also toggle the archive header
    var archiveContainer = document.getElementById('archive-sections');
    if (archiveContainer) archiveContainer.classList.toggle('hidden', tier !== 'all');
}}

function searchJobs(query) {{
    query = query.toLowerCase();
    document.querySelectorAll('.job-card').forEach(card => {{
        var company = card.getAttribute('data-company') || '';
        var title = card.getAttribute('data-title') || '';
        card.classList.toggle('hidden', query && !company.includes(query) && !title.includes(query));
    }});
}}

function sortJobs(mode) {{
    document.querySelectorAll('.tier-section').forEach(section => {{
        var cards = Array.from(section.querySelectorAll('.job-card'));
        if (cards.length === 0) return;
        cards.sort(function(a, b) {{
            if (mode === 'newest') {{
                return (b.getAttribute('data-first-seen') || '').localeCompare(a.getAttribute('data-first-seen') || '');
            }} else if (mode === 'company') {{
                return (a.getAttribute('data-company') || '').localeCompare(b.getAttribute('data-company') || '');
            }} else if (mode === 'score') {{
                return (parseInt(b.getAttribute('data-score')) || 0) - (parseInt(a.getAttribute('data-score')) || 0);
            }}
            return 0;
        }});
        var container = cards[0].parentNode;
        cards.forEach(c => container.appendChild(c));
    }});
}}

function copyPrompt(btn) {{
    var prompt = btn.getAttribute('data-prompt');
    navigator.clipboard.writeText(prompt).then(function() {{
        var orig = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(function() {{
            btn.textContent = orig;
            btn.classList.remove('copied');
        }}, 2000);
    }});
}}

function showJD(slug) {{
    var text = JD_DATA[slug];
    if (!text) {{ alert('No JD available for ' + slug); return; }}
    var title = slug.replace('--', ' — ').replace(/-/g, ' ');
    title = title.replace(/\\b\\w/g, function(c) {{ return c.toUpperCase(); }});
    document.getElementById('jdModalTitle').textContent = title;
    document.getElementById('jdModalBody').textContent = text;
    document.getElementById('jdModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}}

function closeJD() {{
    document.getElementById('jdModal').classList.remove('active');
    document.body.style.overflow = '';
}}

document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeJD();
}});

function queueResume(btn) {{
    if (btn.classList.contains('queued')) return;
    var slug = btn.getAttribute('data-slug');
    var triggerContent = JSON.stringify({{slug: slug}});
    var blob = new Blob([triggerContent], {{type: 'application/json'}});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = slug + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
    btn.textContent = 'Queued';
    btn.classList.add('queued');
    btn.title = 'Trigger file downloaded — move to resumes/queue/ folder';
}}

function toggleDropdown(btn) {{
    var menu = btn.nextElementSibling;
    // Close all other dropdowns first
    document.querySelectorAll('.dropdown-menu.show').forEach(function(m) {{
        if (m !== menu) m.classList.remove('show');
    }});
    menu.classList.toggle('show');
}}

// Close dropdowns on click outside
document.addEventListener('click', function(e) {{
    if (!e.target.closest('.card-dropdown')) {{
        document.querySelectorAll('.dropdown-menu.show').forEach(function(m) {{
            m.classList.remove('show');
        }});
    }}
}});

function markApplied(slug) {{
    var triggerContent = JSON.stringify({{slug: slug, applied_at: new Date().toISOString()}});
    var blob = new Blob([triggerContent], {{type: 'application/json'}});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = slug + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
    // Update button state
    var btns = document.querySelectorAll('[data-applied-slug="' + slug + '"]');
    btns.forEach(function(btn) {{
        btn.disabled = true;
        btn.textContent = '\\u2713 Applied';
    }});
    // Close dropdown
    document.querySelectorAll('.dropdown-menu.show').forEach(function(m) {{
        m.classList.remove('show');
    }});
}}
</script>

</body>
</html>"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard generated: {OUTPUT_FILE}")
    print(f"  Total jobs: {total} | New: {new_count} | Evaluated: {eval_count} | Resumes: {resume_count} | Applied: {applied_count}")


def generate_applied_tracker():
    """Generate applied.html — a clean table of all applied jobs."""
    data = load_jobs()
    jobs = data.get("jobs", {})

    applied_summary = data.get("applied_tracker_summary", "")

    applied_jobs = [(slug, job) for slug, job in jobs.items() if job.get("tier") == "applied"]
    applied_jobs.sort(key=lambda x: (x[1].get("application") or {}).get("applied_at", ""), reverse=True)

    # Build JD data for applied jobs
    jd_data = {}
    for slug, job in applied_jobs:
        jd_text = job.get("jd_text")
        if jd_text:
            jd_data[slug] = jd_text
    jd_data_json = json.dumps(jd_data, ensure_ascii=False)

    # Build CSV export data for applied jobs
    applied_csv_rows = []
    for slug, job in applied_jobs:
        ev = job.get("evaluation") or {}
        res = job.get("resume") or {}
        app = job.get("application") or {}
        applied_csv_rows.append({
            "company": job.get("company", ""),
            "title": job.get("title", ""),
            "applied_at": app.get("applied_at", ""),
            "location": job.get("location", ""),
            "salary": job.get("salary", ""),
            "apply_url": job.get("apply_url", ""),
            "resume": res.get("filename", ""),
            "score": ev.get("score", ""),
            "evaluation": ev.get("score_summary", ""),
            "decision": ev.get("apply_decision", ""),
            "interview_chance": ev.get("interview_chance", ""),
            "buyer_type": ev.get("buyer_type", ""),
            "comp_range": ev.get("comp_range", ""),
            "source": job.get("source_platform") or job.get("source", ""),
            "original_tier": app.get("original_tier", ""),
        })
    applied_csv_json = json.dumps(applied_csv_rows, ensure_ascii=False)

    rows = ""
    for slug, job in applied_jobs:
        company = escape(job.get("company", "Unknown"))
        title = escape(job.get("title", "Unknown"))
        application = job.get("application") or {}
        applied_at = format_date(application.get("applied_at"))
        location = escape(job.get("location") or "")
        salary = escape(job.get("salary") or "")
        resume = job.get("resume")
        if resume and resume.get("filename"):
            resume_text = f'{escape(resume.get("variant", ""))} &mdash; <a href="resumes/{escape(resume["filename"])}" target="_blank">{escape(resume["filename"])}</a>'
        else:
            resume_text = "&mdash;"
        score = str(job.get("evaluation", {}).get("score", "&mdash;")) if job.get("evaluation") else "&mdash;"
        jd_btn = build_jd_button_sm(slug, job)

        rows += f"""<tr>
            <td><strong>{company}</strong></td>
            <td>{title}</td>
            <td>{applied_at}</td>
            <td>{location}</td>
            <td>{salary}</td>
            <td>{resume_text}</td>
            <td>{score}</td>
            <td>{jd_btn}</td>
        </tr>"""

    empty_msg = ""
    if not applied_jobs:
        empty_msg = '<p style="text-align:center; color:#6c757d; padding:40px;">No applied jobs yet. Use the dropdown menu on job cards to mark jobs as applied.</p>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Applied Jobs Tracker</title>
<style>
:root {{
    --bg: #f8f9fa;
    --text: #212529;
    --text-muted: #6c757d;
    --border: #dee2e6;
    --accent: #1f4e79;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 20px;
    max-width: 1100px;
    margin: 0 auto;
}}
.header {{
    background: #5e35b1;
    color: white;
    padding: 24px 32px;
    border-radius: 12px;
    margin-bottom: 20px;
}}
.header h1 {{ font-size: 24px; margin-bottom: 4px; }}
.header p {{ font-size: 14px; opacity: 0.9; }}
.run-summary {{
    margin-top: 14px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.12);
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.6;
    border-left: 3px solid rgba(255,255,255,0.4);
    white-space: pre-line;
}}
.nav-links {{
    display: flex;
    gap: 16px;
    margin-bottom: 20px;
    font-size: 14px;
}}
.nav-link {{
    color: var(--accent);
    text-decoration: none;
    padding: 4px 0;
    border-bottom: 2px solid transparent;
}}
.nav-link:hover {{ border-bottom-color: var(--accent); }}
.nav-link.active {{
    font-weight: 600;
    border-bottom-color: #5e35b1;
    color: #5e35b1;
}}
.btn-export {{
    margin-left: auto;
    padding: 6px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    background: #e8f5e9;
    color: #2e7d32;
    border: 1px solid #4caf50;
}}
.btn-export:hover {{ background: #c8e6c9; }}
.applied-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}}
.applied-table th, .applied-table td {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    text-align: left;
}}
.applied-table th {{
    font-weight: 600;
    background: #f3e5f5;
    color: #5e35b1;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.applied-table tr:hover {{ background: #fafafa; }}
.btn-sm {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
}}
.btn-sm.btn-jd {{ background: #e8eaf6; color: #283593; border: 1px solid #5c6bc0; }}
.btn-sm.btn-jd:hover {{ background: #c5cae9; }}
.jd-modal-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    padding: 20px;
}}
.jd-modal-overlay.active {{ display: flex; }}
.jd-modal {{
    background: white;
    border-radius: 12px;
    max-width: 800px;
    width: 100%;
    max-height: 85vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}}
.jd-modal-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
}}
.jd-modal-header h3 {{ font-size: 16px; }}
.jd-modal-close {{
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: var(--text-muted);
    padding: 4px 8px;
    border-radius: 4px;
}}
.jd-modal-close:hover {{ background: var(--bg); color: var(--text); }}
.jd-modal-body {{
    padding: 20px 24px;
    overflow-y: auto;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
</style>
</head>
<body>

<div class="header">
    <h1>&#128236; Applied Jobs Tracker</h1>
    <p>{len(applied_jobs)} application{"s" if len(applied_jobs) != 1 else ""}</p>
    {"<div class='run-summary'>" + escape(applied_summary) + "</div>" if applied_summary else ""}
</div>

<div class="nav-links">
    <a href="dashboard.html" class="nav-link">Dashboard</a>
    <a href="jobs_log.html" class="nav-link">Jobs Log</a>
    <a href="applied.html" class="nav-link active">Applied Tracker</a>
    <button class="btn-export" onclick="exportAppliedCSV()">Export CSV</button>
</div>

{empty_msg if not applied_jobs else f'''<table class="applied-table">
    <thead>
        <tr>
            <th>Company</th><th>Title</th><th>Applied</th>
            <th>Location</th><th>Salary</th><th>Resume</th>
            <th>Score</th><th>JD</th>
        </tr>
    </thead>
    <tbody>{rows}</tbody>
</table>'''}

<div class="jd-modal-overlay" id="jdModal" onclick="if(event.target===this)closeJD()">
    <div class="jd-modal">
        <div class="jd-modal-header">
            <h3 id="jdModalTitle">Job Description</h3>
            <button class="jd-modal-close" onclick="closeJD()">&times;</button>
        </div>
        <div class="jd-modal-body" id="jdModalBody"></div>
    </div>
</div>

<script>
var JD_DATA = {jd_data_json};
var CSV_DATA = {applied_csv_json};
function showJD(slug) {{
    var text = JD_DATA[slug];
    if (!text) {{ alert('No JD available for ' + slug); return; }}
    var title = slug.replace('--', ' — ').replace(/-/g, ' ');
    title = title.replace(/\\b\\w/g, function(c) {{ return c.toUpperCase(); }});
    document.getElementById('jdModalTitle').textContent = title;
    document.getElementById('jdModalBody').textContent = text;
    document.getElementById('jdModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}}
function closeJD() {{
    document.getElementById('jdModal').classList.remove('active');
    document.body.style.overflow = '';
}}
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeJD();
}});
function exportAppliedCSV() {{
    var headers = ["Company","Title","Applied Date","Location","Salary","Apply URL","Resume","Score","Evaluation","Decision","Interview Chance","Buyer Type","Comp Range","Source","Original Tier"];
    var keys = ["company","title","applied_at","location","salary","apply_url","resume","score","evaluation","decision","interview_chance","buyer_type","comp_range","source","original_tier"];
    var csvContent = headers.map(function(h) {{ return '"' + h + '"'; }}).join(",") + "\\n";
    CSV_DATA.forEach(function(row) {{
        var line = keys.map(function(k) {{
            var val = (row[k] == null) ? "" : String(row[k]);
            return '"' + val.replace(/"/g, '""') + '"';
        }}).join(",");
        csvContent += line + "\\n";
    }});
    var blob = new Blob([csvContent], {{ type: "text/csv;charset=utf-8;" }});
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "applied_jobs.csv";
    link.click();
}}
</script>

</body>
</html>"""

    with open(OUTPUT_APPLIED, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Applied tracker generated: {OUTPUT_APPLIED}")


def generate_jobs_log():
    """Generate jobs_log.html — comprehensive log of ALL jobs organized by month."""
    data = load_jobs()
    jobs = data.get("jobs", {})
    stats = data.get("stats", {})
    log_summary = data.get("jobs_log_summary", "")

    current_month = datetime.now().strftime("%Y-%m")

    # Group by month
    months = {}
    for slug, job in jobs.items():
        month = (job.get("first_seen") or "")[:7] or "unknown"
        months.setdefault(month, []).append((slug, job))

    sorted_months = sorted(months.keys(), reverse=True)

    # Build JD data
    jd_data = {}
    for slug, job in jobs.items():
        jd_text = job.get("jd_text")
        if jd_text:
            jd_data[slug] = jd_text
    jd_data_json = json.dumps(jd_data, ensure_ascii=False)

    # Build CSV export data
    csv_rows = []
    for slug, job in jobs.items():
        ev = job.get("evaluation") or {}
        res = job.get("resume") or {}
        tier = job.get("tier", "")
        tc = TIER_CONFIG.get(tier, {})
        csv_rows.append({
            "company": job.get("company", ""),
            "title": job.get("title", ""),
            "tier": tc.get("label", tier),
            "score": ev.get("score", ""),
            "location": job.get("location", ""),
            "salary": job.get("salary", ""),
            "source": job.get("source_platform") or job.get("source", ""),
            "first_seen": job.get("first_seen", ""),
            "apply_url": job.get("apply_url", ""),
            "evaluation": ev.get("score_summary", ""),
            "decision": ev.get("apply_decision", ""),
            "interview_chance": ev.get("interview_chance", ""),
            "buyer_type": ev.get("buyer_type", ""),
            "comp_range": ev.get("comp_range", ""),
            "resume": res.get("filename", ""),
            "seen_count": job.get("seen_count", 1),
        })
    csv_data_json = json.dumps(csv_rows, ensure_ascii=False)

    # Stats
    total = len(jobs)
    eval_count = sum(1 for j in jobs.values() if j.get("evaluation"))
    resume_count = sum(1 for j in jobs.values() if j.get("resume"))
    applied_count = sum(1 for j in jobs.values() if j.get("tier") == "applied")

    tier_priority = {"apply_now": 0, "worth_reviewing": 1, "applied": 2, "low_priority": 3, "filtered_out": 4, "could_not_retrieve": 5}

    sections = ""
    for month in sorted_months:
        month_jobs = months[month]
        month_label = get_month_label(month)
        is_current = (month == current_month)

        # Sort by tier priority then first_seen desc
        month_jobs.sort(key=lambda x: (
            tier_priority.get(x[1].get("tier", "could_not_retrieve"), 5),
            x[1].get("first_seen", ""),
        ))

        rows = ""
        for slug, job in month_jobs:
            company = escape(job.get("company", "Unknown"))
            title = escape(job.get("title", "Unknown"))
            tier = job.get("tier", "could_not_retrieve")
            tc = TIER_CONFIG.get(tier, {})
            tier_label = f'{tc.get("emoji", "")} {tc.get("label", tier)}'
            tier_color = tc.get("color", "#333")
            location = escape(job.get("location") or "")
            salary = escape(job.get("salary") or "")
            source = escape(job.get("source_platform") or job.get("source") or "")
            first_seen = short_date(job.get("first_seen"))

            score = ""
            eval_summary = ""
            if job.get("evaluation"):
                score = str(job["evaluation"].get("score", ""))
                eval_summary = escape(job["evaluation"].get("score_summary", ""))

            resume_info = ""
            if job.get("resume") and job["resume"].get("filename"):
                variant = escape(job["resume"].get("variant", ""))
                fname = escape(job["resume"]["filename"])
                resume_info = f'{variant} &mdash; <a href="resumes/{fname}" target="_blank">{fname}</a>'

            jd_btn = build_jd_button_sm(slug, job)

            rows += f"""<tr>
                <td><strong>{company}</strong></td>
                <td>{title}</td>
                <td style="color:{tier_color};white-space:nowrap;">{tier_label}</td>
                <td>{score}</td>
                <td>{location}</td>
                <td>{salary}</td>
                <td>{source}</td>
                <td>{first_seen}</td>
                <td class="eval-cell">{eval_summary}</td>
                <td>{resume_info}</td>
                <td>{jd_btn}</td>
            </tr>"""

        open_attr = "open" if is_current else ""
        sections += f"""
        <details class="month-section" {open_attr}>
            <summary class="month-header">
                &#128197; {month_label} ({len(month_jobs)} jobs)
            </summary>
            <div class="month-content">
                <table class="log-table">
                    <thead>
                        <tr>
                            <th>Company</th><th>Title</th><th>Tier</th><th>Score</th>
                            <th>Location</th><th>Salary</th><th>Source</th><th>First Seen</th>
                            <th>Evaluation</th><th>Resume</th><th>JD</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </details>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jobs Log</title>
<style>
:root {{
    --bg: #f8f9fa;
    --text: #212529;
    --text-muted: #6c757d;
    --border: #dee2e6;
    --accent: #1f4e79;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 20px;
    max-width: 1800px;
    margin: 0 auto;
}}
.header {{
    background: var(--accent);
    color: white;
    padding: 24px 32px;
    border-radius: 12px;
    margin-bottom: 20px;
}}
.header h1 {{ font-size: 24px; margin-bottom: 8px; }}
.run-summary {{
    margin-top: 14px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.12);
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.6;
    border-left: 3px solid rgba(255,255,255,0.4);
    white-space: pre-line;
}}
.stats {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
}}
.stat {{
    background: rgba(255,255,255,0.15);
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 13px;
}}
.stat strong {{ font-size: 18px; display: block; }}
.nav-links {{
    display: flex;
    gap: 16px;
    margin-bottom: 20px;
    font-size: 14px;
}}
.nav-link {{
    color: var(--accent);
    text-decoration: none;
    padding: 4px 0;
    border-bottom: 2px solid transparent;
}}
.nav-link:hover {{ border-bottom-color: var(--accent); }}
.nav-link.active {{
    font-weight: 600;
    border-bottom-color: var(--accent);
}}
.btn-export {{
    margin-left: auto;
    padding: 6px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    background: #e8f5e9;
    color: #2e7d32;
    border: 1px solid #4caf50;
}}
.btn-export:hover {{ background: #c8e6c9; }}
.month-section {{
    margin-bottom: 16px;
    background: white;
    border-radius: 8px;
    border: 1px solid var(--border);
    overflow: hidden;
}}
.month-header {{
    padding: 12px 20px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    background: #eef2f7;
    user-select: none;
}}
.month-header:hover {{ background: #e3e8ef; }}
.month-content {{
    padding: 0;
    overflow-x: auto;
}}
.log-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}}
.log-table th, .log-table td {{
    padding: 8px 10px;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
}}
.log-table th {{
    font-weight: 600;
    background: var(--bg);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
    position: sticky;
    top: 0;
}}
.log-table tr:hover {{ background: #fafafa; }}
.eval-cell {{
    max-width: 500px;
    white-space: normal;
    font-size: 12px;
    line-height: 1.4;
}}
.btn-sm {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
}}
.btn-sm.btn-jd {{ background: #e8eaf6; color: #283593; border: 1px solid #5c6bc0; }}
.btn-sm.btn-jd:hover {{ background: #c5cae9; }}
.jd-modal-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    padding: 20px;
}}
.jd-modal-overlay.active {{ display: flex; }}
.jd-modal {{
    background: white;
    border-radius: 12px;
    max-width: 800px;
    width: 100%;
    max-height: 85vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}}
.jd-modal-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
}}
.jd-modal-header h3 {{ font-size: 16px; }}
.jd-modal-close {{
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: var(--text-muted);
    padding: 4px 8px;
    border-radius: 4px;
}}
.jd-modal-close:hover {{ background: var(--bg); color: var(--text); }}
.jd-modal-body {{
    padding: 20px 24px;
    overflow-y: auto;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
</style>
</head>
<body>

<div class="header">
    <h1>&#128218; Jobs Log</h1>
    <div class="stats">
        <div class="stat"><strong>{total}</strong> Total</div>
        <div class="stat"><strong>{eval_count}</strong> Evaluated</div>
        <div class="stat"><strong>{resume_count}</strong> Resumes</div>
        <div class="stat"><strong>{applied_count}</strong> Applied</div>
    </div>
    {"<div class='run-summary'>" + escape(log_summary) + "</div>" if log_summary else ""}
</div>

<div class="nav-links">
    <a href="dashboard.html" class="nav-link">Dashboard</a>
    <a href="jobs_log.html" class="nav-link active">Jobs Log</a>
    <a href="applied.html" class="nav-link">Applied Tracker</a>
    <button class="btn-export" onclick="exportJobsCSV()">Export CSV</button>
</div>

{sections}

<div class="jd-modal-overlay" id="jdModal" onclick="if(event.target===this)closeJD()">
    <div class="jd-modal">
        <div class="jd-modal-header">
            <h3 id="jdModalTitle">Job Description</h3>
            <button class="jd-modal-close" onclick="closeJD()">&times;</button>
        </div>
        <div class="jd-modal-body" id="jdModalBody"></div>
    </div>
</div>

<script>
var JD_DATA = {jd_data_json};
var CSV_DATA = {csv_data_json};
function showJD(slug) {{
    var text = JD_DATA[slug];
    if (!text) {{ alert('No JD available for ' + slug); return; }}
    var title = slug.replace('--', ' — ').replace(/-/g, ' ');
    title = title.replace(/\\b\\w/g, function(c) {{ return c.toUpperCase(); }});
    document.getElementById('jdModalTitle').textContent = title;
    document.getElementById('jdModalBody').textContent = text;
    document.getElementById('jdModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}}
function closeJD() {{
    document.getElementById('jdModal').classList.remove('active');
    document.body.style.overflow = '';
}}
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeJD();
}});
function exportJobsCSV() {{
    var headers = ["Company","Title","Tier","Score","Location","Salary","Source","First Seen","Apply URL","Evaluation","Decision","Interview Chance","Buyer Type","Comp Range","Resume","Seen Count"];
    var keys = ["company","title","tier","score","location","salary","source","first_seen","apply_url","evaluation","decision","interview_chance","buyer_type","comp_range","resume","seen_count"];
    var csvContent = headers.map(function(h) {{ return '"' + h + '"'; }}).join(",") + "\\n";
    CSV_DATA.forEach(function(row) {{
        var line = keys.map(function(k) {{
            var val = (row[k] == null) ? "" : String(row[k]);
            return '"' + val.replace(/"/g, '""') + '"';
        }}).join(",");
        csvContent += line + "\\n";
    }});
    var blob = new Blob([csvContent], {{ type: "text/csv;charset=utf-8;" }});
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "jobs_log.csv";
    link.click();
}}
</script>

</body>
</html>"""

    with open(OUTPUT_JOBS_LOG, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Jobs log generated: {OUTPUT_JOBS_LOG}")


if __name__ == "__main__":
    generate_dashboard()
    generate_jobs_log()
    generate_applied_tracker()

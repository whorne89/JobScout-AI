# JobScout AI

Automated job search pipeline powered by [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Scans Gmail for job alerts, evaluates candidate fit with a rigorous scoring engine, generates tailored PDF resumes, and builds an interactive HTML dashboard — fully autonomous, no human in the loop.

## How It Works

JobScout runs as a Claude Code autonomous pipeline in 4 phases:

**Phase 1 — Gmail Scan**
Searches your Gmail for unread job alert emails (LinkedIn, Indeed, Built In, etc.), extracts job postings, deduplicates against your database, fetches full job descriptions via headless Playwright browser, and assigns initial tiers.

**Phase 2 — Evaluation**
Each job gets a deep individual evaluation against your candidate profile. An 8-step structured rubric scores fit (1-10) covering: strong matches, partial matches, missing qualifications, hard technical requirements, domain gap severity, compounding risk analysis, compensation alignment, and a final synthesis with validation checkpoint. Produces a YES/NO/CAVEATS apply decision with interview probability.

**Phase 3 — Resume Generation**
For top-tier jobs, generates a tailored PDF resume by reframing, reordering, and weaving JD keywords into your base resume. Hard rules prevent fabrication — no fake titles, no invented technologies, no papering over dealbreaker gaps. Every change is recorded with verbatim before/after text.

**Phase 4 — Dashboard**
Generates three HTML files: a main dashboard with tier-based sections and JD viewer, an applied tracker, and a comprehensive jobs log organized by month.

## Features

- **Evaluation engine** with compounding risk scoring, buyer-type analysis (business vs. technical), and domain gap severity assessment
- **Resume tailoring** with SE (Sales Engineer) and SC (Solutions Consultant) variants, adaptive 2-page PDF layout
- **Playwright JD fetcher** with LinkedIn modal dismissal and multi-fallback strategy (Playwright > WebFetch > WebSearch)
- **Sighting tracking** — deduplicates jobs and tracks repeat appearances across emails
- **Interactive dashboard** with collapsible tier sections, JD modal viewer, search/filter, "Copy to Claude" for manual review, and "Mark Applied" workflow
- **Crash resilience** — saves `data/jobs.json` after every phase

## Job Tiers

| Tier | Criteria |
|------|----------|
| Apply Now | Score 7+, no dealbreakers, interview chance 30%+ |
| Worth Reviewing | Score 5-6, gaps but viable, interview 15-30% |
| Applied | User-assigned via dashboard dropdown |
| Low Priority | Multiple concerns, niche domain, comp below target |
| Filtered Out | Hard blockers, wrong role type, or dealbreaker gaps |
| Could Not Retrieve | No extractable data from email |

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) with Gmail MCP integration
- Python 3.7+
- Gmail account with job alert emails configured

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/whorne89/JobScout-AI.git
cd JobScout-AI
```

### 2. Install Python dependencies

```bash
pip install playwright reportlab PyPDF2
playwright install chromium
```

### 3. Create your candidate profile

Copy the example template and fill in your details:

```bash
cp profile/candidate-profile.example.md profile/candidate-profile.md
```

Edit `profile/candidate-profile.md` with:
- Your name, target roles, target compensation range
- Current and previous roles with responsibilities
- Technical skills, platforms, integrations
- Education and certifications
- Strengths, growth areas, and deal-breakers

### 4. Create your base resumes

Copy the example templates:

```bash
cp profile/base-resume-SE.example.md profile/base-resume-SE.md
cp profile/base-resume-SC.example.md profile/base-resume-SC.md
```

Edit each with your actual resume content in markdown format. The pipeline uses these as the foundation for tailored resumes — it reframes and reorders content but never fabricates.

Alternatively, place your source PDF resumes in `profile/` and run `profile/update_resumes.bat` to extract markdown automatically.

### 5. Initialize the jobs database

```bash
cp data/jobs.example.json data/jobs.json
```

### 6. Set up Gmail MCP

Claude Code needs access to your Gmail to scan job alerts. Follow the [Claude Code MCP setup guide](https://docs.anthropic.com/en/docs/claude-code) to enable the Gmail integration.

### 7. Configure job alert emails

Set up job alerts on platforms like LinkedIn, Indeed, Built In, Glassdoor, etc. to send email notifications to your Gmail. The more sources, the better coverage.

## Usage

Open Claude Code in the project directory and run the pipeline:

```bash
cd JobScout-AI
claude
```

Then say:

```
Run the full JobScout pipeline
```

The pipeline runs fully autonomously — no confirmation prompts, no manual steps. Results are saved after each phase. When complete, open `dashboard.html` in your browser.

## Customization

The pipeline behavior is defined in `CLAUDE.md`. Key areas you may want to customize:

- **Title filters** — which job titles to keep vs. auto-skip (Phase 1, Step 1.4)
- **Target compensation** — the OTE range used for scoring adjustments (Phase 2, Step 2.3g)
- **Evaluation criteria** — compounding risk rules, interview chance anchors (Phase 2, Steps 2.3e-2.3h)
- **Resume variants** — SE vs. SC determination logic (Phase 3, Step 3.1)

## Project Structure

```
JobScout-AI/
├── CLAUDE.md                    # Pipeline specification (the "brain")
├── CHANGELOG.md                 # Release history
├── ROADMAP.md                   # Planned features
├── VERSION                      # Current version
├── data/
│   ├── jobs.json                # Job database (gitignored)
│   └── jobs.example.json        # Empty schema template
├── profile/
│   ├── candidate-profile.md     # Your profile (gitignored)
│   ├── base-resume-SE.md        # SE variant base (gitignored)
│   ├── base-resume-SC.md        # SC variant base (gitignored)
│   └── *.example.md             # Templates for new users
├── resumes/
│   ├── *.pdf                    # Generated resumes (gitignored)
│   └── queue/                   # Manual resume triggers
├── applied/
│   └── queue/                   # Applied status triggers
├── scripts/
│   ├── dashboard.py             # HTML dashboard generator
│   ├── build_resume_pdf.py      # PDF resume builder (reportlab)
│   ├── fetch_jd.py              # Playwright JD fetcher
│   ├── extract_resume_pdf.py    # PDF-to-markdown extractor
│   └── log.py                   # Pipeline logging utility
├── logs/
│   └── pipeline.log             # Run history (gitignored)
├── dashboard.html               # Main dashboard (gitignored)
├── applied.html                 # Applied tracker (gitignored)
└── jobs_log.html                # Jobs log (gitignored)
```

## Technical Notes

- **Playwright JD fetcher** handles LinkedIn sign-in modal dismissal and "Show more" expansion. Falls back to WebFetch then WebSearch if blocked.
- **Resume PDF builder** uses reportlab with adaptive spacing via binary search (levels -2 to +5) targeting exactly 2 pages with 85%+ page 2 fill.
- **JD text storage** — Phase 1 stores fetched JDs in the database so Phase 2 doesn't re-fetch. Major token savings.
- **UTF-8 encoding** — all file I/O uses explicit `encoding='utf-8'` (required on Windows where default is cp1252).
- **Evaluation architecture** — each job is evaluated individually (never batched) to maintain quality. Evaluations must match the rigor of a manual deep-dive analysis.

## License

All rights reserved. This project is publicly visible for reference but may not be copied, modified, or distributed without explicit permission.

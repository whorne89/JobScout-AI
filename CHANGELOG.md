# Changelog

All notable changes to JobScout will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-03-10

First formal release. Everything before this was iterative development.

### Core Pipeline
- **4-phase automated pipeline**: Gmail scan → Evaluate → Resume generation → Dashboard
- **Gmail MCP integration**: Scans unread job alert emails with configurable date filters
- **Job extraction**: Pulls company, title, location, salary, apply URL, source from email bodies
- **Title pre-filter**: Auto-keeps SE/SC/pre-sales roles, auto-skips irrelevant titles
- **Dedup with sighting tracking**: Slug-based dedup, `seen_count`, `sightings` array with source/date history
- **JD fetching (3-tier)**: Playwright (primary) → WebFetch → WebSearch fallback
- **Playwright JD fetcher** (`scripts/fetch_jd.py`): Headless Chromium with LinkedIn sign-in modal dismissal, "Show more" expansion. 100% success rate on LinkedIn.
- **JD text storage**: Full JD stored in `jd_text` field, reused across phases to save tokens

### Evaluation Engine
- **Structured 8-step evaluation** (Steps 2.3a–2.3h): Strong matches → Partial matches → Missing quals → Hard tech requirements → Domain gap severity → Compounding risk → Comp adjustment → Score synthesis
- **One agent per job**: No batched evaluations — each job gets individual deep-dive attention
- **Compounding risk rules**: 4 specific penalty combinations for stacking gaps
- **Score validation checkpoint**: "Would a hiring manager actually move the candidate forward?"
- **Exhaustive JD fetch**: 5 search strategies required before skipping evaluation
- **Buyer type analysis**: Business vs. technical vs. mixed buyer classification
- **Tier re-assessment**: Evaluation results update initial tier assignment

### Resume Generation
- **PDF output** via `scripts/build_resume_pdf.py` (reportlab)
- **SE and SC variants**: Sales Engineer and Solutions Consultant base resumes
- **Adaptive 2-page layout**: Binary search spacing algorithm targeting exactly 2 pages with ≥85% page 2 fill
- **Verbatim change tracking**: Before/after diffs stored in `resume.changes` for dashboard display
- **Hard rules enforcement**: Never fabricates experience, changes titles, or adds unlearned technologies
- **Auto-generation for `apply_now`**, manual queue trigger for `worth_reviewing`

### Dashboard (`dashboard.html`)
- **Tier-based sections**: Apply Now, Worth Reviewing, Applied, Low Priority, Filtered Out, Could Not Retrieve
- **All sections collapsible**: Apply Now through Low Priority expanded by default, Filtered Out and Could Not Retrieve collapsed
- **Monthly archives**: Previous months collapse into accordion sections at the bottom
- **Full job cards** (Apply Now, Worth Reviewing): Score badge, evaluation accordion, resume changes accordion, all action buttons
- **Compact cards** (Low Priority, Applied): Single-row layout with buttons grouped on the right
- **Filter bar**: Tier filter buttons, text search, sort by newest/company/score
- **JD modal viewer**: Inline modal overlay with full JD text, Escape key support
- **Copy to Claude**: One-click copy of full job context (evaluation, resume changes, profile references)
- **Resume queue**: "Add to Queue" button downloads trigger file for manual resume generation
- **Dropdown menus**: Kebab (⋮) menu on all cards with "Mark Applied" action
- **Badges**: NEW, REPEAT (with sighting tooltip), source, date, UNCONFIRMED
- **Run summary**: Pipeline-generated narrative summary in header

### Applied Tracker (`applied.html`)
- **Clean data table**: Company, Title, Applied Date, Location, Salary, Resume Used, Score, View JD
- **Sorted by applied date** (newest first)
- **Pipeline summary box** in header (populated each run)
- **JD modal viewer**: Same inline modal as dashboard

### Jobs Log (`jobs_log.html`)
- **Comprehensive log**: ALL jobs with ALL data, organized by month
- **Collapsible month sections**: Current month expanded, previous months collapsed (native `<details>`)
- **Full detail per job**: Tier, score, location, salary, source, first seen, evaluation summary, resume info, JD link
- **Pipeline summary box** in header (populated each run)
- **Stats header**: Total, evaluated, resumes, applied counts

### Applied Tier & Queue
- **`applied` tier**: Purple theme, user-assigned via dashboard dropdown
- **Trigger file pattern**: Dashboard downloads `[slug].json` to `applied/queue/`, pipeline processes in Phase 4
- **Preserves original tier**: `application.original_tier` tracks what the job was before being marked applied

### Navigation
- **3-page nav bar**: Dashboard → Jobs Log → Applied Tracker on all pages
- **Active page highlighting**: Current page link is bold with accent underline

### Infrastructure
- **Pipeline logging** (`scripts/log.py`): Structured logging to `logs/pipeline.log` with RUN/INFO/DETAIL/WARN/ERROR levels
- **Crash resilience**: `data/jobs.json` saved after every phase
- **CLAUDE.md pipeline spec**: Complete autonomous execution instructions — no human in the loop
- **UTF-8 encoding**: All file I/O uses explicit UTF-8 for Windows compatibility

### Tier System
| Tier | Key | Assignment |
|------|-----|------------|
| ⭐ Apply Now | `apply_now` | Pipeline: pre-sales confirmed, no blockers |
| ✅ Worth Reviewing | `worth_reviewing` | Pipeline: good match with some gaps |
| 📬 Applied | `applied` | User: marked via dashboard dropdown |
| ⚠️ Low Priority | `low_priority` | Pipeline: multiple concerns |
| ❌ Filtered Out | `filtered_out` | Pipeline: hard blockers or wrong role |
| ❓ Could Not Retrieve | `could_not_retrieve` | Pipeline: no extractable data |

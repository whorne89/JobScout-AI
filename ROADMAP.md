# Roadmap

## Open-Source Readiness (Pre-GitHub)

Before publishing to GitHub, the project needs to be fully genericized so anyone can clone it and run their own job search pipeline.

### Data Separation
- [ ] `.gitignore` all personal data: `data/jobs.json`, `profile/`, `resumes/`, `logs/`, generated HTML files
- [ ] Create `data/jobs.example.json` with empty schema (no real jobs)
- [ ] Create `profile/candidate-profile.example.md` with template/placeholder content
- [ ] Create `profile/base-resume-SE.example.md` and `profile/base-resume-SC.example.md` with template structure
- [ ] Ensure no personal data (names, emails, companies applied to) leaks into committed files

### First-Run Setup Experience
- [ ] Detect first run (no `data/jobs.json` exists) and guide the user through setup
- [ ] Prompt for candidate profile creation or point to the example template
- [ ] Prompt for base resume creation (both variants) or point to examples
- [ ] Explain Gmail MCP setup requirements (Claude Code Gmail integration)
- [ ] Create initial `data/jobs.json` with empty schema on first run
- [ ] Create required directories (`data/`, `profile/`, `resumes/`, `resumes/queue/`, `applied/queue/`, `logs/`)

### Configuration
- [ ] Extract hardcoded job title filters (KEEP/SKIP lists) into a config file users can customize
- [ ] Extract target compensation range ($155K-$185K OTE) into config
- [ ] Extract candidate-specific evaluation criteria into config (buyer type preferences, years of experience, etc.)
- [ ] Make the CLAUDE.md evaluation rubric parameterizable based on config

### Documentation
- [ ] README.md: Project overview, features, screenshots, setup instructions, how it works
- [ ] Installation guide: Python dependencies, Playwright setup, Claude Code setup, Gmail MCP
- [ ] `requirements.txt` or `pyproject.toml` for Python dependencies

## Future Features

### Pipeline Enhancements
- [ ] Interview prep phase: Auto-generate interview prep notes for applied jobs
- [ ] Cover letter generation: Tailored cover letters alongside resumes
- [ ] Application tracking: Response tracking (heard back / rejected / interview scheduled)
- [ ] Email notifications: Summary email after each pipeline run

### Dashboard Enhancements
- [ ] Run Pipeline button: Launch the pipeline directly from the dashboard (requires local server or custom protocol handler since browsers block launching executables from HTML)
- [ ] Dark mode toggle
- [ ] Dashboard auto-refresh / file watcher
- [ ] Export to CSV/Excel from jobs log
- [ ] Charts/graphs: tier distribution, score histogram, applications over time

### Infrastructure
- [ ] One-click pipeline launcher: Batch file / shell script that launches `claude -p` from outside Claude Code (currently cmd.exe has PATH/environment issues preventing this on Windows)
- [ ] Scheduled runs (cron / Task Scheduler integration)
- [ ] Multi-platform testing (macOS, Linux)
- [ ] Test suite for dashboard.py and build_resume_pdf.py

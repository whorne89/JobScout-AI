# JobScout — Pipeline Orchestrator

## AUTOMATION MODE

You are running in **AUTOMATED** mode. There is NO human in the loop.
Execute the full pipeline end-to-end without asking for confirmation.
Save `data/jobs.json` after every phase for crash resilience.

## File Paths

- **Jobs database:** `data/jobs.json`
- **Candidate profile:** `profile/candidate-profile.md`
- **Base resumes (markdown):** `profile/base-resume-SE.md`, `profile/base-resume-SC.md`
- **Base resumes (source PDFs):** `profile/William Horne - Sales Engineer.pdf`, `profile/William Horne - Solutions Consultant.pdf`
- **Resume queue (manual triggers):** `resumes/queue/[slug].json`
- **Applied queue (manual triggers):** `applied/queue/[slug].json`
- **Generated resumes:** `resumes/` (PDF format)
- **Dashboard output:** `dashboard.html`
- **Applied tracker output:** `applied.html`
- **Jobs log output:** `jobs_log.html`
- **Dashboard generator:** `scripts/dashboard.py`
- **PDF resume builder:** `scripts/build_resume_pdf.py`
- **JD fetcher (Playwright):** `scripts/fetch_jd.py`
- **Logging utility:** `scripts/log.py`
- **Pipeline log:** `logs/pipeline.log`

## Logging

Log every significant action using: `python scripts/log.py LEVEL "message"`

Levels: `RUN` (run start/end markers), `INFO`, `DETAIL`, `WARN`, `ERROR`

## Startup Sequence

1. Log: `RUN "Pipeline started"`
2. Read `data/jobs.json` — load existing jobs, get `last_scan` timestamp
   - Log: `INFO "Loaded jobs.json: X jobs, last_scan=YYYY-MM-DD"`
3. Read `profile/candidate-profile.md` — load candidate profile
   - Log: `INFO "Loaded candidate profile"`
4. Read base resume markdown files: `profile/base-resume-SE.md` and `profile/base-resume-SC.md`
   - Log: `INFO "Loaded base resumes: SE, SC"`
5. Check `resumes/queue/` for manual resume trigger files (process in Phase 3)
   - Log: `INFO "Queue check: X trigger files found"` (or `"Queue check: no trigger files"`)
6. Load Gmail MCP tools via `ToolSearch` query: `+gmail search`
7. Proceed through Phases 1–4 in order

---

## PHASE 1 — Gmail Scan

### Step 1.1 — Compute Date Filter

Log: `INFO "Phase 1: Gmail scan started, date filter: after:YYYY/MM/DD"`

Use `last_scan` from jobs.json to set the date filter:
- If `last_scan` is null (first run): use `after:` 7 days ago
- Otherwise: use `after:` the `last_scan` date (format `YYYY/MM/DD`)

### Step 1.2 — Search Gmail

Use `mcp__claude_ai_Gmail__gmail_search_messages` with:
- **Primary query:** `is:unread ("job alert" OR "jobs alert" OR "new jobs" OR "job matches" OR "jobs matching" OR "jobs for you" OR "job recommendations" OR "new listings" OR "you may be a fit" OR "actively hiring" OR "hiring now") after:YYYY/MM/DD`
- **maxResults:** 30

If primary returns < 3 results, try **fallback query:**
- `is:unread (subject:alert OR subject:hiring OR subject:jobs OR subject:engineer OR subject:consultant OR subject:matches) after:YYYY/MM/DD`

### Step 1.3 — Read Emails and Extract Jobs

For each email, use `mcp__claude_ai_Gmail__gmail_read_message` to get the body.
Log: `DETAIL "Reading email: [subject snippet]"` for each email.
Log: `DETAIL "Extracted job: [Company] - [Title]"` for each job found.

Extract from each email:
- **Company** name
- **Job Title**
- **Location** (city, remote, hybrid)
- **Salary/Comp** (if listed)
- **Apply URL** (best link from the email)
- **Source Platform** (LinkedIn, Indeed, Built In, etc.)

### Step 1.4 — Title Pre-Filter

Log: `DETAIL "Title filter: KEEP [Title]"` or `DETAIL "Title filter: SKIP [Title]"` for each job.

**KEEP** these title types:
- Sales Engineer, Solutions Engineer, Solutions Consultant, Pre-Sales Engineer
- Technical Consultant, Implementation Consultant, Solutions Architect (pre-sales)
- Customer Engineer (pre-sales)

**AUTO-SKIP** these title types:
- Data Engineer, Software Engineer, Developer, DevOps, Security Analyst
- Network Engineer, Data Scientist, Accountant, Marketing Manager, HR, Recruiter

### Step 1.5 — Dedup Against Existing Jobs

Generate slug: `company--title` (lowercase, spaces→hyphens, strip special chars).

For each extracted job:
- If slug exists in jobs.json: increment `seen_count`, update `last_seen`, append to `sightings` array, keep existing data
  - Append: `{"date": "ISO timestamp", "source": "LinkedIn/Indeed/etc", "email_subject": "subject snippet"}`
  - Log: `DETAIL "Dedup: existing [slug], seen_count now X"`
- If new: create new job entry with `is_new: true`, `seen_count: 1`, `sightings: [{"date": ..., "source": ..., "email_subject": ...}]`
  - Log: `DETAIL "Dedup: new job [slug]"`

### Step 1.6 — Validity Check (New Jobs Only)

For each new job, attempt to fetch the JD:
1. **Playwright** — `python scripts/fetch_jd.py "[apply_url]"` (captures stdout)
   - If exit code 0 and output has real content: JD fetched successfully
   - **Store the full JD text in `jd_text` field** on the job entry
   - Log: `DETAIL "JD fetch [slug]: Playwright OK"`
2. If Playwright fails: **WebFetch** the apply URL (one attempt)
   - Check: Does the page confirm the role title? Is the JD accessible?
   - If successful, store result in `jd_text`
   - Log: `DETAIL "JD fetch [slug]: WebFetch OK"` or `WARN "JD fetch [slug]: WebFetch failed, trying WebSearch"`
3. If WebFetch fails or returns thin content: **WebSearch** fallback
   - Query: `"[Company]" "[Job Title]" job description requirements responsibilities`
   - Try to find the JD on job boards (Greenhouse, Lever, Ashby, Built In)
   - If found, store in `jd_text`
4. Set `jd_fetched: true` if JD was retrieved, `false` if not
5. If JD could not be fetched at all, set `unconfirmed: true`
   - Log: `WARN "JD fetch [slug]: all methods failed, marking unconfirmed"`

**Important:** Always store the fetched JD text in `jd_text` so Phase 2 can reuse it and the dashboard can display it.

### Step 1.7 — Tier Assignment

Based on JD content (or email content if JD not fetched), assign tier:

| Tier | Key (`tier`) | Criteria |
|------|-------------|----------|
| ⭐ Apply Now | `apply_now` | Pre-sales confirmed, no hard blockers, years in range (< 7 required), comp signals OK |
| ✅ Worth Reviewing | `worth_reviewing` | Senior/Lead title, explicit years req at/above level, one domain gap, otherwise OK |
| ⚠️ Low Priority | `low_priority` | Multiple open questions, niche domain, comp well below $155K target |
| ❌ Filtered Out | `filtered_out` | JD explicitly requires domain-specific experience Will lacks (e.g., "5+ years cybersecurity sales"), confirmed post-sales/SWE role, or hard experience blocker. Do NOT filter based on industry/domain alone — only filter when the JD demands specific expertise he doesn't have |
| ❓ Could Not Retrieve | `could_not_retrieve` | Email so broken no title/company/link extractable at all |
| 📬 Applied | `applied` | **User-assigned only** — set via dashboard dropdown "Mark Applied". Pipeline never assigns this tier automatically. |

Set `tier_reason` with a 1-sentence explanation of why this tier was assigned.
Log: `INFO "Tier: [slug] → [tier] — [tier_reason]"` for each job.

### Step 1.8 — Save

Update `last_scan` to current ISO timestamp.
Update `stats.total_jobs`.
Save `data/jobs.json`.
Log: `INFO "Phase 1 complete: X emails, Y new jobs, Z updated"`

---

## PHASE 2 — Evaluation

**CRITICAL: Each evaluation must be as rigorous as a manual deep-dive analysis.**
Every job gets focused, individual attention — never rush through evaluations.

Process jobs in priority order: `apply_now` first, then `worth_reviewing`.
Skip `applied`, `low_priority`, `filtered_out`, `could_not_retrieve`.
Log: `INFO "Phase 2: X jobs to evaluate"`

### Evaluation Architecture

**Each job MUST be evaluated individually.** When spawning agents for evaluation,
give each job its own agent with the full candidate profile and JD content.
Do NOT batch multiple evaluations into a single agent — this degrades quality.

For each job needing evaluation (`evaluation` is null):

#### Step 2.1 — Fetch Full JD (Exhaustive)

**Do NOT evaluate off partial JDs or search snippets.** You need the actual job posting
with full requirements, qualifications, and responsibilities. A partial JD leads to
over-scoring (missing hard requirements) or under-scoring (missing context that softens gaps).

Fetch strategy (check stored JD first, then try all methods until you get the full JD):

0. **Check `jd_text`** — If the job already has `jd_text` stored from Phase 1, use it directly.
   - Log: `DETAIL "Eval [slug]: Using stored JD (Phase 1)"`
1. If no stored JD: **Playwright** — `python scripts/fetch_jd.py "[apply_url]"` (primary method)
   - Captures stdout as the full JD text. Store in `jd_text`.
   - If exit code 0 and content passes validation: done
   - Log: `DETAIL "Eval [slug]: Full JD fetched via Playwright"`
2. If Playwright fails: **WebFetch** the apply URL directly
   - Log: `WARN "Eval [slug]: Playwright failed, trying WebFetch"`
3. If fails: **WebSearch** with ATS site filter:
   `"[Company]" "[Job Title]" site:greenhouse.io OR site:lever.co OR site:ashbyhq.com OR site:jobs.lever.co`
4. If fails: **WebSearch** broad:
   `"[Company]" "[Job Title]" job description requirements qualifications responsibilities`
5. If fails: **WebSearch** with location:
   `"[Company]" "[Job Title]" "[New York]" OR "remote" job posting`
6. If all fail: **Do NOT evaluate.** Set `evaluation_blocked: true` with reason, skip this job.
   - Log: `WARN "Eval [slug]: Could not retrieve full JD after 5 attempts, skipping"`

**Validation:** After fetching, confirm the JD contains:
- A requirements/qualifications section (not just a summary blurb)
- Specific technical skills, tools, or domain knowledge listed
- Years of experience requirement

If you only have a 2-3 sentence summary from a job board, that's NOT a full JD. Keep searching.

Log: `DETAIL "Eval [slug]: Full JD fetched via [method]"` on success.

#### Step 2.2 — Company Research

WebSearch: `[Company] funding product customers 2025 2026`
Log: `DETAIL "Eval [slug]: company research complete"`

Research and determine:
- **Funding stage & recent rounds** — early stage (Series A/B) vs. growth (C+) vs. public
- **Product focus & ICP** — what does the product do, who buys it?
- **GTM motion** — product-led growth vs. sales-led enterprise
- **Team size signals** — startup (<100), growth (100-500), enterprise (500+)
- **Buyer type** (CRITICAL — this directly affects interview probability):
  - **"business"** — the product is sold to business users, ops teams, HR, finance, executives. Will's background aligns well.
  - **"technical"** — the product is sold to developers, DevOps, security engineers, or technical teams. Will lacks experience selling to this persona. This is a significant disadvantage.
  - **"mixed"** — sold to both; evaluate which side the SE role sits on.

#### Step 2.3 — Structured Evaluation

**You MUST follow this exact sequence.** Do not skip steps or combine them.
Score on **FIT** (not interest). Reference `profile/candidate-profile.md`.

##### Step 2.3a — Identify Strong Matches

List every JD requirement that Will's background **directly satisfies**.
Each match must cite a **specific credential or experience**, not a vague claim.

✅ Good: "Technical discovery and POC delivery — Will leads POC engagements and technical demos at iObeya for enterprise prospects"
❌ Bad: "Enterprise experience — Will has enterprise experience"

##### Step 2.3b — Identify Partial Matches

List JD requirements where Will has **adjacent but not direct** experience.
For each, name the **specific gap** between what the JD asks and what Will has.

⚠️ Good: "4+ years as Sales Engineer with quota — Will has ~3.5 years in customer-facing technical roles but title has been CSM/Consultant, not SE. The title mismatch and slightly short years are both risk factors."
❌ Bad: "SE experience — Will has some relevant experience"

##### Step 2.3c — Identify Missing Qualifications

List JD requirements Will **does not meet**. For each, classify as:
- **Dealbreaker:** The JD frames this as essential AND it's core to daily work (e.g., "must have SAML/OIDC experience" for an identity platform SE role)
- **Nice-to-have:** Listed as preferred/bonus, OR it's domain knowledge that can be learned on the job

##### Step 2.3d — Check for Hard Technical Requirements

**This step catches the Staffbase-type error.** Scan the JD for:
- Specific protocols or standards (SAML, OIDC, OAuth, LDAP, SCIM, etc.)
- Specific programming languages or frameworks the SE must know
- Specific methodologies (web development, data modeling, ML/AI engineering)
- Specific certifications required

For each hard technical requirement found, check: Does Will have this? If NO, flag it explicitly.
Technical hard requirements that Will lacks are usually **dealbreakers**, not nice-to-haves,
especially at the senior level.

##### Step 2.3e — Assess Domain Gap Severity

**Not all domain gaps are equal.** Determine severity:

- **Minor (no score penalty):** JD lists domain knowledge as "nice-to-have" or "preferred." The role is functionally a standard SE role that happens to be in an unfamiliar industry. Will can learn the domain.
- **Moderate (-1 to score, -10% to interview):** JD emphasizes domain knowledge but doesn't list it as required. The SE needs to credibly discuss industry-specific concepts with buyers. Will would need significant ramp time.
- **Major (-2 to score, -15% to interview):** JD explicitly requires domain expertise (e.g., "deep understanding of the Employee Experience landscape," "travel technology background"). The domain knowledge is core to daily conversations with buyers, not just context.

##### Step 2.3f — Assess Compounding Risk

**Multiple gaps compound — they don't just add up, they multiply.**
Check for these compounding combinations:

1. **Senior title + years gap + title mismatch** = Triple filter.
   The hiring manager screens for experienced SEs first. Will gets filtered before a human sees the resume.
   → Score penalty: -2, Interview penalty: -15%

2. **Domain gap + hard technical requirements missing** = Double filter.
   Even if functional SE skills match, the JD needs specific knowledge Will doesn't have.
   → Score penalty: -1, Interview penalty: -10%

3. **Developer/technical buyer + no developer-facing experience** = Fundamental mismatch.
   Will's experience is with business buyers. Selling to developers requires a fundamentally different motion, demo style, and technical credibility.
   → Score penalty: -2, Interview penalty: -20%

4. **Senior level + domain-specific vertical** = Elevated bar.
   Senior roles in vertical-specific companies (cybersecurity, healthcare, fintech) expect the SE to already speak the language. There's no ramp time.
   → Score penalty: -1, Interview penalty: -10%

Apply these penalties **cumulatively** if multiple combinations apply.

##### Step 2.3g — Factor in Compensation

- **Comp above target ($185K+ OTE):** +0.5 to score (signals the company values the role and may be flexible on exact experience)
- **Comp in target range ($155K-$185K OTE):** No adjustment
- **Comp below target ($130K-$155K OTE):** -0.5 to score
- **Comp significantly below target (<$130K OTE):** -1 to score
- **Comp not listed:** No adjustment (but note it as unknown in concerns)

##### Step 2.3h — Synthesize Score

**Start from a base score, then apply adjustments:**

| Base Score | Condition |
|-----------|-----------|
| 8 | Every JD requirement is a strong match, pre-sales confirmed, right level |
| 7 | Most requirements are strong matches, 1-2 minor partial matches, no missing quals |
| 6 | Good functional match but with 2-3 partial matches or 1 moderate gap |
| 5 | Functional match with significant gaps (domain, technical, or seniority) |
| 4 | Multiple material gaps that compound |
| 3 | Fundamental mismatch (wrong buyer type, wrong role motion, hard blockers) |

Then apply adjustments from Steps 2.3e (domain), 2.3f (compounding), and 2.3g (comp).
**Final score = base + adjustments, clamped to 1-10.**

**Score validation checkpoint:** Before finalizing, ask yourself:
- "If Will submitted this application, what would actually happen?"
- "Would a hiring manager for THIS specific role, at THIS seniority level, at THIS company, move Will forward?"
- If your answer is "probably not," the score should be ≤5 and the decision should be NO.

#### Step 2.4 — Produce Evaluation Output

All of the following fields are **required**:

- **score** (integer 1-10): Final calibrated score
- **score_summary**: 2-3 sentence explanation covering the key dynamic (not just listing matches)
- **strong_matches**: Array of strings — each citing specific JD requirement → specific Will credential
- **partial_matches**: Array of strings — each naming the specific gap
- **missing_qualifications**: Array of strings — each classified as dealbreaker or nice-to-have
- **hard_technical_requirements**: Array of strings — any specific technical skills/protocols/tools the JD requires that Will lacks. Empty array if none.
- **domain_gap_severity**: `"none"` / `"minor"` / `"moderate"` / `"major"` — from Step 2.3e
- **compounding_risks**: Array of strings — which compounding combinations from Step 2.3f apply. Empty array if none.
- **key_concerns**: 2-4 bullets covering:
  - ATS/title risk (LOW/MEDIUM/HIGH) — how likely is "Product & Business Consultant" or "Customer Success Manager" to pass ATS filters for the target title?
  - Buyer type and its impact on fit
  - Company stage risk
  - Comp signal vs. $155K-$185K OTE target (include actual comp range if known)
  - Domain gap severity and whether it's learnable or a daily requirement
- **apply_decision**: `YES` / `YES WITH CAVEATS` / `NO`
  - `YES`: Score ≥7, no dealbreakers, interview chance ≥30%
  - `YES WITH CAVEATS`: Score 5-6, no hard dealbreakers but meaningful gaps, interview chance 15-30%
  - `NO`: Score ≤4, or any dealbreaker present, or interview chance <15%
- **apply_reason**: 1-2 sentence rationale explaining the decision
- **interview_chance**: Integer percentage, using calibration anchors:
  - Perfect functional + domain + buyer match: 50-65%
  - Strong functional, domain gap, business buyer: 35-45%
  - Strong functional, HIGH ATS/title risk: 25-35%
  - Developer/technical buyer, or CS-titled candidate filter: 10-20%
  - Multiple compounding mismatches: <10%
  - **Then apply compounding penalties from Step 2.3f**
- **buyer_type**: `"business"` / `"technical"` / `"mixed"`
- **comp_range**: The actual compensation range from the JD (or `null` if not listed)

#### Step 2.5 — Re-assess Tier

After evaluation, the initial Phase 1 tier may be wrong. Update if needed:

- Score ≥7 + YES → tier should be `apply_now`
- Score 5-6 + YES WITH CAVEATS → tier should be `worth_reviewing`
- Score ≤5 + NO → downgrade to `low_priority` or `filtered_out`
- If tier changes, log: `INFO "Tier change: [slug] [old_tier] → [new_tier]"`

#### Step 2.6 — Store and Save

Set `evaluation.evaluated_at` to current ISO timestamp.
Store ALL fields from Step 2.4 in the job's `evaluation` object.
Save `data/jobs.json` after each evaluation.
Log: `INFO "Eval [slug]: score=[X], decision=[YES/NO/CAVEATS], interview=[X%], buyer=[type], domain_gap=[severity]"`

After all evaluations: Log: `INFO "Phase 2 complete: X evaluations"`

---

## PHASE 3 — Resume Generation

Log: `INFO "Phase 3: Resume generation started"`

### Resume Generation Rules

- **`apply_now`** jobs with evaluation but no resume: **Auto-generate** during pipeline run
- **`worth_reviewing`** jobs: **Do NOT auto-generate.** Resume generation requires a manual trigger via the dashboard's "Create Resume" button (writes a trigger file to `resumes/queue/[slug].json`)
- **`applied`** jobs: **Do NOT auto-generate.** These already have resumes from when they were apply_now/worth_reviewing.
- **NEVER generate** if evaluator said `NO`
- Process `apply_now` jobs first, then queued `worth_reviewing` jobs

### Step 3.0 — Check Resume Queue

Before processing auto-generate jobs, check `resumes/queue/` for trigger files:
- Each `.json` file contains `{"slug": "company--title"}` identifying a job to generate a resume for
- For each trigger file found: add that job to the generation list (same process as `apply_now`)
  - Log: `DETAIL "Queue trigger: [slug]"` for each trigger file
- After successful generation, **delete the trigger file immediately** to prevent duplicates
- If generation fails, keep the trigger file so it retries next run

### For each job needing a resume:

Log: `DETAIL "Resume [slug]: variant=[SE|SC], changes=[X]"` after identifying changes.

#### Step 3.1 — Determine Variant

| Role Type | Variant |
|-----------|---------|
| Sales Engineer, Solutions Engineer, Pre-Sales Engineer, Customer Engineer | SE |
| Solutions Consultant, Technical Consultant, Implementation Consultant | SC |
| Solutions Architect, Customer Success Engineer, ambiguous | Infer from JD language |

Infer from JD motion if title is ambiguous: pre-sales demo/POC/discovery focus → SE; advisory/delivery/implementation focus → SC.

#### Step 3.2 — Read Base Resume and JD

1. Read the base resume markdown: `profile/base-resume-SE.md` or `profile/base-resume-SC.md`
2. **Always fetch and re-read the full JD fresh** — do not rely on evaluation memory or cached snippets.
   The evaluation tells you *what* to change; the fresh JD read tells you *how* to change it.
3. Use the evaluation's qualification breakdown (strong_matches, partial_matches, missing_qualifications) as a prioritization guide:
   - **strong_matches** → these are the strengths to surface prominently
   - **partial_matches** → these are areas to reframe existing experience toward
   - **missing_qualifications** → if flagged as dealbreaker, do NOT attempt to paper over with invented keywords

#### Step 3.3 — Identify Changes

Compare the JD against the active resume variant. Identify changes across:
- **Summary** — reframe emphasis, reorder clauses, add JD-specific language
- **Selected Achievements** — reorder by relevance to JD, reframe lead text
- **Skills & Expertise** — swap or reorder keywords matching JD language
- **Technical Proficiencies** — reorder to surface relevant tools
- **Experience bullets** — reframe, reorder, or weave JD keywords into existing content

#### HARD RULES — NEVER VIOLATE

These rules are absolute. Violating any of them produces a resume that misrepresents Will's background.

1. **NEVER change job titles, company names, dates, degrees, or credentials.**
   This includes titles in the Experience section AND the self-description in the Summary.

2. **NEVER change Will's identity in the Summary.**
   The Summary's opening describes what Will actually IS — "Technical consultant" (SC variant) or
   "Sales engineer" (SE variant). Do NOT replace this with the target role title.
   - ❌ WRONG: "Solutions architect specializing in..." (Will is not a Solutions Architect)
   - ❌ WRONG: "Customer engineer specializing in..." (Will is not a Customer Engineer)
   - ✅ RIGHT: "Technical consultant specializing in enterprise platform deployment, integration
     architecture, and scalable solution design..." (reframed emphasis, kept true identity)

3. **NEVER add technologies, tools, or platforms Will hasn't actually used.**
   Only tools that appear in the base resume can appear in the tailored resume.
   - ❌ WRONG: Adding "Workday (familiar)" when Will has never used Workday
   - ❌ WRONG: Adding "SAML" or "OIDC" when Will has no identity protocol experience
   - ✅ RIGHT: Reordering existing tools to put the most JD-relevant ones first

4. **NEVER fabricate experience, metrics, or credentials.**
   Keywords are woven into existing true content only. If Will didn't do it, it doesn't go on the resume.

5. **NEVER paper over dealbreaker gaps.**
   If the evaluation flagged a missing qualification as a dealbreaker, do not attempt to
   close the gap with creative rewording. The resume should honestly present Will's strengths —
   if there's a gap, let the cover letter or interview address it, not resume fabrication.

6. **Only reframe, reorder, and weave keywords from the JD into existing true content.**
   - **reframe** = change how existing experience is described (same facts, different emphasis)
   - **reorder** = move existing bullets/items to surface the most relevant ones first
   - **keyword_weave** = incorporate JD terminology into existing true statements
   - **emphasis_shift** = adjust which aspects of existing experience are highlighted

#### Self-Check Before Finalizing Changes

Before generating the PDF, validate every change against these questions:
- "Is every statement in the modified resume still literally true about Will?"
- "Have I claimed Will holds a title or role he doesn't actually hold?"
- "Have I added any technology, tool, or platform Will hasn't actually used?"
- "Would Will be comfortable defending every line in an interview?"
If any answer is NO, revert that change.

#### Step 3.4 — Record All Changes

For EVERY modification, record **verbatim before/after text** in the `resume.changes` array:
```json
{
  "section": "Summary",
  "change_type": "reframe",
  "before": "[exact verbatim original text from base resume]",
  "after": "[exact verbatim new text as it will appear in the resume]",
  "reason": "JD quotes 'X requirement' — reframed to highlight Will's Y experience"
}
```

Change types: `reframe`, `reorder`, `keyword_weave`, `emphasis_shift`

**Important:** `before` and `after` must contain the full verbatim text, not summaries. The dashboard displays these as side-by-side diffs.

#### Step 3.5 — Generate PDF

1. Parse the base markdown into a content JSON structure (the build script handles this)
2. Apply all changes from Step 3.3 to the content
3. Write the modified content to a temporary JSON file
4. Run: `python scripts/build_resume_pdf.py content.json --output resumes/William_Horne_[SE|SC]_[Company].pdf`

The build script handles:
- All formatting (colors, typography, layout) — locked in code, not configurable here
- Adaptive spacing with binary search to target exactly 2 pages with ≥85% page 2 fill
- Last-resort content trimming if overflow occurs

**Output filename:** `resumes/William_Horne_[SE|SC]_[Company].pdf`
- Company name: strip special chars, spaces→underscores

5. **Delete the temporary content JSON file** after the PDF is successfully generated.
   Do NOT leave intermediate `*_content.json` files, temp scripts, or test PDFs in `resumes/`.
   The only files that should persist in `resumes/` are final resume PDFs and the `queue/` directory.

#### Step 3.6 — Store and Save

Set `resume.generated_at` to current ISO timestamp.
Set `resume.variant` and `resume.filename`.
Store all changes in `resume.changes`.
Save `data/jobs.json` after each resume.
Log: `INFO "Resume generated: [filename]"`

After all resumes: Log: `INFO "Phase 3 complete: X resumes generated"`

---

## PHASE 4 — Dashboard & Cleanup

### Step 4.0 — Process Applied Queue

Before generating the dashboard, check `applied/queue/` for trigger files:
- Each `.json` file contains `{"slug": "company--title", "applied_at": "ISO timestamp"}`
- For each trigger file found:
  - Set `job.tier = "applied"`
  - Set `job.application = {"applied_at": "<timestamp>", "original_tier": "<previous tier>"}`
  - Log: `INFO "Applied: [slug]"`
  - **Delete the trigger file immediately** after processing
- If the slug doesn't exist in jobs.json, log `WARN "Applied queue: unknown slug [slug]"` and delete the trigger

### Step 4.1 — Write Run Summary

Before generating the dashboard, write a short narrative summary of this pipeline run to `data/jobs.json` under the key `last_run_summary`. This text is displayed in the dashboard header's blue summary box.

The summary should be 2-4 sentences covering:
- **Sighting updates** — which existing jobs appeared again (e.g., "Stainless, Sentry, and Box appeared again — all now seen 3 times.")
- **New jobs** — how many new jobs were found, with a brief note on actionable vs. blocked (e.g., "4 new jobs found, but all had hard blockers: 10+ years required, wrong location, or contract roles.")
- **Actionable opportunities** — any new `apply_now` or strong `worth_reviewing` jobs, or "No new actionable opportunities this cycle."
- **Resumes** — if any were generated, mention them

Keep the tone concise and informative. This is a status update, not a report.

Also write two additional summaries to `data/jobs.json`:

**`jobs_log_summary`** — A 2-4 sentence overview of the full job search picture. Cover:
- Total jobs tracked across all months, tier breakdown (e.g., "3 apply now, 8 worth reviewing, 12 filtered out")
- Top-scoring opportunities still in play (not yet applied)
- Any patterns or trends (e.g., "Most SE roles require 5+ years, majority are remote-friendly")

**`applied_tracker_summary`** — A 2-3 sentence status of applications. Cover:
- Total applications submitted, most recent one
- Which companies/roles have been applied to
- If no applications yet: "No applications submitted yet. Mark jobs as applied from the dashboard to track them here."

Log: `INFO "Phase 4: Run summaries written"`

### Step 4.2 — Generate Dashboard

Run: `python scripts/dashboard.py`

This reads `data/jobs.json` (including `last_run_summary`) and generates three files:
- `dashboard.html` — main dashboard with tier sections, monthly archives, and dropdown menus
- `applied.html` — clean table of all applied jobs
- `jobs_log.html` — comprehensive log of ALL jobs organized by month with collapsible sections
Log: `INFO "Phase 4: Dashboard generated (3 files)"`

### Step 4.3 — Reset New Flags

Set `is_new: false` for ALL jobs in jobs.json.

### Step 4.4 — Final Save

Update stats:
- `stats.total_jobs` = count of all jobs
- `stats.total_evaluated` = count of jobs with evaluation
- `stats.total_resumes` = count of jobs with resume
- `stats.total_applied` = count of jobs with tier "applied"

Save `data/jobs.json`.
Log: `INFO "Stats: X total, Y evaluated, Z resumes, W applied"`

### Step 4.5 — Summary Output

Log: `RUN "Pipeline complete: X emails, Y new jobs, Z evaluated, W resumes"`

Print a summary:
```
=== JobScout Complete ===
Scanned: X emails
New jobs found: X
Evaluations run: X
Resumes generated: X
Dashboard: dashboard.html
```

---

## Error Handling

- **Gmail MCP fails:** Log `ERROR "Gmail MCP failed: [reason]"`, proceed with existing data (skip Phase 1)
- **Single evaluation fails:** Log `ERROR "Eval failed [slug]: [reason]"`, skip that job, continue with remaining jobs
- **Single resume fails:** Log `ERROR "Resume failed [slug]: [reason]"`, skip that job, continue with remaining jobs
- **WebFetch fails:** Log `WARN "WebFetch blocked: [url]"`, use WebSearch fallback, then mark unconfirmed if both fail
- **Python script fails:** Log `ERROR "Script failed [script]: [reason]"`, report in summary, continue
- **Save-after-every-phase:** Even if later phases fail, earlier work is preserved

## Priority Order

Within each phase, always process:
1. `apply_now` jobs first
2. `worth_reviewing` jobs second
3. Skip `applied`, `low_priority`, `filtered_out`, `could_not_retrieve` for evaluation/resume

## JD Fetching Notes

Known site behaviors:
- **LinkedIn:** Usually blocked, use WebSearch fallback
- **Indeed:** Often returns 403, use WebSearch fallback
- **Greenhouse/Lever/Ashby:** Often blocked, try WebSearch with ATS site filter
- **Built In:** Usually works with WebFetch
- **WebSearch is the primary fallback** for all blocked sites

WebSearch fallback pattern:
```
"[Company]" "[Job Title]" job description requirements responsibilities
```

ATS-specific search:
```
"[Company]" "[Job Title]" "[New York]" site:greenhouse.io OR site:lever.co OR site:ashbyhq.com
```

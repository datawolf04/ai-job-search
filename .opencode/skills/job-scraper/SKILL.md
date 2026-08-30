---
name: job-scraper
description: Scrapes job sites for new positions matching your profile
---

## How It Works

This skill searches multiple job sites using targeted queries based on your profile, deduplicates against previously seen jobs and the application tracker, and presents new matches with a quick fit assessment.

## Invocation

The user triggers this skill by saying things like:
- "Find new jobs"
- "Scrape for jobs"
- "Any new positions?"
- "/scrape"

Optional arguments:
- A focus area, e.g. "/scrape data science" or "/scrape geophysics"
- "broad" to run all search categories, e.g. "/scrape broad"

---

## Execution Steps

### Step 0: Load State

1. Read `job_scraper/seen_jobs.json` (create if missing - start with `{"seen": {}}`)
2. Read `job_search_tracker.csv` to extract already-applied companies+roles
3. Read `search-queries.md` (this directory) for the search strategy

### Step 1: Search

Run **WebSearch** queries from `search-queries.md`. By default, run the top 3 priority categories. If the user said "broad", run all categories.

If the user specified a focus area (e.g. "data science"), prioritize queries from that category.

For each search:
- Use `WebSearch` with site-specific queries (linkedin.com/jobs, indeed.com, glassdoor.com, google.com/jobs, ncworks.gov, etc.)
- Target your configured geographic area (US: Remote / Research Triangle NC / DC metro / Midwest)
- Look for postings from the last 14 days

### Step 2: Fetch & Parse

For each promising result from Step 1:
- Use `WebFetch` to retrieve the job posting page
- Extract: **job title**, **company**, **location**, **posting date** (or "recent"), **URL**, **key requirements** (brief), **application deadline** (if listed)
- Skip if the URL or company+title combo already exists in `seen_jobs.json`
- Skip if the company+role already appears in `job_search_tracker.csv`

### Step 3: Quick Fit Assessment

For each new job, do a rapid fit check (NOT the full evaluation from `04-job-evaluation.md` - just a quick signal):

- **High match**: Role directly involves your core skills
- **Medium match**: Role is adjacent to your experience
- **Low match**: Role requires significant skills you lack

### Step 4: Deduplicate & Store

1. Add ALL fetched jobs (new and skipped) to `seen_jobs.json` with structure:
```json
{
  "seen": {
    "<url_or_company_title_key>": {
      "title": "...",
      "company": "...",
      "url": "...",
      "first_seen": "YYYY-MM-DD",
      "fit": "high/medium/low",
      "status": "new/skipped/evaluated"
    }
  }
}
```
2. Only present jobs NOT already in the seen list or tracker.

### Step 5: Present Results

Present new jobs in a table sorted by fit (high first):

```
## New Job Matches - YYYY-MM-DD

Found X new positions (Y high, Z medium, W low match).

| # | Fit | Title | Company | Location | Deadline | URL |
|---|-----|-------|---------|----------|----------|-----|
| 1 | High | ... | ... | ... | ... | [Link](...) |

### High-Match Highlights
For each high-match job, add 2-3 bullet points:
- Why it matches your profile
- Key requirements to check
- Any red flags
```

After presenting, ask:
> "Want me to evaluate any of these in detail? Just give me the number(s)."

If the user picks a number, invoke the **job-application-assistant** skill workflow (fit evaluation first, then CV + cover letter if approved).

### Step 6: Update Tracker (Optional)

If the user decides to apply to any job, add a row to `job_search_tracker.csv`.

---

## Important Rules

1. **Never fabricate job postings.** Only present jobs found via actual WebSearch/WebFetch results.
2. **Respect deduplication.** Always check seen_jobs.json AND job_search_tracker.csv before presenting.
3. **Focus on configured geographic area.** Skip jobs that require relocation or are clearly outside commute range.
4. **Only open positions.** Skip postings with expired deadlines or those marked as closed.
5. **Be efficient with WebFetch.** Don't fetch every search result - use titles and snippets to pre-filter before fetching.
6. **Parallel searches.** Use the Task tool or parallel WebSearch calls to speed up the search phase.

---

## NC State Careers Portal Check (always run during /scrape)

The State of North Carolina uses a Workday careers portal. Query it directly via its public jobs API and
report any new data-science / ML / analytics postings matching Steven's profile alongside the other
scrape results.

**Endpoint** (POST, JSON body, `Content-Type: application/json`):

```
curl -s -X POST "https://nc.wd108.myworkdayjobs.com/wday/cxs/nc/NC_Careers/jobs" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"appliedFacets":{},"limit":20,"offset":0,"searchText":"<term>"}'
```

**Query terms to run** (deduplicate against `seen_jobs.json` and `job_search_tracker.csv`):
- `data scientist`, `data science`, `data analyst`, `data analytics`
- `machine learning`, `business intelligence`, `SQL`, `statistics`
- `quantitative`, `research analyst`, `database`

Fetch individual full listings with (GET):
`https://nc.wd108.myworkdayjobs.com/wday/cxs/nc/NC_Careers/job/<externalPath>`
(run a search first to get the externalPath/title-slug for each posting).

**Dedup:** Use `seen_jobs.json` `"NC-<JR-id>"` keys for these postings. The OSA Senior Data Analyst
(JR-121425) and the Applications Systems Analyst II shortlist (JR-111172) are already known/considered —
skip those. Report only genuinely new, un-applied postings.

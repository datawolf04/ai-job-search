---
name: job-scraper
description: Scrapes job sites for new positions matching your profile
---

## How It Works

This skill searches multiple job sites using targeted queries based on your profile, deduplicates against previously seen jobs and the application tracker, **verifies every aggregator-sourced result on the employer's own ATS**, **applies a freshness threshold so stale reqs are not presented as open**, and presents only the surviving new matches with a quick fit assessment.

## Non-Negotiable Rules

> **1. Never present a job posting found on an aggregator search page unless you have confirmed it is live on
> the employer's own ATS.** See Step 2b.
>
> **2. Never present a verified posting as open without applying the freshness gate.** See Step 2c.
> Anything 11+ days old is stale; a passed End Date means closed even if an Apply button still renders.

Rule 1 exists because it has already gone wrong. Two Northrop Grumman reqs were surfaced through search
capture, one had a full application package built for it, and both turned out to be removed from the
employer's site. Only a manual browser check caught it. Aggregator pages get re-indexed after a req is
pulled and their posted dates are unreliable. 21 entries in `seen_jobs.json` still carry aggregator index
URLs that cannot be verified at all.

Rule 2 exists because ATS verification turned out to be necessary but not sufficient. On 2026-10-04 four
positions were each verified live on an employer ATS and were all dead when Steven checked them in a browser:
RTX `01867802`, DMI `2026-28957`, DMI `2026-28958`, and GoodRx `JR100637`. DMI Senior had scored 83/100, the
best fit in the queue, and closed within ~12 days of being posted. Verification proves a posting exists; it
does not prove the req is still hiring.

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
- Look for postings from the last 14 days. Cast slightly wider (21-30 days) if the user asked for a broad
  sweep, since the freshness gate in Step 2c will drop anything too old to act on anyway.

### Step 2: Fetch & Parse

For each promising result from Step 1:
- Use `WebFetch` to retrieve the job posting page
- Extract: **job title**, **company**, **location**, **posting date** (or "recent"), **URL**, **key requirements** (brief), **application deadline** (if listed)
- Skip if the URL or company+title combo already exists in `seen_jobs.json`
- Skip if the company+role already appears in `job_search_tracker.csv`
- **If the URL came from an aggregator, you are NOT done — go to Step 2b.**

### Step 2b: ATS Verification Gate (MANDATORY for aggregator-sourced results)

**A position found on an aggregator search page must be verified on the employer's own ATS before it is
presented to Steven. This is a hard gate, not a preference.**

This rule exists because of a concrete failure: on 2026-10-02 a Northrop Grumman req
(`R10231897`) was surfaced through a search capture, materials were built for it, and the req turned out to
be dead — the employer site returned a removed-posting link. Separately, req `R10229090` had already been
closed. Both were only caught by Steven checking in a browser. 21 entries in `seen_jobs.json` still carry
aggregator index URLs (Dice, Indeed, aijobsmap, devitjobs) that cannot be verified at all.

**Aggregators** = LinkedIn, Indeed, Glassdoor, Dice, ZipRecruiter, Built In, Lensa, BuiltIn SF,
aijobsmap, devitjobs, Himalayas, Jooble, Talent.com, aggregator pages generally.
**ATS / direct** = the employer's own careers domain or its ATS vendor subdomain.

Procedure for each aggregator-sourced result:

1. Identify the employer from the posting.
2. Search the employer's own careers site for the role. Try, in order:
   - `WebSearch` with `site:<employer-domain> <role title> <req id if known>`
   - The employer careers search URL directly via `WebFetch`
   - An ATS API if the employer uses one (see the Hitachi and NC sections below for the Workday
     CX-API pattern, which is the fastest and most reliable route when applicable)
3. Record the outcome honestly:
   - **Verified** — found on the ATS. Store the **ATS URL**, not the aggregator URL. Mark
     `"verified": true`, `"verified_date": "YYYY-MM-DD"`, `"source": "<aggregator name>"`.
   - **Not found** — could not locate on the ATS after a reasonable attempt. Mark
     `"status": "unverified"` and `"url_quality": "aggregator_index_not_direct"`. **Do not present it
     as a live opening.**
   - **Closed** — ATS has it marked closed/removed. Mark `"status": "closed"`.
4. Only **Verified** results advance to Step 3 and get presented in Step 5.

**Never present an aggregator-sourced posting whose liveness you could not confirm.** If a result looks
promising but cannot be verified, mention it in a short separate "Unverified leads" note at the end, clearly
labelled, and never include it in the fit-ranked table. Do not assign it a fit score.

Report the gate's effect in the Step 5 output, e.g. `7 aggregator results found, 3 verified on ATS,
3 closed/removed, 1 unverified (listed below)`.

Cost control: verify with `WebSearch site:` before `WebFetch`, and batch verifications in parallel via the
Task tool. If a company has 5+ aggregator reqs, verify the employer's ATS endpoint once, then query it
directly for the rest.

### Step 2c: Freshness Gate (MANDATORY)

**ATS verification proves a posting exists. It does not prove it is still hiring. Target-sector employer
ATS listings turn over fast, and a req can close within days. Classify every verified posting by posted
date before presenting it.**

This rule exists because of a concrete failure: on 2026-10-04 Steven browser-checked four positions that
had each been verified live on an employer ATS days earlier. **All four were dead** — RTX Data Engineer
`01867802` (End Date had already passed, hidden behind stale "Posted Yesterday" index metadata), DMI Senior
Data Scientist `2026-28957` and DMI Data Scientist `2026-28958` (both posted 2026-09-22 with working Apply
buttons, both closed within ~12 days), and GoodRx Lead Data Scientist `JR100637` (showed "Posted 21-30+ Days
Ago"). DMI Senior had scored 83/100, the best fit in the entire queue, and evaporated before an application
could be filed.

Classify each verified posting by age, using the ATS ISO posted date where available:

| Age at time of run | Label | Action |
|---|---|---|
| 0–3 days | `FRESH` | Present immediately. Top of the table. Recommend acting within 24–48 hours. |
| 4–7 days | `RECENT` | Present normally. Note the age and suggest acting within a week. |
| 8–10 days | `AGING` | Present only if fit is high. Flag explicitly: "posted N days ago, confirm still open." |
| 11+ days | `STALE` | **Do not present as an open role.** Either omit, or list only in a clearly labelled "Stale — confirm before investing time" note. No fit score. |

Rules:
- Compute age from the ATS posted date, never from an aggregator's relative string. `postedOn` values like
  "Posted 30+ Days Ago" or "Posted Yesterday" are unreliable and have already caused one false liveness
  signal; Workday `jobPostingInfo.startDate` / `timePosted` are authoritative (see the Hitachi and NC
  sections for the CX-API pattern).
- If the posting states an explicit **End Date / application deadline** and that date has passed, treat it
  as `STALE` regardless of any Apply button still rendering. A visible Apply button is not proof of an open
  req — the RTX page did exactly this.
- If no posted date is available, mark `STALE` and say so rather than assuming it is new.
- Where posted date and End Date disagree, **trust the End Date** and flag the conflict.

Report the age distribution in the Step 5 output, e.g.
`4 verified on ATS: 1 fresh (0-3d), 1 recent (4-7d), 2 stale (11d+, listed separately)`.

**Timing guidance to pass on to Steven:** surface fresh postings immediately rather than batching them
into a weekly digest. In this market a strong req posted on Monday can be closed by the following week, so
an 8+ day delay between discovery and presentation is enough to lose the role.

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
      "company": "...",
      "role": "...",
      "req_id": "...",
      "url": "<ATS URL if verified, else the aggregator URL>",
      "location": "...",
      "posted": "YYYY-MM-DD",
      "seen_date": "YYYY-MM-DD",
      "salary": "...",
      "fit": "high/medium/low",
      "status": "new/skipped/closed/unverified",
      "verified": true,
      "verified_date": "YYYY-MM-DD",
      "freshness": "fresh|recent|aging|stale",
      "source": "linkedin|indeed|dice|ats_direct|...",
      "url_quality": "ats_direct | aggregator_index_not_direct",
      "notes": "..."
    }
  }
}
```
2. Only present jobs NOT already in the seen list or tracker.
3. Before writing, check the tracker for an existing outcome on that company+role. If the tracker already
   records an application or rejection, mirror that status rather than writing `new`.

### Step 5: Present Results

Present **verified** jobs in a table sorted by fit (high first):

```
## New Job Matches - YYYY-MM-DD

Found X new positions (Y high, Z medium, W low match).
All entries below verified on the employer ATS on YYYY-MM-DD.
Age distribution: A fresh (0-3d), B recent (4-7d), C aging (8-10d), D stale (11d+, listed separately).

| # | Fit | Title | Company | Location | Salary | Age | ATS URL |
|---|-----|-------|---------|----------|--------|-----|----------|
| 1 | High | ... | ... | ... | ... | 2d | [Link](...) |

### High-Match Highlights
For each high-match job, add 2-3 bullet points:
- Why it matches your profile
- Key requirements to check
- Any red flags
- **If `FRESH`, say so and recommend acting within 24-48 hours.**
```

Then report the verification gate's effect, and list anything that failed it separately and clearly:

```
### Verification Notes
- 9 aggregator results found this run; 4 verified on employer ATS, 3 closed/removed, 2 could not verify.
- Closed/removed: <company> <role> (req no longer on ATS), <company> <role>
- Unverified leads - NOT confirmed live, do not treat as openings:
  - <company> <role> - found only on <aggregator>, not found on employer ATS as of YYYY-MM-DD
- Stale postings - verified once but 11+ days old or past their End Date. Confirm in a browser before
  investing any time:
  - <company> <role> - posted YYYY-MM-DD (Nd ago), End Date YYYY-MM-DD has passed
```

If a `FRESH` high-match job appears, surface it at the very top and state plainly that it is time
sensitive. Do not bury a fresh high-fit req under analysis of lower-priority results.

After presenting, ask:
> "Want me to evaluate any of these in detail? Just give me the number(s)."

If the user picks a number, invoke the **job-application-assistant** skill workflow (fit evaluation first, then CV + cover letter if approved).

### Step 6: Update Tracker (Optional)

If the user decides to apply to any job, add a row to `job_search_tracker.csv`.

---

## Important Rules

1. **Never fabricate job postings.** Only present jobs found via actual WebSearch/WebFetch results.
2. **Aggregator results must be verified on the employer ATS before presentation.** See Step 2b. This is a
   hard gate: an unverified aggregator hit is never presented as a live opening and never gets a fit score.
3. **Apply the freshness gate to every verified posting.** See Step 2c. Anything 11+ days old is not
   presented as an open role, and a passed End Date means closed even if an Apply button still renders.
   Verification proves existence, not continued hiring.
4. **Respect deduplication.** Always check seen_jobs.json AND job_search_tracker.csv before presenting.
5. **Focus on configured geographic area.** Skip jobs that require relocation or are clearly outside commute range.
6. **Only open positions.** Skip postings with expired deadlines or those marked as closed.
7. **Be efficient with WebFetch.** Don't fetch every search result - use titles and snippets to pre-filter before fetching.
8. **Parallel searches.** Use the Task tool or parallel WebSearch calls to speed up the search phase.
9. **Record provenance.** Every entry stored must carry a real ATS URL once verified, plus `verified`,
   `verified_date`, and `source` fields, so later scrapes can tell a confirmed req from an aggregator rumor.
10. **Reconcile on write.** When adding to `seen_jobs.json`, also check whether the tracker already has an
   outcome for that company+role. `seen_jobs` has drifted from `job_search_tracker.csv` before (an entry with
   no status at all for a req applied weeks earlier). Trust the tracker for status; trust `seen_jobs` for
   discovery history.

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

**Apply the Step 2c freshness gate** to anything surfaced here. `jobPostingInfo.startDate` from the
detail GET is a real ISO date, so age is exact — surface anything 0–7 days old promptly and drop anything
11+ days old unless it is a high-fit match worth a browser confirmation.

## Sierra Nevada Corporation (SNC) Careers Check (always run during /scrape)

SNC uses a Workday careers portal. Query it directly via its public jobs API and report any new
data-science / ML / AI / analytics postings or physics-adjacent roles matching Steven's profile.

**Endpoint** (POST, JSON body, `Content-Type: application/json`):

```
curl -s -X POST "https://snc.wd1.myworkdayjobs.com/wday/cxs/snc/SNC_External_Career_Site/jobs" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"appliedFacets":{},"limit":50,"offset":0,"searchText":"<term>"}'
```

**Query terms to run** (deduplicate against `seen_jobs.json` and `job_search_tracker.csv`):
- `data scientist`, `data science`, `machine learning`, `AI`, `ML`, `LLM`, `MLOps`
- `data engineer`, `analytics`, `business intelligence`
- `physics`, `optical`, `photonics`, `aerospace engineer`

Fetch individual full listings with (GET):
`https://snc.wd1.myworkdayjobs.com/wday/cxs/snc/SNC_External_Career_Site/job/<externalPath>`

**Dedup:** Use `seen_jobs.json` `"SNC-<R-id>"` keys for these postings. Report only genuinely new,
un-applied postings.

**Notes:** Many SNC AI/ML roles accept STEM degrees (CS/Math/Physics/Engineering). Physics background
is relevant for roles like Sr Optical Test and Measurement Engineer and some aerospace/engineering
positions. Apply the Step 2c freshness gate as above.

---

## Hitachi Energy Careers Check (always run during /scrape)

Hitachi Energy runs a Workday tenant covering the **entire global group**, so results must be filtered
client-side down to US requisitions. A purpose-built scraper already exists and handles the filtering,
date windowing, and deduplication:

```
python3 job_scraper/hitachi_energy.py              # default 14-day window, US only
python3 job_scraper/hitachi_energy.py --days 30    # widen the posted-date window
python3 job_scraper/hitachi_energy.py --json       # machine-readable
```

Run this on every `/scrape` and report anything new alongside the other results.

**Why it matters:** Hitachi Energy's Raleigh research center posts new reqs constantly (84 NC reqs at last
check, several marked NEW) and runs adjacent roles to the ones Steven applies to. The theoretical physics
req (R0136799) was found this way, not via an aggregator.

**Underlying API**, if the script needs debugging (POST, JSON body):
`https://hitachi.wd1.myworkdayjobs.com/wday/cxs/hitachi/hitachi/jobs`
Job detail requires the **full** `externalPath` from the search response:
`https://hitachi.wd1.myworkdayjobs.com/wday/cxs/hitachi/hitachi<externalPath>`

**Gotchas that cost time if rediscovered:**
- Facet arrays (`locationMainGroup`, `timeType`, etc.) come back **empty** on this endpoint. Filter on
  `locationsText` and `jobPostingInfo.country` in code instead. Do not rely on server-side facets.
- `searchText` is fuzzy and OR-ish, returning hundreds of loosely-matched rows. The script over-fetches
  and filters on title; expect "research scientist" ~32 and "machine learning" ~428 before filtering.
- A naive "location contains Remote, therefore US" rule is **wrong**. Hitachi posts `Remote - Mexico` and
  `(DEAI HV) CN Remote`. Foreign country names *and* bare ISO-2 codes (`CN`, `IN`, `MX`) must be rejected
  explicitly. The script's `is_us_location`/`is_foreign` handle this and are unit-checked.
- The detail payload exposes `jobPostingInfo.startDate` as a real ISO date, so the 14-day filter can be
  exact rather than trusting the `postedOn` string ("Posted 30+ Days Ago").
- **No salary field is published** on these reqs. Expect to raise compensation on-screen instead.

**Scope limit — read before trusting company attribution.** This tenant returns reqs from multiple Hitachi
US entities, so check `hiringOrganization.name` on every result rather than assuming "Hitachi Energy":
- `HITACHI ENERGY USA INC` — grid/power research, e.g. Raleigh. This is the interesting one.
- `HITACHI HIGH-TECH AMERICA, INC.` — semiconductor **metrology equipment**, e.g. the Hillsboro OR
  Data Scientist reqs. Different industry, different domain requirements.
- International Hitachi Energy entities (Poland, India, Chile, Vietnam, Brazil, Sweden) also appear.

`HITACHI AMERICA, LTD.` reqs (for example the Santa Clara ML/CV Research Scientist, R0135875) live on a
**separate** front-end and will **not** appear here. If that company is worth covering it needs its own
source.

**Dedup:** `seen_jobs.json` `"HE-<R-id>"` keys (e.g. `HE-R0136799`). The script additionally dedupes on the
requisition ID found anywhere in `seen_jobs.json`, so older human-readable slugs still match. R0136799
(applied 2026-10-04), R0130393, R0135875 and R0093642 are already known — skip them.

**Apply the Step 2c freshness gate.** The script's default 14-day window is a discovery window, not a
presentability filter. Re-check `posted` age at presentation time and lead with anything 0–3 days old.
Hitachi reqs have historically stayed live well past 10 days (R0136799 was 86 days old and still accepting
at application time), so Hitachi postings are an exception worth surfacing beyond the stale cutoff rather
than dropping silently — but still flag the age and confirm no End Date has passed.

---

## Employer ATS Patterns (reference for Step 2b verification)

Knowing the employer's ATS makes verification one request instead of a search. Check these before falling
back to `WebSearch site:`.

### Workday — public CX API (best case: no auth, real ISO dates)

Most large employers. URL shape: `https://<company>.wd<N>.myworkdayjobs.com/<locale>/<site>`

Search:
```
curl -s -X POST "https://<host>/wday/cxs/<tenant>/<site>/jobs" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"appliedFacets":{},"limit":20,"offset":0,"searchText":"<role>"}'
```
Detail (requires the **full** `externalPath` from the search response):
```
curl -s "https://<host>/wday/cxs/<tenant>/<site><externalPath>" -H "Accept: application/json"
```

Useful fields: `jobPostingInfo.jobReqId` (dedup key), `.startDate` (real ISO posted date, unlike the
useless `postedOn` string), `.endDate` (treat as authoritative for liveness — if it has passed, the req is
closed even if an Apply button still renders), `.jobDescription`, `.location`, `.country`.

**Known Workday tenants:**
| Employer | Host | Tenant/Site |
|---|---|---|
| Hitachi Energy (multi-entity) | `hitachi.wd1.myworkdayjobs.com` | `hitachi/hitachi` — use `job_scraper/hitachi_energy.py` |
| NC State | `nc.wd108.myworkdayjobs.com` | `nc/NC_Careers` |
| RTX / Raytheon | `globalhr.wd5.myworkdayjobs.com` | `REC_RTX_Ext_Gateway` |

**Workday caveats:**
- Facet arrays usually come back **empty**. Filter client-side on location text and country rather than
  expecting server-side faceting.
- **RTX detail endpoints are unreliable.** On 2026-10-04 the CX-API detail path for req `01867802` returned
  `HTTP_400` on every variant tried (`REC_RTX_Ext_Gateway/REC_RTX_Ext_Gateway/job/...`,
  `REC_RTX_Ext_Gateway/job/...`, and with an `en-US` prefix), and the rendered page is a JavaScript shell
  returning ~6.7KB with no metadata. Do not burn time retrying RTX detail URLs. Use the Workday **search**
  endpoint for liveness, extract `endDate` from the search hit, and hand RTX reqs to Steven for a browser
  confirmation.

### Greenhouse
Posting JSON is public: `https://boards-api.greenhouse.io/v1/boards/<board>/jobs/<id>`

### Lever
`https://api.lever.co/v0/postings/<company>/<id>`

### Ashby
`https://api.ashbyhq.com/posting-api/job-board/<company>`

### Dayforce / Direct
Usually HTML only. Fetch the req URL directly; if the page shows "no longer accepting applications" or
redirects to a search page, treat as **closed**.

### Reading the result
- 200 + full JD → **Verified**. Store the ATS URL.
- 200 + "closed"/"removed"/"no longer accepting" → **Closed**.
- 404 → **Closed** (removed) or never existed. Do not present as live.
- Timeout / blocked → **Unverified**. Say so; do not present as an opening.

### When the employer has many aggregator reqs
Verify the ATS endpoint once with a broad query, then enumerate the employer's own listings directly instead
of verifying each aggregator hit separately. That is what `job_scraper/hitachi_energy.py` does.

---

## Observed Req Lifetimes (learned 2026-10-02 to 2026-10-04)

Measured from reqs that were verified live on an employer ATS and then browser-checked by Steven. Useful for
setting expectations on how fast to move and which employers to trust.

| Employer | Req | Verified live | Confirmed dead | Observed lifetime |
|---|---|---|---|---|
| DMI | Senior Data Scientist `2026-28957` | 2026-10-04 | 2026-10-04 | **~12 days from a 2026-09-22 post** |
| DMI | Data Scientist `2026-28958` | 2026-10-04 | 2026-10-04 | ~12 days, posted same day as the Senior req |
| GoodRx | Lead Data Scientist `JR100637` | 2026-10-04 | 2026-10-04 | 21-30+ days at verification, already stale |
| RTX | Data Engineer `01867802` | 2026-10-04 | 2026-10-04 | End Date 2026-08-24 had already passed |
| Northrop Grumman | `R10231897`, `R10229090` | 2026-10-02 | 2026-10-02 | already removed |
| Hitachi Energy | Research Scientist `R0136799` | 2026-10-02 | still accepting | **86 days and open** |
| Bandwidth | AI Engineer R&D `R-101893` | never | already closed | first published 2026-05-21 |

Takeaways:

- **Federal contractor and cleared work (DMI, RTX, Booz Allen) closes in roughly 1-2 weeks.** Clearance-
  eligible reqs are requisition-driven and get pulled or filled quickly. Assume a two-week shelf life and
  apply same-day.
- **Commercial employers with high req volume (Hitachi Energy) run reqs for months.** A long posting age is
  not itself a warning sign there. The presence of a closing date is a better signal than the posted date.
- **Requisition pairs move together.** DMI posted Senior and mid Data Scientist on the same day and both
  closed together. If one sibling closes, expect the other to follow; check both, but do not assume one
  surviving sibling means fresh inventory.
- **A req can be genuinely open on the ATS and still close within days.** Verification is a snapshot, not a
  reservation. This is the entire reason Step 2c exists.
- **Aggregators lag badly.** GoodRx was already stale when first surfaced; RTX's search metadata said
  "Posted Yesterday" against an End Date two months prior. Prefer ATS ISO dates every time.

**Practical consequence:** when a high-fit req appears, do not defer it to a batch review. Surface it
immediately, apply the same day, and treat a browser confirmation as a same-session check rather than
something to defer to the end of the week.

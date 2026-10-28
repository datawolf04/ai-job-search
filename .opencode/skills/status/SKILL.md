---
name: status
description: Reports current job-search state — open applications, follow-ups due or overdue, freshness of live leads, and recommended next actions
---

## Overview

`/status` answers three questions in one read: **where does every application stand, what is due next, and what should Steven do today.** It is strictly read-only at runtime. It never edits `job_search_tracker.csv`, `job_scraper/seen_jobs.json`, or any `outcome.md`. Output goes to the terminal; it is written to disk only when the user explicitly asks.

Read-only is a hard rule, not a preference. The tracker has a single sanctioned writer (`scripts/record_application.py`); a status report must never become a second writer.

## Data Sources

Four sources, read in this order. The first two are authoritative; the other two are advisory and never override a structured field.

### 1. `job_search_tracker.csv` — authoritative, structured

15 columns, header row first:

```
date, company, sector, role, role_type, channel, status, contact_person,
fit_rating, notes, cv_file, cover_letter_file, source, follow_up_date, follow_up_action
```

65 data rows. Read it as CSV with `newline=""` — never split on `,`, never use `splitlines` and index positionally. Several `notes` cells contain commas and are quoted by the writer.

`follow_up_date` + `follow_up_action` (columns 14 and 15) are the structured follow-up fields. Both or neither: a date with no action, or an action with no date, is an integrity error to report, not to repair.

### 2. `job_scraper/seen_jobs.json` — authoritative, structured

**Nested.** Top level is `{"seen": {…}}`; the 74 entries live under the `seen` key. Access as `data["seen"]`, not `data`.

Relevant fields per entry:

| Field | Use |
|---|---|
| `follow_up` | object `{date, action, done, created}` — structured commitment |
| `status` | lifecycle: `new`, `skipped`, `applied`, `submitted`, `rejected`, `closed`, `ineligible`, `stale`, `deprioritized`, `accepted` |
| `recommended_action` / `recommended_action_due` | advisory next step with a due date |
| `outcome` | free-text prose, may contain an embedded "Follow up…" instruction |
| `fit_score`, `fit` | screening and evaluated fit |
| `freshness`, `age_days`, `verified`, `liveness` | lead health |
| `url`, `company`, `role`, `salary` | identification |

### 3. `documents/applications/*/outcome.md` — advisory prose

Fifteen files. Legacy vocabulary in `**Status:**`: `no_response`, `applied`, `submitted`, `ready_to_submit`, `Ready`, `Applied`. Two files (`nc_osa_senior_data_analyst`, `opm_data_scientist`) have **no** `**Status:**` line — report as `unknown`, do not invent one.

Going forward these files carry a `**Follow-up:** <YYYY-MM-DD> — <action>` line. That line is a **fallback source**: parse it only when neither structured source already covers the same application. Do not rewrite the 15 existing files to add it.

Prose mentions of a past follow-up ("Follow-up sent 2026-08-04 to Phaedra Grove") are **history, not commitment** — they are `DONE`, never reported as due.

### 4. `cv/`, `cover_letters/`, `documents/applications/` — evidence only

Used to confirm a claimed application actually has materials on disk. Not a status source.

## Procedure

### Step 1 — Resolve the date first

Everything downstream is relative to today. Never hardcode a date.

```bash
TODAY=$(date +%F); echo "$TODAY"
```

### Step 2 — Load and validate both structured sources

```bash
python3 - <<'PY'
import csv, io, json, collections
rows = list(csv.reader(io.StringIO(open("job_search_tracker.csv", newline="").read())))
hdr, data = rows[0], rows[1:]
bad = [i for i, r in enumerate(data, 2) if len(r) != len(hdr)]
print("tracker:", len(data), "rows x", len(hdr), "cols", "| malformed:", bad or "none")
print("statuses:", dict(collections.Counter(r[6] for r in data)))
seen = json.load(open("job_scraper/seen_jobs.json"))["seen"]
print("seen:", len(seen), "entries")
print("follow_up:", sum(1 for v in seen.values() if isinstance(v.get("follow_up"), dict)))
PY
```

Abort the report if either source fails validation — a report built on a malformed tracker is worse than no report. State the problem and stop.

### Step 3 — Build the follow-up register

Collect commitments from all structured sources, then dedupe.

**Sources:**
1. Tracker rows where `follow_up_date` is non-empty → key `(follow_up_date, normalized company-or-contact)`, action from `follow_up_action`, origin `tracker`.
2. `seen["*"].follow_up` where `done` is not `true` → key `(follow_up.date, normalized company)`, origin `seen_jobs`.
3. `seen["*"].recommended_action_due` → key `(recommended_action_due, normalized company)`, origin `seen_jobs:recommended_action`.
4. `outcome.md` `**Follow-up:**` lines → key `(date, normalized company)`, origin `outcome.md`, **only if key not already present**.

**Normalization:** lowercase, strip all punctuation and whitespace, collapse to bare company or person token (`"LexisNexis (RELX)"` and `"Mithun Acharya"` are distinct tokens for the same row — build the key from whichever field the origin actually names, and include both when available so either lookup hits).

**Dedupe rule:** same key → keep one entry, prefer origin order `tracker` > `seen_jobs` > `seen_jobs:recommended_action` > `outcome.md`, and merge origins into a list. When two entries share a date and company but name different actors (a company-level "follow up if no contact" plus a person-level "raise with Adam Canton"), they are **different actions** — surface both, and label them `company-level` / `person-level` so it is obvious they are complementary rather than duplicated.

Never drop an entry silently. Every dedupe must be visible in the output as a merge note, because a lost commitment is the worst failure this skill can have.

### Step 4 — Bucket by urgency

Relative to `TODAY`:

| Bucket | Window |
|---|---|
| `OVERDUE` | date < today — negative day count shown, e.g. `(−51d)` |
| `DUE ≤7d` | today … today+7 |
| `DUE ≤30d` | today+8 … today+30 |
| `LATER` | > today+30 |
| `DONE` | `done: true`, or prose describing a follow-up already sent |

Order the register `OVERDUE` → `DUE ≤7d` → `DUE ≤30d` → `LATER`, ascending by date within a bucket. `DONE` goes in a collapsed history section, never in the active list.

### Step 5 — Map every status to the six canonical states

Display-only. The underlying data keeps its own vocabulary; never rewrite it.

| Canonical | Tracker statuses | seen_jobs statuses | outcome.md statuses |
|---|---|---|---|
| `QUEUE` | `Planned`, `Removed before submission` | `new`, `skipped`, `deprioritized` | `ready_to_submit`, `Ready` |
| `PENDING` | `Applied`, `Unresponsive`, `CV shared`, `On hold - future role` | `applied`, `submitted` | `applied`, `Applied`, `submitted`, `no_response` |
| `ACTIVE` | `Shortlisted`, `Referred to hiring manager` | — | interview stages reached |
| `WON` | `Accepted` | `accepted` | offer received |
| `DEAD` | `Rejected`, `Ghosted`, `Cancelled/Filled`, `Closed - req pulled before submission` | `rejected`, `closed`, `ineligible`, `stale` | — |
| `PARKED` | (fold `On hold - future role` here if separating from `PENDING`) | — | — |

Unmapped value → report as `UNKNOWN` with the raw string. Never guess, never coerce.

### Step 6 — Report integrity problems

Report, do not fix:

- Rows not at 15 columns
- `follow_up_date` without `follow_up_action`, or vice versa
- Missing `**Status:**` in an `outcome.md`
- A structured follow-up and an `outcome.md` line disagreeing on the same application
- `done: true` with a date still in the future
- Tracker rows with no `cv_file`/`cover_letter_file` while status ≥ `Applied`
- Anything in the CSV that cannot be parsed

### Step 7 — Recommend the next actions

Rank the **top 5** and, for each, state `why`, `source`, and `effort` (S/M/L). Base ranking on:

1. Overdue follow-ups (highest — a missed commitment costs more than a new application)
2. Follow-ups due within 7 days
3. Applications in `PENDING` with no contact beyond 30 days
4. Live leads with high fit (`fit_score ≥ 70`) and `freshness` not `stale`
5. Everything else

Reference the specific person or req id, never a vague "check on your applications".

## Output Shape

Terminal-first, ~40 lines. Save only if the user asks.

```
STATUS 2026-10-07

FOLLOW-UP REGISTER (4 active, 2 done hidden)
  OVERDUE   2026-08-17 (−51d)  LexisNexis (RELX)     tracker
            Follow up with Mithun Acharya (Sr Data Scientist III)
  DUE ≤7d   2026-10-16 (+9d)   Motion / LexisNexis   seen_jobs + seen_jobs:recommended_action
            Raise req 879726 by name with Adam Canton; do NOT apply cold.
  DUE ≤30d  2026-11-05 (+29d)  OneSix                tracker + seen_jobs
  DUE ≤30d  2026-11-16 (+40d)  Hitachi Energy        tracker
  merges: OneSix 2026-11-05 (tracker + seen_jobs); Motion 2026-10-16 (follow_up + recommended_action_due)

PIPELINE
  QUEUE 4   PENDING 18   ACTIVE 2   WON 1   DEAD 39   PARKED 1   UNKNOWN 0

LEAD HEALTH
  verified 19   unverified 46   liveness-failed 8
  freshness: fresh 3 | recent 5 | aging 6 | stale 12 | no-posted-date 4

INTEGRITY  (n problems)
  outcome.md missing **Status:** — nc_osa_senior_data_analyst, opm_data_scientist

NEXT ACTIONS
  1. [M] Contact Mithun Acharya re LexisNexis Sr Data Scientist III — 51 days overdue (tracker)
  2. [S] Raise Motion req 879726 with Adam Canton before 2026-10-16 (seen_jobs)
  3. [S] Check OneSix req 4706504006 — no contact since 2026-10-05 (tracker + seen_jobs)
  ...
```

Counters must reconcile with the register and the sources. If `PENDING` does not equal the number of tracker rows mapping to `PENDING` plus seen entries mapping to `PENDING`, say so rather than printing a plausible number.

## Failure Modes

- **Reading the tracker positionally.** Use `csv.reader`. Notes contain commas; positional indexing silently shifts columns.
- **Treating `seen_jobs.json` as flat.** It is `{"seen": {...}}`.
- **Double-counting OneSix and Motion.** Both have follow-ups in two sources. Dedupe, and show the merge.
- **Reporting a past follow-up as due.** "Follow-up sent 2026-08-04" is `DONE`.
- **Writing anything.** Read-only. To record a new application use `scripts/record_application.py`.
- **Hardcoding a date.** Resolve `TODAY` first; every day count derives from it.
- **Silently dropping an entry during dedupe.** Merges must be printed.

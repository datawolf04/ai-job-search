---
description: Report job-search status, follow-ups due or overdue, and recommended next actions
---

Report the current state of Steven's job search: every open application by stage, follow-ups due or overdue, health of live leads, data-integrity problems, and a ranked list of what to do next.

Load the `status` skill and follow its procedure exactly. Read the sources, never write them.

Resolve the date with `date +%F` first — every day count in the report derives from it.

**Strictly read-only.** Do not edit `job_search_tracker.csv`, `job_scraper/seen_jobs.json`, or any `outcome.md`. To record a new application, use `scripts/record_application.py` instead.

If `$ARGUMENTS` contains a company or role (e.g. `status LexisNexis`), narrow the report to that application and print the full detail for it — tracker row, seen_jobs entry, matching `outcome.md`, and any pending follow-up — while still showing the overdue count across everything else, so nothing gets hidden by the filter.

If `$ARGUMENTS` contains `save`, write the report to `status.md` in the repository root after printing it. Otherwise print to the terminal only.

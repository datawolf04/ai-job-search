---
description: Search job portals for new positions matching your profile
---

Run the job scraper to find new positions matching your profile. Search multiple US job sites using targeted queries, deduplicate against previously seen jobs, and present new matches with a quick fit assessment.

If `$ARGUMENTS` contains a focus area (e.g. "data science"), prioritize queries from that category. If it contains "broad", run all search categories.

Load the job-scraper skill for detailed execution steps. Read `search-queries.md` for the search strategy.

**NC State portal check (always run):** Also query the NC Careers Workday portal API
(https://nc.wd108.myworkdayjobs.com/en-US/NC_Careers) for new data-science / ML / analytics postings
matching Steven's profile. See the `job-scraper` skill for the API endpoint and query terms. Report any
new postings alongside the other search results.

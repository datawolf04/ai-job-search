# Search Queries for Job Scraper

## Search Sites

Primary (US job market):
- **linkedin.com/jobs** - LinkedIn job listings (filter: USA / target cities)
- **indeed.com** - Indeed job listings
- **glassdoor.com** - Glassdoor job listings
- **google.com/jobs** - Google Jobs aggregation

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for known target companies

## Query Categories

Queries are grouped by priority. Each query should be combined with your location terms where the site supports it.

### Priority 1: Data Scientist

These match your strongest and most desired career direction.

```
site:linkedin.com/jobs "Data Scientist" " numerical methods"
site:linkedin.com/jobs "Data Scientist" " statistical modeling"
site:linkedin.com/jobs "Data Scientist" "Python" "R"
site:indeed.com "Data Scientist" "physics"
site:indeed.com "Data Scientist" "computational modeling"
site:glassdoor.com "Data Scientist" "machine learning"
```

### Priority 2: Research Scientist

These match your domain expertise and research background.

```
site:linkedin.com/jobs "Research Scientist" "Python" "R"
site:linkedin.com/jobs "Research Scientist" "numerical methods"
site:linkedin.com/jobs "Research Scientist" "statistical modeling"
site:indeed.com "Research Scientist" "physics"
site:indeed.com "Research Scientist" "computational"
site:glassdoor.com "Research Scientist" "data analysis"
```

### Priority 3: Adjacent Roles

Adjacent roles you could pivot into.

```
site:linkedin.com/jobs "ML Engineer" "Python" "numerical"
site:linkedin.com/jobs "Quantitative Analyst" "statistical modeling"
site:linkedin.com/jobs "Applied Scientist" "machine learning"
site:indeed.com "Technical Consultant" "data science"
site:indeed.com "Scientific Programmer" "Python" "R"
```

### Priority 4: Broader Technical / Consulting

Wider net for general technical roles.

```
site:linkedin.com/jobs "Data Analyst" "Python" "R"
site:linkedin.com/jobs "Software Engineer" "scientific computing"
site:indeed.com "Computational Scientist" "Python"
site:indeed.com "Research Engineer" "machine learning"
```

## Location Filter

When evaluating results, verify the job location is within reasonable commute distance from your home. Open to relocation, so include:
- Any US city (primary targets: Research Triangle NC, Detroit MI, Indianapolis IN, Washington DC)
- Remote positions
- Hybrid positions within major metro areas

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed. If a posting date cannot be determined, include it but flag as "date unknown".

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" -> relevant category queries + custom focus-specific queries

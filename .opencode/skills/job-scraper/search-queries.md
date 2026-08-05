# Search Queries for Job Scraper

## Search Sites

Primary (US job market):
- **linkedin.com/jobs** - LinkedIn job listings (filter: USA / target cities)
- **indeed.com** - Indeed job listings
- **glassdoor.com** - Glassdoor job listings
- **google.com/jobs** - Google Jobs aggregation
- **ncworks.gov** - North Carolina state job portal

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for known target companies:
  - raytheon.com/careers
  - sncorp.com/careers
  - posit.co/about/careers
  - anaconda.com/about/careers

## Query Categories

Queries are grouped by priority. Each query should be combined with your location terms where the site supports it.

### Priority 1: Data Scientist

These match your strongest and most desired career direction.

```
site:linkedin.com/jobs "Data Scientist" " statistical modeling"
site:linkedin.com/jobs "Data Scientist" "Python" "R"
site:linkedin.com/jobs "Data Scientist" "physics"
site:indeed.com "Data Scientist" "machine learning"
site:indeed.com "Data Scientist" "computational modeling"
site:glassdoor.com "Data Scientist" "decision intelligence"
site:ncworks.gov "Data Scientist"
```

### Priority 2: Research Scientist / Research Engineer

These match your domain expertise in modeling physical systems.

```
site:linkedin.com/jobs "Research Scientist" "Python" "R"
site:linkedin.com/jobs "Research Scientist" "numerical methods"
site:linkedin.com/jobs "Research Scientist" "physics"
site:linkedin.com/jobs "Research Engineer" "physical systems"
site:indeed.com "Research Scientist" "computational modeling"
site:indeed.com "Research Engineer" "simulation"
site:glassdoor.com "Research Scientist" "data analysis"
site:ncworks.gov "Research Scientist"
```

### Priority 3: ML / Data Engineering (Python or R)

Engineering roles requiring Python or R skills.

```
site:linkedin.com/jobs "ML Engineer" "Python" "numerical"
site:linkedin.com/jobs "Machine Learning Engineer" "Python" "R"
site:linkedin.com/jobs "Data Engineer" "Python" "R"
site:indeed.com "ML Engineer" "scientific computing"
site:indeed.com "Scientific Programmer" "Python" "R"
site:ncworks.gov "Machine Learning"
```

### Priority 4: Adjacent & Broader Roles

Wider net for roles where your quantitative background is an asset.

```
site:linkedin.com/jobs "Applied Scientist" "machine learning"
site:linkedin.com/jobs "Quantitative Analyst" "statistical modeling"
site:linkedin.com/jobs "Research Analyst" "Python"
site:indeed.com "Computational Scientist" "Python"
site:indeed.com "Technical Consultant" "data science"
site:glassdoor.com "Data Analyst" "Python" "R"
```

## Location Filter

Evaluate results against these location tiers:

- **Ideal:** Remote (fully remote US), Raleigh/Durham/Chapel Hill NC (commutable)
- **Acceptable:** Washington DC metro area, Midwest (Chicago IL, Indianapolis IN, Detroit MI, Madison WI, Columbus/Cleveland OH)
- **Borderline:** Other Midwest cities more than 1hr from major metro
- **Too far:** Outside US, any location requiring >1hr daily commute (unless remote or hybrid with infrequent office visits)

Include remote positions regardless of location. For on-site/hybrid positions, focus on the preferred areas above.

## Target Companies

Prioritize listings from:
- Government contractors: Raytheon, SNCorp (Sierra Nevada Corporation), Northrop Grumman, Lockheed Martin, Booz Allen Hamilton
- Data science / scientific computing: Posit (formerly RStudio), Anaconda, Dataiku, Domino Data Lab
- Any company explicitly seeking physics or quantitative research background

## Salary Filter

Minimum acceptable salary: $100,000/year with benefits. Flag positions below this threshold for discussion before skipping.

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed. If a posting date cannot be determined, include it but flag as "date unknown".

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" -> relevant category queries + custom focus-specific queries

#!/usr/bin/env python3
"""
Booz Allen Hamilton Workday CX API scraper.

Host: bah.wd1.myworkdayjobs.com
Tenant/Site: bah / BAH_Jobs
"""
import sys
from workday_scraper import run_scraper

def main():
    return run_scraper(
        host="bah.wd1.myworkdayjobs.com",
        tenant="bah",
        site="BAH_Jobs",
        company_name="Booz Allen Hamilton",
        slug="BAH",
        search_terms=[
            "research scientist", "data scientist", "machine learning",
            "scientific computing", "numerical", "simulation", "physics",
            "analytics", "statistics",
        ],
        days=14,
        all_locations=False,
        json_out="--json" in sys.argv,
    )

if __name__ == "__main__":
    sys.exit(main())

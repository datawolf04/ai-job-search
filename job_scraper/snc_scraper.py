#!/usr/bin/env python3
"""
Sierra Nevada Corporation (SNC) Workday CX API scraper.

Host: snc.wd1.myworkdayjobs.com
Tenant/Site: snc / SNC_External_Career_Site
"""
import sys
from workday_scraper import run_scraper

def main():
    return run_scraper(
        host="snc.wd1.myworkdayjobs.com",
        tenant="snc",
        site="SNC_External_Career_Site",
        company_name="Sierra Nevada Corporation",
        slug="SNC",
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

#!/usr/bin/env python3
"""
Northrop Grumman Workday CX API scraper.

Host: ngc.wd1.myworkdayjobs.com
Tenant/Site: ngc / Northrop_Grumman_External_Site
"""
import sys
from workday_scraper import run_scraper

def main():
    return run_scraper(
        host="ngc.wd1.myworkdayjobs.com",
        tenant="ngc",
        site="Northrop_Grumman_External_Site",
        company_name="Northrop Grumman",
        slug="NGC",
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

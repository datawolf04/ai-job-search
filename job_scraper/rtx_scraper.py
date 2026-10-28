#!/usr/bin/env python3
"""
RTX (Raytheon) Workday CX API scraper.

Host: globalhr.wd5.myworkdayjobs.com
Tenant/Site: globalhr / REC_RTX_Ext_Gateway
"""
import sys
from workday_scraper import run_scraper

def main():
    return run_scraper(
        host="globalhr.wd5.myworkdayjobs.com",
        tenant="globalhr",
        site="REC_RTX_Ext_Gateway",
        company_name="RTX (Raytheon)",
        slug="RTX",
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

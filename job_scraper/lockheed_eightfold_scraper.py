#!/usr/bin/env python3
"""
Lockheed Martin Eightfold API scraper.

Domain: lockheedmartin.eightfold.ai (eightfold.ai platform)
API: /api/apply/v2/jobs with domain=lockheedmartin.com
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import urllib.parse
from datetime import date, timedelta

SEEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_jobs.json")

SEARCH_TERMS = [
    "research scientist", "data scientist", "machine learning",
    "scientific computing", "numerical", "simulation", "physics",
    "analytics", "statistics",
]
TITLE_PATTERNS = [
    r"research scientist", r"research engineer", r"scientist", r"data scientist",
    r"machine learning", r"\bai\b", r"\bml\b", r"applied scientist",
    r"computational", r"simulation", r"numerical", r"modeling", r"modelling",
    r"optimization", r"optimisation", r"analytics", r"quantitative",
    r"statistic", r"physics",
]
REJECT_PATTERNS = [
    r"\bintern", r"\bco-?op\b", r"apprentice", r"technician",
    r"product manager", r"project manager", r"program manager",
    r"\bpm\b", r"architect", r"consultant", r"supervisor", r"leadership",
]

def load_seen():
    seen = set()
    if not os.path.exists(SEEN_PATH):
        return seen
    try:
        with open(SEEN_PATH) as fh:
            data = json.load(fh)
    except Exception:
        return seen
    blob = json.dumps(data)
    for rid in re.findall(r"\b\d{10,}\b", blob):
        seen.add(str(rid))
    return seen

def fetch_jobs(term, start=0, num=50, timeout=30):
    q = urllib.parse.urlencode({
        "domain": "lockheedmartin.com",
        "start": start,
        "num": num,
        "query": term,
        "sort_by": "relevance",
    })
    url = f"https://lockheedmartin.eightfold.ai/api/apply/v2/jobs?{q}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (job-search-script)",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def matches_title(title, patterns):
    low = title.lower()
    return any(re.search(p, low) for p in patterns)

def is_rejected_title(title, patterns):
    low = title.lower()
    return any(re.search(p, low) for p in patterns)

def main():
    ap = argparse.ArgumentParser(description="Scrape Lockheed Martin (Eightfold)")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    seen = load_seen()
    results = []
    cutoff = date.today() - timedelta(days=args.days)

    for term in SEARCH_TERMS:
        try:
            d = fetch_jobs(term)
        except Exception as e:
            print(f"warning: {term} failed: {e}", file=sys.stderr)
            continue
        for p in d.get("positions", []):
            rid = str(p.get("id", ""))
            name = p.get("name", "")
            loc = p.get("location", "")
            if rid and rid in seen:
                continue
            if is_rejected_title(name, REJECT_PATTERNS):
                continue
            if not matches_title(name, TITLE_PATTERNS):
                continue
            results.append({
                "req_id": rid,
                "title": name,
                "location": loc,
                "url": f"https://lockheedmartin.eightfold.ai/careers/job/{rid}?domain=lockheedmartin.com",
            })
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    print(f"Lockheed Martin (Eightfold) - {len(results)} new req(s)\n")
    for r in results:
        print(f"  {r['req_id']:15} {r['title']}")
        print(f"{'':24}{r['location']}")
    if not results:
        print("  (nothing new)")
    return 0

if __name__ == "__main__":
    sys.exit(main())

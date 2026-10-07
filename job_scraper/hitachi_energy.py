#!/usr/bin/env python3
"""
Hitachi Energy US careers scraper.

Hitachi Energy posts to a Workday tenant that covers the whole global group,
so this script queries the public Workday CX API and filters client-side down
to United States requisitions.

Endpoint (POST, JSON):
    https://hitachi.wd1.myworkdayjobs.com/wday/cxs/hitachi/hitachi/jobs

Job detail (GET, requires the FULL externalPath from the search response):
    https://hitachi.wd1.myworkdayjobs.com/wday/cxs/hitachi/hitachi<externalPath>

Scope note: this tenant covers Hitachi Energy only. Hitachi America, Ltd.
reqs (e.g. the Santa Clara ML/CV Research Scientist, R0135875) live on a
separate front-end and are NOT returned here.

Usage:
    python3 hitachi_energy.py                 # default window, US only
    python3 hitachi_energy.py --days 30       # widen the posted-date window
    python3 hitachi_energy.py --all-locations # skip the US filter
    python3 hitachi_energy.py --json          # machine-readable output

Exit codes: 0 ok, 1 network/API failure, 2 bad arguments.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

BASE = "https://hitachi.wd1.myworkdayjobs.com/wday/cxs/hitachi/hitachi"
SEEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_jobs.json")

# Workday searchText is fuzzy/OR-ish, so results are noisy. Over-fetch and
# filter on title and location rather than trusting the ranking.
SEARCH_TERMS = [
    "research scientist",
    "data scientist",
    "machine learning",
    "scientific computing",
    "numerical",
    "optimization",
    "simulation",
    "power systems",
    "physics",
    "analytics",
]

# Titles worth surfacing. Kept deliberately broad: this employer posts a lot of
# pure electrical-engineering hardware roles that are not a fit, so the title
# filter is the first cheap cut, not the final judgement.
TITLE_PATTERNS = [
    r"research scientist", r"research engineer", r"scientist", r"data scientist",
    r"machine learning", r"\bai\b", r"\bml\b", r"applied scientist",
    r"computational", r"simulation", r"numerical", r"modeling", r"modelling",
    r"optimization", r"optimisation", r"analytics", r"quantitative",
    r"statistic", r"power system", r"energy system", r"physics",
]

# Roles that are a poor fit regardless of title match: requires an EE/ME
# hardware background or a specific toolchain Wolf does not have.
REJECT_PATTERNS = [
    r"\bintern", r"\bco-?op\b", r"apprentice", r"technician", r"welder",
    r"\bplc\b", r"assembly", r"\bhvac\b", r"field service", r"service technician",
    # role-type mismatches: management, architecture, or hardware engineering
    r"product manager", r"project manager", r"program manager", r"\bpm\b",
    r"architect", r"consultant", r"supervisor", r"leadership",
    r"\bengineer\b", r"engineering\b",
]

US_MARKERS = ("united states", "usa", "u.s.")

# Named foreign countries/regions. Checked before the US test so that
# "Remote - Mexico" or "(DEAI HV) CN Remote" are correctly rejected rather
# than waved through by a naive "remote means remote-US" rule.
FOREIGN_MARKERS = (
    "mexico", "canada", "china", "india", "poland", "sweden", "switzerland",
    "germany", "france", "spain", "italy", "brazil", "australia", "japan",
    "korea", "vietnam", "thailand", "malaysia", "indonesia", "philippines",
    "norway", "denmark", "finland", "netherlands", "belgium", "austria",
    "portugal", "greece", "czech", "romania", "hungary", "turkey", "brazil",
    "chile", "peru", "colombia", "argentina", "south africa", "egypt",
    "morocco", "algeria", "tunisia", "serbia", "ukraine", "bulgaria",
    "croatia", "slovakia", "slovenia", "lithuania", "latvia", "estonia",
    "ireland", "auckland", "malawi", "nigeria", "kenya", "ghana",
    "singapore", "ph nom penh", "ho chi minh", "hanoi", "jabalpur",
    "vadodara", "chennai", "bengaluru", "bangalore", "hyderabad", "pune",
    "chennai", "ahmedabad", "gurgaon", "noida", "krakow", "malmo", "lodz",
    "wroclaw", "global ", "worldwide",
)

# ISO-3166 alpha-2 codes for countries Hitachi posts in. Checked as whole
# tokens so "(DEAI HV) CN Remote" and "IN Remote" are caught.
FOREIGN_ISO2 = {
    "CN", "IN", "MX", "CA", "BR", "PL", "SE", "CH", "DE", "FR", "ES", "IT",
    "JP", "KR", "VN", "TH", "MY", "ID", "PH", "NO", "DK", "FI", "NL", "BE",
    "AT", "PT", "GR", "CZ", "RO", "HU", "TR", "CL", "PE", "CO", "AR", "ZA",
    "EG", "MA", "DZ", "TN", "RS", "UA", "BG", "HR", "SK", "SI", "LT", "LV",
    "EE", "IE", "IL", "AE", "SA", "SG", "NG", "KE", "GH", "AU", "NZ",
}

# US state names/abbreviations, so a bare "City, State" is recognized as US.
US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy", "dc",
}


def post_jobs(search_text, limit=20, offset=0, timeout=30):
    """Query the Workday CX jobs search endpoint."""
    payload = json.dumps({
        "appliedFacets": {},
        "limit": limit,
        "offset": offset,
        "searchText": search_text,
    }).encode()
    req = urllib.request.Request(
        f"{BASE}/jobs", data=payload, method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (job-search-script)",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_job(external_path, timeout=30):
    """Fetch one job detail record. Requires the full externalPath."""
    url = f"{BASE}{external_path}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (job-search-script)",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def load_seen_rids():
    """Collect every requisition ID already known, across all key styles.

    Returns a set of normalized R-IDs like 'R0136799'. Matching on req ID
    rather than dict key means this stays correct even if seen_jobs entries
    were created under a human-readable slug instead of the HE- convention.
    """
    rids = set()
    if not os.path.exists(SEEN_PATH):
        return rids
    try:
        with open(SEEN_PATH) as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"warning: could not read {SEEN_PATH}: {exc}", file=sys.stderr)
        return rids
    blob = json.dumps(data)
    for rid in re.findall(r"\bR0\d{6}\b", blob):
        rids.add(rid)
    return rids


def is_foreign(loc):
    """True if the location names a non-US country or region."""
    low = (loc or "").lower()
    if any(m in low for m in FOREIGN_MARKERS):
        return True
    # Whole-token ISO-2 codes, so CN/IN/MX are caught without matching
    # substrings of ordinary words.
    for tok in re.findall(r"\b[A-Z]{2}\b", loc or ""):
        if tok in FOREIGN_ISO2:
            return True
    return False


def is_us_location(loc):
    """True for US-based reqs, including US-remote and bare 'Remote'.

    This is a country test, not a geography test. Non-target US cities still
    pass here and are triaged later against the location tiers in
    search-queries.md. An explicitly foreign location is rejected even when
    it says Remote, which a naive 'remote means US' rule would get wrong.
    """
    low = (loc or "").lower().strip()
    if not low:
        return False
    if is_foreign(loc):
        return False
    if any(m in low for m in US_MARKERS):
        return True
    if "remote" in low and "," not in low:
        return True
    # "City, State" where State is a US state name or abbreviation.
    # Parentheses are stripped so "(HTA) NCP (Hillsboro, OR)" parses.
    parts = [p.strip().strip("()").strip() for p in low.split(",")]
    parts = [p for p in parts if p]
    if len(parts) >= 2 and parts[-1] in US_STATES:
        return True
    if len(parts) >= 2 and parts[0] in US_STATES:
        return True
    return False


def is_rejected_title(title):
    low = title.lower()
    return any(re.search(p, low) for p in REJECT_PATTERNS)


def matches_title(title):
    low = title.lower()
    return any(re.search(p, low) for p in TITLE_PATTERNS)


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def collect(days, all_locations, timeout=30):
    """Run all search terms and return deduplicated candidate postings."""
    cutoff = date.today() - timedelta(days=days)
    seen_rids = load_seen_rids()
    candidates = {}

    for term in SEARCH_TERMS:
        try:
            data = post_jobs(term, timeout=timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"warning: search '{term}' failed: {exc}", file=sys.stderr)
            continue

        for posting in data.get("jobPostings", []):
            rid_list = posting.get("bulletFields") or []
            rid = rid_list[0] if rid_list else None
            title = posting.get("title", "")
            loc = posting.get("locationsText", "")

            if rid and rid in seen_rids:
                continue
            if rid and rid in candidates:
                continue
            if not all_locations and not is_us_location(loc):
                continue
            if is_rejected_title(title):
                continue
            if not matches_title(title):
                continue

            candidates[rid or title] = {
                "req_id": rid,
                "title": title,
                "location": loc,
                "posted_label": posting.get("postedOn", ""),
                "external_path": posting.get("externalPath", ""),
            }
    return candidates, cutoff


def fetch_details(candidates, cutoff, timeout=30):
    """Add posting date, company and JD length; drop anything outside window."""
    out = []
    for cand in candidates.values():
        rec = dict(cand)
        start = None
        org = None
        if cand["external_path"]:
            try:
                detail = get_job(cand["external_path"], timeout=timeout)
                jpi = detail.get("jobPostingInfo", {})
                start = parse_date(jpi.get("startDate"))
                rec["posted"] = start.isoformat() if start else None
                rec["time_type"] = jpi.get("timeType")
                rec["remote_type"] = jpi.get("remoteType")
                jd = jpi.get("jobDescription") or ""
                rec["jd_chars"] = len(jd)
                rec["jd_excerpt"] = re.sub(r"<[^>]+>", " ", jd)[:600].strip()
                ho = detail.get("hiringOrganization") or {}
                org = ho.get("name") if isinstance(ho, dict) else None
                rec["company"] = org
            except (urllib.error.URLError, urllib.error.HTTPError,
                    TimeoutError, json.JSONDecodeError) as exc:
                print(f"warning: detail fetch failed for "
                      f"{cand.get('req_id')}: {exc}", file=sys.stderr)
                rec["posted"] = None
        else:
            rec["posted"] = None

        if rec.get("posted") and rec["posted"] < cutoff.isoformat():
            continue
        rec["date_unknown"] = rec.get("posted") is None
        if org:
            rec["company"] = org
        out.append(rec)
    out.sort(key=lambda r: (r.get("posted") or "", r.get("title") or ""), reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser(description="Scrape Hitachi Energy US reqs.")
    ap.add_argument("--days", type=int, default=14,
                    help="posted-date window in days (default 14)")
    ap.add_argument("--all-locations", action="store_true",
                    help="do not filter to United States")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    if args.days < 0:
        print("error: --days must be >= 0", file=sys.stderr)
        return 2

    try:
        candidates, cutoff = collect(args.days, args.all_locations)
    except Exception as exc:  # noqa: BLE001 - surface and exit cleanly
        print(f"error: scraper failed: {exc}", file=sys.stderr)
        return 1

    results = fetch_details(candidates, cutoff)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    fresh = [r for r in results if not r["date_unknown"]]
    unknown = [r for r in results if r["date_unknown"]]
    print(f"Hitachi Energy US - {len(results)} new req(s) in last {args.days}d "
          f"({len(fresh)} dated, {len(unknown)} date unknown)\n")
    for rec in results:
        posted = rec.get("posted") or "DATE UNKNOWN - verify manually"
        print(f"  {rec.get('req_id') or 'no-id':10} {posted:12} {rec['title']}")
        print(f"{'':24}{rec['location']}")
    if not results:
        print("  (nothing new)")
    print(f"\nDeduplicated against: {SEEN_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
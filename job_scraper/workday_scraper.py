#!/usr/bin/env python3
"""
Generic Workday CX API scraper.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta


US_MARKERS = ("united states", "usa", "u.s.")
FOREIGN_MARKERS = (
    "mexico", "canada", "china", "india", "poland", "sweden", "switzerland",
    "germany", "france", "spain", "italy", "brazil", "australia", "japan",
    "korea", "vietnam", "thailand", "malaysia", "indonesia", "philippines",
    "norway", "denmark", "finland", "netherlands", "belgium", "austria",
    "portugal", "greece", "czech", "romania", "hungary", "turkey", "chile",
    "peru", "colombia", "argentina", "south africa", "egypt", "morocco",
    "algeria", "tunisia", "serbia", "ukraine", "bulgaria", "croatia",
    "slovakia", "slovenia", "lithuania", "latvia", "estonia", "ireland",
    "auckland", "malawi", "nigeria", "kenya", "ghana", "singapore",
    "ph nom penh", "ho chi minh", "hanoi", "jabalpur", "vadodara", "chennai",
    "bengaluru", "bangalore", "hyderabad", "pune", "ahmedabad", "gurgaon",
    "noida", "krakow", "malmo", "lodz", "wroclaw", "global ", "worldwide",
)
FOREIGN_ISO2 = {
    "CN", "IN", "MX", "CA", "BR", "PL", "SE", "CH", "DE", "FR", "ES", "IT",
    "JP", "KR", "VN", "TH", "MY", "ID", "PH", "NO", "DK", "FI", "NL", "BE",
    "AT", "PT", "GR", "CZ", "RO", "HU", "TR", "CL", "PE", "CO", "AR", "ZA",
    "EG", "MA", "DZ", "TN", "RS", "UA", "BG", "HR", "SK", "SI", "LT", "LV",
    "EE", "IE", "IL", "AE", "SA", "SG", "NG", "KE", "GH", "AU", "NZ",
}
US_STATES = {
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut",
    "delaware","florida","georgia","hawaii","idaho","illinois","indiana","iowa",
    "kansas","kentucky","louisiana","maine","maryland","massachusetts","michigan",
    "minnesota","mississippi","missouri","montana","nebraska","nevada","new hampshire",
    "new jersey","new mexico","new york","north carolina","north dakota","ohio",
    "oklahoma","oregon","pennsylvania","rhode island","south carolina","south dakota",
    "tennessee","texas","utah","vermont","virginia","washington","west virginia",
    "wisconsin","wyoming","al","ak","az","ar","ca","co","ct","de","fl","ga","hi",
    "id","il","in","ia","ks","ky","la","me","md","ma","mi","mn","ms","mo","mt",
    "ne","nv","nh","nj","nm","ny","nc","nd","oh","ok","or","pa","ri","sc","sd",
    "tn","tx","ut","vt","va","wa","wv","wi","wy","dc",
}


def is_foreign(loc):
    low = (loc or "").lower()
    if any(m in low for m in FOREIGN_MARKERS):
        return True
    for tok in re.findall(r"\b[A-Z]{2}\b", loc or ""):
        if tok in FOREIGN_ISO2:
            return True
    return False


def is_us_location(loc):
    low = (loc or "").lower().strip()
    if not low:
        return False
    if is_foreign(loc):
        return False
    if any(m in low for m in US_MARKERS):
        return True
    if "remote" in low and "," not in low:
        return True
    parts = [p.strip().strip("()").strip() for p in low.split(",")]
    parts = [p for p in parts if p]
    if len(parts) >= 2 and parts[-1] in US_STATES:
        return True
    if len(parts) >= 2 and parts[0] in US_STATES:
        return True
    return False


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


def load_seen_rids():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    seen_path = os.path.join(base_dir, "seen_jobs.json")
    rids = set()
    if not os.path.exists(seen_path):
        return rids
    try:
        with open(seen_path) as fh:
            data = json.load(fh)
    except Exception:
        return rids
    blob = json.dumps(data)
    for rid in re.findall(r"\b(R0\d{6}|\d{8,})\b", blob):
        rids.add(rid)
    return rids


def is_rejected_title(title, reject_patterns):
    if not title:
        return True
    low = title.lower()
    return any(re.search(p, low) for p in reject_patterns)


def matches_title(title, title_patterns):
    if not title:
        return False
    low = title.lower()
    return any(re.search(p, low) for p in title_patterns)


def post_jobs(host, tenant, site, search_text, limit=20, offset=0, timeout=30):
    url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    payload = json.dumps({
        "appliedFacets": {},
        "limit": limit,
        "offset": offset,
        "searchText": search_text,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (job-search-script)",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_job(host, tenant, site, external_path, timeout=30):
    url = f"https://{host}/wday/cxs/{tenant}/{site}{external_path}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0 (job-search-script)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def collect(host, tenant, site, terms, title_patterns, reject_patterns,
            days, all_locations, timeout=30, limit_per_term=20):
    cutoff = date.today() - timedelta(days=days)
    seen_rids = load_seen_rids()
    candidates = {}

    for term in terms:
        try:
            data = post_jobs(host, tenant, site, term, limit=limit_per_term, timeout=timeout)
        except Exception as exc:
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
            if is_rejected_title(title, reject_patterns):
                continue
            if title_patterns and not matches_title(title, title_patterns):
                continue

            candidates[rid or title] = {
                "req_id": rid,
                "title": title,
                "location": loc,
                "posted_label": posting.get("postedOn", ""),
                "external_path": posting.get("externalPath", ""),
            }
    return candidates, cutoff


def fetch_details(host, tenant, site, candidates, cutoff, timeout=30):
    out = []
    for cand in candidates.values():
        rec = dict(cand)
        start = None
        org = None
        if cand["external_path"]:
            try:
                detail = get_job(host, tenant, site, cand["external_path"], timeout=timeout)
                jpi = detail.get("jobPostingInfo", {})
                start = parse_date(jpi.get("startDate"))
                rec["posted"] = start.isoformat() if start else None
                rec["jd_chars"] = len(jpi.get("jobDescription") or "")
                ho = detail.get("hiringOrganization") or {}
                org = ho.get("name") if isinstance(ho, dict) else None
                rec["company"] = org
            except Exception as exc:
                print(f"warning: detail fetch failed for {cand.get('req_id')}: {exc}", file=sys.stderr)
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


def run_scraper(host, tenant, site, company_name, slug, search_terms,
                title_patterns=None, reject_patterns=None, days=14,
                all_locations=False, timeout=30, json_out=False):
    title_patterns = title_patterns or [
        r"research scientist", r"research engineer", r"scientist", r"data scientist",
        r"machine learning", r"\bai\b", r"\bml\b", r"applied scientist",
        r"computational", r"simulation", r"numerical", r"modeling", r"modelling",
        r"optimization", r"optimisation", r"analytics", r"quantitative",
        r"statistic", r"power system", r"energy system", r"physics",
    ]
    reject_patterns = reject_patterns or [
        r"\bintern", r"\bco-?op\b", r"apprentice", r"technician", r"welder",
        r"product manager", r"project manager", r"program manager", r"\bpm\b",
        r"architect", r"consultant", r"supervisor", r"leadership",
    ]
    candidates, cutoff = collect(host, tenant, site, search_terms, title_patterns,
                                reject_patterns, days, all_locations, timeout)
    results = fetch_details(host, tenant, site, candidates, cutoff, timeout)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    seen_path = os.path.join(base_dir, "seen_jobs.json")

    if json_out:
        print(json.dumps(results, indent=2))
        return 0
    fresh = [r for r in results if not r["date_unknown"]]
    unknown = [r for r in results if r["date_unknown"]]
    print(f"{company_name} US - {len(results)} new req(s) in last {days}d "
          f"({len(fresh)} dated, {len(unknown)} date unknown)\n")
    for rec in results:
        posted = rec.get("posted") or "DATE UNKNOWN - verify manually"
        print(f"  {rec.get('req_id') or 'no-id':15} {posted:12} {rec['title']}")
        print(f"{'':24}{rec['location']}")
    if not results:
        print("  (nothing new)")
    print(f"\nDeduplicated against: {seen_path}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Generic Workday CX scraper.")
    ap.add_argument("--host", required=True)
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--company", required=True)
    ap.add_argument("--slug", default="")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--all-locations", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    terms = [
        "research scientist", "data scientist", "machine learning",
        "scientific computing", "numerical", "simulation", "physics", "analytics"
    ]
    return run_scraper(args.host, args.tenant, args.site, args.company, args.slug,
                       terms, days=args.days, all_locations=args.all_locations,
                       json_out=args.json)


if __name__ == "__main__":
    sys.exit(main())

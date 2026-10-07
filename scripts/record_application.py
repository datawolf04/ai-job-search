#!/usr/bin/env python3
"""
record_application.py — Safely append one application to the job tracker.

This is the ONLY sanctioned writer for job_search_tracker.csv. Both historical
corruptions of that file (unquoted commas shifting columns, and a full-file
rewrite normalizing unrelated rows) came from string interpolation or ad-hoc
csv.round-trips. This script exists so no prose instruction ever needs to
hand-edit the CSV again.

Safety properties:
  * Refuses to write if the header is not exactly the 15-column schema, or if
    any existing row fails to parse. Never compounds a broken file.
  * Validates every date as YYYY-MM-DD and status against a fixed vocabulary,
    so the vocabulary cannot silently drift.
  * Uses csv.writer with proper quoting. Notes are written verbatim — commas,
    quotes and newlines are safe. There is deliberately no comma-mangling.
  * Atomic write (tempfile + os.replace): an interrupted run cannot leave a
    half-written CSV.
  * Timestamped backup to /tmp/opencode/ before every write.
  * --dry-run prints the row and writes nothing.

Optionally upserts a follow_up object in job_scraper/seen_jobs.json when
--seen-key is supplied.

Usage:
    python3 scripts/record_application.py --company Acme --role Data Scientist \
        --channel Greenhouse --status Applied --source https://... \
        --follow-up-date 2026-11-07 --follow-up-action "Chase if silent"
"""

import argparse
import csv
import datetime as dt
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRACKER = REPO / "job_search_tracker.csv"
SEEN_JOBS = REPO / "job_scraper" / "seen_jobs.json"
BACKUP_DIR = Path("/tmp/opencode")

COLUMNS = [
    "date", "company", "sector", "role", "role_type", "channel", "status",
    "contact_person", "fit_rating", "notes", "cv_file", "cover_letter_file",
    "source", "follow_up_date", "follow_up_action",
]

# Fixed vocabulary: every value already present in the tracker, plus the
# accepted spellings. Adding a new status means editing this list on purpose.
ALLOWED_STATUSES = {
    "Applied", "Accepted", "Rejected", "Ghosted", "Unresponsive",
    "Cancelled/Filled", "Removed before submission",
    "Referred to hiring manager", "CV shared", "Shortlisted", "Planned",
    "On hold - future role", "Closed - req pulled before submission",
}

DATE_FMT = r"20\d{2}-\d{2}-\d{2}"


class Abort(Exception):
    """Write refused. Message is user-facing."""


def is_date(value: str) -> bool:
    if not value:
        return True
    try:
        return dt.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def load_tracker() -> list[list[str]]:
    if not TRACKER.exists():
        raise Abort(f"tracker not found: {TRACKER}")
    with TRACKER.open("r", encoding="utf-8", newline="") as fh:
        raw = fh.read()
    if "\r" in raw:
        raise Abort("tracker contains CRLF line endings; normalize to LF first")

    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        raise Abort("tracker is empty — refusing to guess the header")

    if rows[0] != COLUMNS:
        raise Abort(
            "header does not match the 15-column schema.\n"
            f"  expected: {COLUMNS}\n"
            f"  found:    {rows[0]}\n"
            "Refusing to write. Migrate the header before recording applications."
        )

    for i, row in enumerate(rows[1:], start=2):
        if len(row) != len(COLUMNS):
            raise Abort(
                f"line {i} parses to {len(row)} columns, expected {len(COLUMNS)}. "
                "Repair the file before writing — appending would compound the damage."
            )
        if not is_date(row[13]):
            raise Abort(f"line {i} has an invalid follow_up_date: {row[13]!r}")

    return rows


def backup(path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{path.stem}_prewrite_{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    return dest


def write_atomic(path: Path, lines: list[str]) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(lines))
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class _Collector:
    """Minimal file-like sink for csv.writer, avoiding a temp-text round-trip."""

    def __init__(self, buf: list[str]) -> None:
        self._buf = buf

    def write(self, s: str) -> int:
        self._buf.append(s)
        return len(s)


def _as_csv_line(cells: list[str]) -> str:
    """Render one row exactly as it will be written, so preview matches disk."""
    sink = io.StringIO()
    csv.writer(sink, lineterminator="").writerow(cells)
    return sink.getvalue()


def build_row(args: argparse.Namespace) -> list[str]:
    row = {
        "date": args.date or dt.date.today().isoformat(),
        "company": args.company,
        "sector": args.sector,
        "role": args.role,
        "role_type": args.role_type,
        "channel": args.channel,
        "status": args.status,
        "contact_person": args.contact,
        "fit_rating": args.fit,
        "notes": args.notes,
        "cv_file": args.cv,
        "cover_letter_file": args.cover_letter,
        "source": args.source,
        "follow_up_date": args.follow_up_date,
        "follow_up_action": args.follow_up_action,
    }

    if not is_date(row["date"]):
        raise Abort(f"--date is not a valid date: {row['date']!r}")
    if not is_date(row["follow_up_date"]):
        raise Abort(f"--follow-up-date is not a valid date: {row['follow_up_date']!r}")
    if row["follow_up_date"] and not row["follow_up_action"]:
        raise Abort("--follow-up-date given without --follow-up-action")
    if row["follow_up_action"] and not row["follow_up_date"]:
        raise Abort("--follow-up-action given without --follow-up-date")

    if row["status"] not in ALLOWED_STATUSES:
        raise Abort(
            f"status {row['status']!r} not in vocabulary.\n"
            f"  allowed: {', '.join(sorted(ALLOWED_STATUSES))}"
        )
    for key in ("company", "role", "channel"):
        if not row[key].strip():
            raise Abort(f"--{key.replace('_', '-')} is required")

    return [row[c] for c in COLUMNS]


def upsert_seen_follow_up(key: str, date: str, action: str, dry_run: bool) -> str:
    if not SEEN_JOBS.exists():
        return f"seen_jobs.json not found; skipped {key}"
    data = json.loads(SEEN_JOBS.read_text(encoding="utf-8"))
    seen = data.get("seen", {})
    if key not in seen:
        return (
            f"seen_jobs key {key!r} not found — skipped. "
            "Create the entry first, then re-run if a follow-up should be tracked there."
        )
    entry = seen[key]
    if not date:
        return f"{key}: no follow-up requested, left unchanged"

    previous = entry.get("follow_up")
    entry["follow_up"] = {
        "date": date,
        "action": action,
        "done": False,
        "created": dt.date.today().isoformat(),
    }
    if dry_run:
        return f"{key}: WOULD set follow_up {date} (was {previous or 'none'})"
    backup(SEEN_JOBS)
    SEEN_JOBS.write_text(
        json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    json.loads(SEEN_JOBS.read_text(encoding="utf-8"))
    return f"{key}: follow_up set to {date} (was {previous or 'none'})"


def main() -> int:
    p = argparse.ArgumentParser(
        description="Append one application to job_search_tracker.csv safely.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--company", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--channel", required=True, help="LinkedIn / Greenhouse / Company site / ...")
    p.add_argument("--status", required=True, help=f"one of: {', '.join(sorted(ALLOWED_STATUSES))}")
    p.add_argument("--date", default="", help="YYYY-MM-DD, defaults to today")
    p.add_argument("--sector", default="")
    p.add_argument("--role-type", default="Full-time")
    p.add_argument("--contact", default="")
    p.add_argument("--fit", default="", help='e.g. "73/100 - Good Fit"')
    p.add_argument("--notes", default="", help="written verbatim; commas are safe")
    p.add_argument("--cv", default="", help="path to CV source, e.g. cv/main_acme.tex")
    p.add_argument("--cover-letter", default="", dest="cover_letter",
                   help="path to cover letter source, e.g. cover_letters/cover_acme_ds.tex")
    p.add_argument("--source", default="", help="URL of the posting")
    p.add_argument("--follow-up-date", dest="follow_up_date", default="")
    p.add_argument("--follow-up-action", dest="follow_up_action", default="")
    p.add_argument("--seen-key", default="", help="seen_jobs.json key to upsert follow_up into")
    p.add_argument("--dry-run", action="store_true", help="print and write nothing")
    args = p.parse_args()

    try:
        rows = load_tracker()
        new_row = build_row(args)

        print(_as_csv_line(COLUMNS))
        print(_as_csv_line(new_row))
        print(f"\n{len(rows) - 1} existing data rows, all validated at {len(COLUMNS)} columns.")

        if args.dry_run:
            print("\nDRY RUN — nothing written.")
        else:
            buf: list[str] = []
            writer = csv.writer(_Collector(buf), lineterminator="\n")
            writer.writerows(rows)
            writer.writerow(new_row)
            backup(TRACKER)
            write_atomic(TRACKER, buf)
            print(f"APPENDED 1 row -> {len(rows)} data rows x {len(COLUMNS)} cols.")

        if args.seen_key:
            print(upsert_seen_follow_up(
                args.seen_key, args.follow_up_date, args.follow_up_action, args.dry_run
            ))
        elif args.follow_up_date:
            print("note: --follow-up-date set but --seen-key omitted; "
                  "only the tracker row records it.")

        return 0
    except Abort as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

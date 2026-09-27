"""Archive GitHub daily views without adding overlapping 14-day totals.

Run from any directory with Python 3.11+. Authentication uses GH_TOKEN or the
existing Git credential manager; credentials are never written to the archive.
"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import os
import subprocess
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "Cesarito2021/pyNISAR"
START = "2026-09-27"
ARCHIVE = ROOT / "docs/traffic-history.json"


def merge(history, payload, now):
    """Replace daily observations, preserving days outside the API window."""
    if history.get("repository") != REPOSITORY or history.get("since") != START:
        raise ValueError("Unexpected archive repository or start date")
    rows = payload["views"]
    for row in rows:
        for key in ("count", "uniques"):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError("Invalid traffic observation")
        date.fromisoformat(row["timestamp"][:10])
    # Exclude the oldest boundary day, which may be incomplete in a rolling window.
    lower = max(date.fromisoformat(START), now.date() - timedelta(days=13))
    by_date = {r["timestamp"][:10]: r for r in rows}
    days = history.setdefault("days", {})
    day = lower
    while day <= now.date():
        key = day.isoformat()
        row = by_date.get(key, {"count": 0, "uniques": 0})
        days[key] = {"views": row["count"], "daily_unique_visitors": row["uniques"]}
        day += timedelta(days=1)
    history["days"] = dict(sorted(days.items()))
    history["updated_at_utc"] = now.isoformat()
    history["accumulated_views"] = sum(r["views"] for r in days.values())
    history["missing_dates"] = []
    day = date.fromisoformat(START)
    while day < now.date():
        if day.isoformat() not in days:
            history["missing_dates"].append(day.isoformat())
        day += timedelta(days=1)
    return history


def token():
    if os.environ.get("GH_TOKEN"):
        return os.environ["GH_TOKEN"]
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT), "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True,
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never"), timeout=30,
    )
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if result.returncode or not fields.get("password"):
        raise RuntimeError("GitHub authentication unavailable; archive unchanged")
    return fields["password"]


def main():
    request = Request(
        f"https://api.github.com/repos/{REPOSITORY}/traffic/views?per=day",
        headers={"Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "pyNISAR-traffic-archive"},
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    history = json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else {
        "repository": REPOSITORY, "since": START, "days": {},
    }
    history = merge(history, payload, datetime.now(timezone.utc))
    temporary = ARCHIVE.with_suffix(".tmp")
    temporary.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    temporary.replace(ARCHIVE)
    count = history["accumulated_views"]
    label = "Recorded views" if history["missing_dates"] else "Accumulated views"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="270" height="28" role="img" aria-label="{label}: {count}">
<rect width="270" height="28" rx="4" fill="#263746"/><rect x="180" width="90" height="28" fill="#167d8d"/>
<g fill="white" font-family="Verdana,sans-serif" font-size="12" text-anchor="middle"><text x="90" y="19">{label}</text><text x="225" y="19">{count:,}</text></g></svg>\n'''
    (ROOT / "docs/assets").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/assets/traffic-views.svg").write_text(svg, encoding="utf-8")
    print(f"Archived {count} views since {START}; {len(history['missing_dates'])} missing dates.")


if __name__ == "__main__":
    main()

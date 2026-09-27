# Repository visits

The README badge sums GitHub page views recorded from **27 September 2026 UTC**.
The [daily archive](traffic-history.json) is retained in Git; it does not reset
monthly or when the repository becomes public. The latest timestamp is included
in the archive. Today's count is provisional and GitHub can revise recent days.

`tools/archive_traffic.py` reads the official GitHub traffic API. Each refresh
replaces overlapping daily observations rather than adding rolling totals.
Older observations remain stored. Daily unique visitors are preserved separately
and **never summed as lifetime unique people**. Views are not downloads, installs,
or use of the library. The library itself collects no telemetry.

## Daily collection

A daily Codex task on the owner's computer refreshes the archive and badge,
commits those two files, and pushes them to this repository. Codex must be running,
the computer available, and GitHub authentication valid. This is a local schedule,
not an unattended GitHub-hosted workflow. Repository visibility is not changed.

Manual refresh from the repository directory:

```bash
python tools/archive_traffic.py
```

Authentication uses `GH_TOKEN` or the existing Git credential manager; no token
is saved in the repository. GitHub requires access to repository traffic
(fine-grained tokens require Administration: read).

The collector revisits the latest 13 days plus today, avoiding the oldest rolling
window boundary. Short interruptions can be recovered. Longer interruptions may
leave missing dates, explicitly listed in the archive; the badge then says
"Recorded views" instead of implying complete coverage. Authentication/API
errors leave the previous archive unchanged. Neither GitHub nor this archive can
reconstruct older uncollected traffic.

## Countries

GitHub does not provide visitor countries or identities. The optional
[MapMyVisitors widget](https://mapmyvisitors.com/web/1c8hr) counts requests received
by that provider. GitHub's image proxy and caching mean its totals and locations
are **not reliable measurements of GitHub readers**. The accumulated-views badge
uses GitHub's API, never that widget's numbers.

Sources: [GitHub traffic API](https://docs.github.com/en/rest/metrics/traffic),
[GitHub image proxy](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-anonymized-urls).

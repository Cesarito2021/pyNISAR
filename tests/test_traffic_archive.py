"""Protect accumulated counts from overlapping snapshots and missing days."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location("traffic", Path(__file__).resolve().parents[1] / "tools/archive_traffic.py")
traffic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(traffic)


def test_overlap_replaces_counts_and_never_sums_unique_visitors():
    history = {"repository": traffic.REPOSITORY, "since": traffic.START, "days": {}}
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    payload = {"views": [{"timestamp": "2026-09-27T00:00:00Z", "count": 8, "uniques": 3}]}
    traffic.merge(history, payload, now)
    traffic.merge(history, payload, now)
    assert history["accumulated_views"] == 8
    payload["views"][0]["count"] = 9
    traffic.merge(history, payload, now)
    assert history["accumulated_views"] == 9
    assert "accumulated_unique_visitors" not in history


def test_old_days_survive_and_missing_days_are_explicit():
    history = {"repository": traffic.REPOSITORY, "since": traffic.START,
               "days": {"2026-09-27": {"views": 8, "daily_unique_visitors": 3}}}
    traffic.merge(history, {"views": []}, datetime(2026, 10, 20, tzinfo=timezone.utc))
    assert history["accumulated_views"] == 8
    assert "2026-09-28" in history["missing_dates"]
    assert "2026-10-07" not in history["missing_dates"]

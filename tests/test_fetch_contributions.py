"""Unit tests for scripts/fetch_contributions.py."""
import copy
import datetime
import pytest

from scripts.fetch_contributions import (
    build_contribution_data,
    compute_current_streak,
    compute_longest_streak,
    parse_contributions_html,
)


SAMPLE_HTML = """
<table>
  <tbody>
    <tr>
      <td id="c3" data-date="2026-11-18" data-level="2" class="ContributionCalendar-day"></td>
      <td id="c1" data-date="2026-11-16" data-level="0" class="ContributionCalendar-day"></td>
      <td id="c2" data-date="2026-11-17" data-level="1" class="ContributionCalendar-day"></td>
      <td id="c4" data-date="2026-11-19" data-level="0" class="ContributionCalendar-day"></td>
    </tr>
  </tbody>
</table>
<tool-tip for="c1">No contributions on November 16.</tool-tip>
<tool-tip for="c2">3 contributions on November 17.</tool-tip>
<tool-tip for="c3">12 contributions on November 18.</tool-tip>
<tool-tip for="c4">No contributions on November 19.</tool-tip>
"""


def test_parse_contributions_html_sorts_and_parses_counts():
    days = parse_contributions_html(SAMPLE_HTML)
    assert days == [
        {"date": "2026-11-16", "count": 0, "level": 0},
        {"date": "2026-11-17", "count": 3, "level": 1},
        {"date": "2026-11-18", "count": 12, "level": 2},
        {"date": "2026-11-19", "count": 0, "level": 0},
    ]


def test_parse_contributions_html_raises_when_empty():
    with pytest.raises(ValueError, match="no calendar cells found"):
        parse_contributions_html("<html><body><div>empty</div></body></html>")


def test_compute_current_streak_active_today():
    days = [
        {"date": "2026-11-17", "count": 0, "level": 0},
        {"date": "2026-11-18", "count": 4, "level": 1},
        {"date": "2026-11-19", "count": 2, "level": 1},
    ]
    assert compute_current_streak(days) == (2, "2026-11-18", "2026-11-19")


def test_compute_current_streak_zero_today_active_yesterday():
    days = [
        {"date": "2026-11-16", "count": 0, "level": 0},
        {"date": "2026-11-17", "count": 5, "level": 2},
        {"date": "2026-11-18", "count": 1, "level": 1},
        {"date": "2026-11-19", "count": 0, "level": 0},
    ]
    assert compute_current_streak(days) == (2, "2026-11-17", "2026-11-18")


def test_compute_current_streak_broken_and_empty():
    days = [
        {"date": "2026-11-17", "count": 5, "level": 2},
        {"date": "2026-11-18", "count": 0, "level": 0},
        {"date": "2026-11-19", "count": 0, "level": 0},
    ]
    assert compute_current_streak(days) == (0, None, None)
    assert compute_current_streak([]) == (0, None, None)


def test_compute_longest_streak_variants():
    days = [
        {"date": "2026-11-10", "count": 1, "level": 1},
        {"date": "2026-11-11", "count": 2, "level": 1},
        {"date": "2026-11-12", "count": 0, "level": 0},
        {"date": "2026-11-13", "count": 3, "level": 1},
        {"date": "2026-11-14", "count": 4, "level": 2},
        {"date": "2026-11-15", "count": 1, "level": 1},
    ]
    assert compute_longest_streak(days) == (3, "2026-11-13", "2026-11-15")
    assert compute_longest_streak([{"date": "2026-11-10", "count": 0, "level": 0}]) == (0, None, None)
    assert compute_longest_streak([]) == (0, None, None)


def test_build_contribution_data_stats_and_immutability():
    days = [
        {"date": "2026-10-30", "count": 10, "level": 2},
        {"date": "2026-10-31", "count": 0, "level": 0},
        {"date": "2026-11-01", "count": 5, "level": 1},
        {"date": "2026-11-02", "count": 25, "level": 3},
    ]
    snapshot = copy.deepcopy(days)
    ts = datetime.datetime(2026, 11, 19, 15, 0, 0, tzinfo=datetime.timezone.utc)
    result = build_contribution_data(days, username="Mahardika-Ramadhana", generated_at=ts)

    assert days == snapshot
    assert result["username"] == "Mahardika-Ramadhana"
    assert result["generated_at"] == "2026-11-19T15:00:00Z"
    assert result["range"] == {"start": "2026-10-30", "end": "2026-11-02"}
    assert result["total_contributions"] == 40
    assert result["active_days"] == 3
    assert result["avg_per_active_day"] == 13.3
    assert result["current_streak"] == {"length": 2, "start": "2026-11-01", "end": "2026-11-02"}
    assert result["longest_streak"] == {"length": 2, "start": "2026-11-01", "end": "2026-11-02"}
    assert result["best_day"] == {"date": "2026-11-02", "count": 25}
    assert result["monthly"] == [
        {"month": "2026-10", "total": 10},
        {"month": "2026-11", "total": 30},
    ]

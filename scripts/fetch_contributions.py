#!/usr/bin/env python3
"""
Scrape real daily contribution counts from GitHub's public, unauthenticated
contributions endpoint and write data/contributions.json with raw days plus
derived stats (current streak, longest streak, best day, monthly totals).
"""
import datetime
import json
import os
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

DEFAULT_USERNAME = "Mahardika-Ramadhana"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "..", "data", "contributions.json")


def fetch_contributions_html(username: str, timeout: int = 30) -> str:
    """Fetch public GitHub contributions calendar HTML for the given username."""
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(
        url,
        headers={"User-Agent": "profile-readme-bot/1.0"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.text


def parse_contributions_html(html: str) -> list[dict[str, Any]]:
    """Parse GitHub contribution calendar HTML into date-sorted day records."""
    soup = BeautifulSoup(html, "html.parser")
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        raise ValueError("no calendar cells found -- github markup may have changed")

    days: list[dict[str, Any]] = []
    for td in cells:
        date = td.get("data-date")
        if not date:
            continue
        td_id = td.get("id")
        tooltip_el = soup.find("tool-tip", attrs={"for": td_id}) if td_id else None
        text = tooltip_el.get_text(strip=True) if tooltip_el else ""
        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            match = re.match(r"(\d+)", text)
            count = int(match.group(1)) if match else 0
        days.append(
            {
                "date": str(date),
                "count": count,
                "level": int(td.get("data-level") or 0),
            }
        )

    days.sort(key=lambda d: d["date"])
    return days


def compute_current_streak(days: list[dict[str, Any]]) -> tuple[int, str | None, str | None]:
    """Return (length, start_date, end_date) for the active contribution streak."""
    if not days:
        return 0, None, None

    idx = len(days) - 1
    if days[idx]["count"] == 0:
        idx -= 1  # today is not over yet; do not break the streak on an incomplete day

    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1

    if streak == 0:
        return 0, None, None
    return streak, days[idx + 1]["date"], days[end_idx]["date"]


def compute_longest_streak(days: list[dict[str, Any]]) -> tuple[int, str | None, str | None]:
    """Return (length, start_date, end_date) for the longest contribution run."""
    longest = 0
    run = 0
    longest_start: str | None = None
    longest_end: str | None = None
    run_start_idx = 0

    for i, day in enumerate(days):
        if day["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = day["date"]
        else:
            run = 0

    return longest, longest_start, longest_end


def build_contribution_data(
    days: list[dict[str, Any]],
    username: str = DEFAULT_USERNAME,
    generated_at: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Compute derived statistics and return an immutable contributions payload."""
    if not days:
        raise ValueError("days must not be empty")

    copied_days = [dict(day) for day in days]
    timestamp = generated_at or datetime.datetime.now(datetime.timezone.utc)
    total = sum(d["count"] for d in copied_days)
    active_days = sum(1 for d in copied_days if d["count"] > 0)
    best = max(copied_days, key=lambda d: d["count"])
    cur_len, cur_start, cur_end = compute_current_streak(copied_days)
    long_len, long_start, long_end = compute_longest_streak(copied_days)

    monthly: dict[str, int] = {}
    for day in copied_days:
        key = day["date"][:7]
        monthly[key] = monthly.get(key, 0) + day["count"]
    monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

    return {
        "username": username,
        "generated_at": timestamp.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": copied_days[0]["date"], "end": copied_days[-1]["date"]},
        "total_contributions": total,
        "active_days": active_days,
        "avg_per_active_day": round(total / active_days, 1) if active_days else 0.0,
        "current_streak": {"length": cur_len, "start": cur_start, "end": cur_end},
        "longest_streak": {"length": long_len, "start": long_start, "end": long_end},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly_list,
        "days": copied_days,
    }


def main() -> None:
    """Fetch GitHub contributions and write data/contributions.json."""
    username = os.environ.get("GH_PROFILE_USER", DEFAULT_USERNAME)
    html = fetch_contributions_html(username)
    days = parse_contributions_html(html)
    data = build_contribution_data(days, username=username)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(
        f"wrote {OUT_PATH}: {data['total_contributions']} contributions, "
        f"current streak {data['current_streak']['length']}, "
        f"longest streak {data['longest_streak']['length']}"
    )


if __name__ == "__main__":
    main()

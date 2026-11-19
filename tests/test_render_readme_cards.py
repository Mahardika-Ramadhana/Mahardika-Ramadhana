"""Unit tests for scripts/render_readme_cards.py."""
import copy
import datetime
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.render_readme_cards import (
    EXPECTED_CARDS,
    count_up,
    level_for,
    render_all,
    wrap,
)


def make_sample_data(all_zero: bool = False) -> dict:
    """Build deterministic contributions payload spanning 369 days."""
    start = datetime.date(2025, 11, 16)
    days = []
    for i in range(369):
        d = start + datetime.timedelta(days=i)
        count = 0 if all_zero else ((i % 7) * 5 if i % 3 == 0 else 0)
        days.append({"date": d.isoformat(), "count": count, "level": min(4, count // 5)})

    monthly_map: dict[str, int] = {}
    for day in days:
        key = day["date"][:7]
        monthly_map[key] = monthly_map.get(key, 0) + day["count"]
    monthly = [{"month": k, "total": v} for k, v in sorted(monthly_map.items())]

    best = max(days, key=lambda x: x["count"])
    return {
        "username": "Mahardika-Ramadhana",
        "generated_at": "2026-11-19T15:00:00Z",
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": sum(d["count"] for d in days),
        "active_days": sum(1 for d in days if d["count"] > 0),
        "avg_per_active_day": 10.0 if not all_zero else 0.0,
        "current_streak": {"length": 0 if all_zero else 3, "start": None, "end": None},
        "longest_streak": {"length": 0 if all_zero else 12, "start": None, "end": None},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly,
        "days": days,
    }


def test_wrap_preserves_words_and_respects_limit():
    text = "Autonomous robotics, ROS 2 bipedal kinematics & C++ deep learning"
    lines = wrap(text, 24)
    assert len(lines) >= 2
    assert all(len(line) <= 24 for line in lines)
    assert " ".join(lines) == text


def test_count_up_animated_and_static():
    for target, word in [("3", "podiums"), ("10K+", "runs"), ("5", "titles")]:
        anim = count_up(target, word, 22, 112, 'font-size="44"', begin=3.55, static=False)
        assert anim.count("<text ") == 19
        assert "<set attributeName=\"opacity\" to=\"1\"" in anim
        assert f">{target} " in anim
        assert word in anim

        st = count_up(target, word, 22, 112, 'font-size="44"', begin=3.55, static=True)
        assert st.count("<text ") == 1
        assert "<set " not in st
        assert f">{target} " in st


def test_level_for_thresholds():
    assert level_for(0) == 0
    assert level_for(1) == 1
    assert level_for(5) == 1
    assert level_for(6) == 2
    assert level_for(15) == 2
    assert level_for(16) == 3
    assert level_for(30) == 3
    assert level_for(31) == 4
    assert level_for(50) == 4
    assert level_for(51) == 5


def test_render_all_animated_valid_xml_and_sandbox_safe(tmp_path: Path):
    data = make_sample_data()
    snapshot = copy.deepcopy(data)

    written = render_all(
        data,
        out_dir=tmp_path,
        static=False,
        stars={"dish-counter-apparatus": 4, "mlaku-mulu": 0, "neetcode-gpt": 2},
    )

    assert data == snapshot
    assert sorted(p.name for p in written) == sorted(EXPECTED_CARDS)

    for svg_path in written:
        content = svg_path.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        assert root.tag.endswith("svg")
        assert "@font-face" in content
        assert "data:font/woff;base64," in content
        assert "@media (prefers-reduced-motion: reduce)" in content
        assert "<script" not in content.lower()
        assert "<foreignobject" not in content.lower()
        assert not re.search(r"url\(\s*['\"]?https?://", content, re.I)

    robotics_svg = (tmp_path / "robotics.svg").read_text(encoding="utf-8")
    assert '<set attributeName="opacity"' in robotics_svg
    hero_svg = (tmp_path / "hero.svg").read_text(encoding="utf-8")
    assert "<animateTransform" in hero_svg
    repo_svg = (tmp_path / "repo-dish-counter-apparatus.svg").read_text(encoding="utf-8")
    assert "★ 4" in repo_svg


def test_render_all_static_mode_and_zero_contributions(tmp_path: Path):
    zero_data = make_sample_data(all_zero=True)
    written = render_all(
        zero_data,
        out_dir=tmp_path,
        static=True,
        stars={},
    )

    assert len(written) == len(EXPECTED_CARDS)
    for svg_path in written:
        content = svg_path.read_text(encoding="utf-8")
        ET.fromstring(content)
        assert "animation:none!important" in content
        assert "<set " not in content

    activity_svg = (tmp_path / "activity.svg").read_text(encoding="utf-8")
    assert "0 " in activity_svg

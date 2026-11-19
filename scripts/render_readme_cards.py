#!/usr/bin/env python3
"""
Render the Mahardika-Ramadhana profile README's cards as animated SVGs into cards/.

Design: Dark Cyber-Robotics matched to https://mahardikaramadhana.vercel.app
(#070c12/#0c141e void surfaces, #00e5ff cyan, #ff3b00 crimson, #0077b6 cobalt;
Cabinet Grotesk, General Sans, JetBrains Mono).

Every card is a standalone SVG shown through <img> or <picture>, using only what
GitHub's README sanitizer permits: inline CSS animations, SMIL <animateTransform> /
<set>, and subsetted static WOFF fonts embedded as base64 data URIs.
"""
import base64
import datetime
import json
import os
import re
from html import escape
from pathlib import Path
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA_PATH = os.path.join(ROOT, "data", "contributions.json")
DEFAULT_OUT = os.path.join(ROOT, "cards")
FONTS_DIR = os.path.join(ROOT, "fonts")

# ---- Design tokens matched to mahardikaramadhana.vercel.app -----------------
VOID = "#04070b"
BG_DARK = "#070c12"
BG_CARD_TOP = "#101c2a"
BG_CARD_FALLBACK = "#0c141e"
INK_FG = "#e8f4fa"
INK_BODY = "#b8d0e0"
INK_MUTED = "#7a94aa"
INK_LIGHT = "#070c12"

CYAN = "#00e5ff"
CRIMSON = "#ff3b00"
COBALT = "#0077b6"
SKY = "#38bdf8"

HEATMAP_RAMP = ["#111d2b", "#0a3a4f", "#006580", "#0099b8", "#00cce8", CYAN]
BAR_MUTED = "#2b445c"
BAR_PARTIAL = "#1a2c3d"

W = 880
GAP = 12
BOTTOM = 12
TILE_W = W / 3 - 8  # 285.333...
TILE_H = 212
REPO_W = W / 3 - 8
REPO_H = 184

DISP = "'Cabinet Grotesk', system-ui, -apple-system, sans-serif"
SANS = "'General Sans', system-ui, -apple-system, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

FONT_FILES = {
    "disp-800": ("Cabinet Grotesk", "normal", 800, "cabinet-800.woff"),
    "disp-600": ("Cabinet Grotesk", "normal", 600, "cabinet-600.woff"),
    "sans-400": ("General Sans", "normal", 400, "general-400.woff"),
    "sans-600": ("General Sans", "normal", 600, "general-600.woff"),
    "mono-400": ("JetBrains Mono", "normal", 400, "jetbrains-400.woff"),
}

EXPECTED_CARDS = (
    "hero.svg",
    "heatmap.svg",
    "activity.svg",
    "robotics.svg",
    "ai.svg",
    "honors.svg",
    "title-coding-dark.svg",
    "title-coding-light.svg",
    "repo-dish-counter-apparatus.svg",
    "repo-mlaku-mulu.svg",
    "repo-neetcode-gpt.svg",
)

REPOS = (
    (
        "dish-counter-apparatus",
        "Edge-AI POS fusing YOLOv11 vision with load-cell telemetry & QRIS.",
        "Python",
        "Edge-AI",
        CYAN,
    ),
    (
        "mlaku-mulu",
        "NestJS & Prisma backend API for tourist and trip management.",
        "TypeScript",
        "NestJS",
        CRIMSON,
    ),
    (
        "neetcode-gpt",
        "GPT built from scratch in PyTorch: attention, Transformers & RMSNorm.",
        "Python",
        "PyTorch",
        SKY,
    ),
)

BASE_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(4px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
.live{animation:pulse 1.6s ease-in-out infinite}
.n{transform-box:fill-box;animation:nudge 1.8s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
@keyframes tilein{0%{opacity:0;transform:translateY(90px) scale(.6) rotate(-9deg)}55%{opacity:1;transform:translateY(-10px) scale(1.05) rotate(2deg)}75%{transform:translateY(3px) scale(.98) rotate(-.8deg)}90%{transform:translateY(-1px) scale(1.01) rotate(.2deg)}100%{opacity:1;transform:none}}
@keyframes slidein{from{opacity:0;transform:translateX(-26px)}to{opacity:1;transform:none}}
@keyframes arrowin{0%{opacity:0;transform:translateX(-30px)}60%{opacity:1;transform:translateX(6px)}100%{opacity:1;transform:none}}
@keyframes roll{from{transform:translateY(60px)}to{transform:none}}
@keyframes sheen{0%{transform:translateX(-260px) skewX(-20deg)}22%,100%{transform:translateX(420px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.7;transform:scale(.2)}100%{opacity:0;transform:scale(2.4)}}
.ti{opacity:0;transform-box:fill-box;transform-origin:50% 60%;animation:tilein 1.1s cubic-bezier(.2,.8,.2,1) both}
.sl{opacity:0;transform-box:fill-box;animation:slidein .6s cubic-bezier(.2,.7,.2,1) both}
.ai{opacity:0;transform-box:fill-box;animation:arrowin .7s cubic-bezier(.2,.7,.2,1) both}
.ro{transform-box:fill-box;animation:roll .8s cubic-bezier(.15,.8,.2,1) both}
.sh{animation:sheen 5s ease-in-out infinite}
.rg{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 1s ease-out both}
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.rg{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}}
"""


def font_face(keys: list[str]) -> str:
    """Build embedded @font-face CSS blocks for the requested font keys."""
    out = []
    for k in keys:
        fam, style, weight, fn = FONT_FILES[k]
        with open(os.path.join(FONTS_DIR, fn), "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        out.append(
            f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
            f"src:url(data:font/woff;base64,{b64}) format('woff')}}"
        )
    return "".join(out)


def svg(
    w: float,
    h: int,
    body: str,
    fonts: list[str],
    label: str,
    static: bool = False,
    extra_css: str = "",
    left: float = 0,
    right: float = 0,
    bottom: int = BOTTOM,
) -> str:
    """Wrap card markup inside a standalone SVG canvas with embedded fonts and CSS."""
    if left:
        body = f'<g transform="translate({left:.3f} 0)">{body}</g>'
    total_w = w + left + right
    total_h = h + bottom
    css = font_face(fonts) + BASE_CSS + extra_css
    if static:
        css += (
            ".r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro{animation:none!important;opacity:1!important;transform:none!important}"
            ".sh,.rg{display:none}"
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w:.3f}" height="{total_h}" '
        f'viewBox="0 0 {total_w:.3f} {total_h}" role="img" aria-label="{escape(label)}">'
        f"<title>{escape(label)}</title><style>{css}</style>{body}</svg>"
    )


def write_card(out_dir: str | Path, name: str, content: str) -> Path:
    """Write SVG content to out_dir/name and return its Path."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    target = out_path / name
    target.write_text(content, encoding="utf-8")
    print(f"wrote {target} ({len(content) // 1024} KB)")
    return target


def d(seconds: float) -> str:
    """Return an inline CSS animation-delay style attribute."""
    return f'style="animation-delay:{seconds:.2f}s"'


def wrap(text: str, max_chars: int) -> list[str]:
    """Greedy word-wrap without dropping or mutating words."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    return lines + [current] if current else lines


def text_lines(x: float, y: float, lines: list[str], line_height: int, attrs: str) -> str:
    """Render wrapped lines as stacked SVG <text> nodes."""
    return "".join(
        f'<text x="{x}" y="{y + i * line_height}" {attrs}>{escape(line)}</text>'
        for i, line in enumerate(lines)
    )


def card_surface(w: float, h: int, grad_id: str = "cardbg", extra_defs: str = "") -> str:
    """Return dark cyber-robotics gradient surface defs, fill rect, and subtle cyan border."""
    return (
        f'<defs>'
        f'<linearGradient id="{grad_id}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG_CARD_TOP}"/>'
        f'<stop offset="1" stop-color="{BG_DARK}"/>'
        f"</linearGradient>"
        f"{extra_defs}"
        f"</defs>"
        f'<rect width="{w:.3f}" height="{h}" rx="14" fill="url(#{grad_id})"/>'
        f'<rect x="0.5" y="0.5" width="{w - 1:.3f}" height="{h - 1}" rx="14" fill="none" '
        f'stroke="{CYAN}" stroke-opacity="0.22" stroke-width="1"/>'
    )


def render_hero(data: dict[str, Any], out_dir: str | Path, static: bool = False) -> Path:
    """Render Card 1: typography + live status hero card."""
    h = 330
    total = int(data["total_contributions"])

    grid_lines = []
    for gx in range(44, W, 44):
        grid_lines.append(
            f'<line x1="{gx}" y1="0" x2="{gx}" y2="{h}" stroke="{CYAN}" stroke-opacity="0.045" stroke-width="1"/>'
        )
    for gy in range(44, h, 44):
        grid_lines.append(
            f'<line x1="0" y1="{gy}" x2="{W}" y2="{gy}" stroke="{CYAN}" stroke-opacity="0.045" stroke-width="1"/>'
        )

    brackets = (
        f'<g stroke="{CYAN}" stroke-opacity="0.42" stroke-width="1.5" fill="none">'
        f'<path d="M16 28V16H28"/>'
        f'<path d="M{W - 28} 16H{W - 16}V28"/>'
        f'<path d="M16 {h - 28}V{h - 16}H28"/>'
        f'<path d="M{W - 28} {h - 16}H{W - 16}V{h - 28}"/>'
        f"</g>"
    )

    shine_anim = (
        ""
        if static
        else '<animateTransform attributeName="gradientTransform" type="translate" '
        'values="-620 0;680 0;680 0" keyTimes="0;.45;1" dur="6.5s" begin="1.4s" repeatCount="indefinite"/>'
    )
    name_fill = INK_FG if static else "url(#shine)"

    extra_defs = (
        f'<clipPath id="heroclip"><rect width="{W}" height="{h}" rx="14"/></clipPath>'
        f'<radialGradient id="heroglow" cx="85%" cy="18%" r="55%">'
        f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0.11"/>'
        f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>'
        f"</radialGradient>"
        f'<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="620" y2="0">'
        f'<stop offset="0" stop-color="{INK_FG}"/><stop offset=".40" stop-color="{INK_FG}"/>'
        f'<stop offset=".50" stop-color="{CYAN}"/><stop offset=".60" stop-color="{INK_FG}"/>'
        f'<stop offset="1" stop-color="{INK_FG}"/>'
        f"{shine_anim}"
        f"</linearGradient>"
    )

    tagline = [
        "Autonomous robotics, ROS 2 bipedal kinematics & C++ deep learning",
        "at Universitas Gadjah Mada — 1st Place Global HVAC 2026 Japan.",
    ]

    body = f"""
{card_surface(W, h, "herobg", extra_defs)}
<g clip-path="url(#heroclip)">
  <rect width="{W}" height="{h}" fill="url(#heroglow)"/>
  {''.join(grid_lines)}
</g>
{brackets}
<g class="f" {d(0)}>
  <rect class="live" x="44" y="37" width="8" height="8" rx="2" fill="{CYAN}"/>
  <text x="62" y="45" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{INK_MUTED}">ROBOTICS SOFTWARE &amp; AI ENGINEER // UGM</text>
  <text x="{W - 44}" y="45" text-anchor="end" font-family="{MONO}" font-size="11.5" letter-spacing="0.8" fill="{INK_MUTED}">YOGYAKARTA, ID  &#183;  <tspan fill="{CYAN}">{total:,}</tspan> COMMITS / YR</text>
</g>
<text class="r" {d(0.15)} x="42" y="138" font-family="{DISP}" font-weight="800" font-size="78" letter-spacing="-2.2" fill="{INK_FG}">Mahardika</text>
<text class="r" {d(0.30)} x="42" y="214" font-family="{DISP}" font-weight="800" font-size="78" letter-spacing="-2.2" fill="{name_fill}">Ramadhana</text>
<g class="r" {d(0.50)}>
  {text_lines(44, 250, tagline, 24, f'font-family="{SANS}" font-weight="400" font-size="16.5" fill="{INK_BODY}"')}
</g>
<g class="f" {d(0.72)}>
  <text x="44" y="306" font-family="{MONO}" font-size="12.5" fill="{INK_FG}">mahardikaramadhana.vercel.app</text>
  <text class="nu" x="268" y="306" font-family="{MONO}" font-size="13" fill="{CYAN}">&#8599;</text>
  <text x="{W - 44}" y="306" text-anchor="end" font-family="{MONO}" font-size="11.5" letter-spacing="0.8" fill="{INK_MUTED}">ROS 2 &#183; C++17 &#183; PYTORCH &#183; TYPESCRIPT</text>
</g>
"""
    return write_card(
        out_dir,
        "hero.svg",
        svg(
            W,
            h,
            body,
            ["disp-800", "sans-400", "mono-400"],
            "Mahardika Ramadhana — Robotics Software & AI Engineer at Universitas Gadjah Mada.",
            static=static,
        ),
    )


def level_for(count: int) -> int:
    """Map daily contribution count to a 0..5 cyber-cyan intensity bucket."""
    if count <= 0:
        return 0
    if count <= 5:
        return 1
    if count <= 15:
        return 2
    if count <= 30:
        return 3
    if count <= 50:
        return 4
    return 5


def render_heatmap(data: dict[str, Any], out_dir: str | Path, static: bool = False) -> Path:
    """Render Card 2: cyber-cyan daily contribution heatmap."""
    days = data["days"]
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7
    cell, step, gy = 12, 15, 88
    ncols = (len(days) + lead + 6) // 7
    grid_w = ncols * step - 3
    gx = max(32.0, (W - grid_w) / 2)
    right = gx + grid_w

    cells, months, seen = [], [], set()
    for i, day in enumerate(days):
        k = i + lead
        col, row = divmod(k, 7)
        dt = datetime.date.fromisoformat(day["date"])
        if dt.day <= 7 and (dt.year, dt.month) not in seen and row == 0:
            seen.add((dt.year, dt.month))
            months.append((col, dt.strftime("%b")))
        c = int(day["count"])
        delay = 1.0 + col * 0.03 + row * 0.02
        suffix = "s" if c != 1 else ""
        cells.append(
            f'<rect class="p" style="animation-delay:{delay:.2f}s" x="{gx + col * step:.1f}" '
            f'y="{gy + row * step}" width="{cell}" height="{cell}" rx="3" fill="{HEATMAP_RAMP[level_for(c)]}">'
            f'<title>{escape(day["date"])}: {c} contribution{suffix}</title></rect>'
        )

    legend_x = right - len(HEATMAP_RAMP) * 14 - 32
    labels = "".join(
        f'<text x="{gx + col * step:.1f}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{INK_MUTED}">{m}</text>'
        for col, m in months
        if gx + col * step < legend_x - 64
    )
    legend = "".join(
        f'<rect x="{legend_x + i * 14:.1f}" y="{gy + 7 * step + 6}" width="11" height="11" rx="2.5" fill="{col_hex}"/>'
        for i, col_hex in enumerate(HEATMAP_RAMP)
    )
    h = gy + 7 * step + 48
    total = int(data["total_contributions"])
    body = f"""
{card_surface(W, h, "heatbg")}
<text class="r" {d(0.80)} x="{gx:.1f}" y="54" font-family="{DISP}" font-weight="600" font-size="32" fill="{INK_FG}">Every day, <tspan fill="{CYAN}">in cyan</tspan></text>
<text class="f" {d(0.80)} x="{right:.1f}" y="52" text-anchor="end" font-family="{MONO}" font-size="11.5" letter-spacing="1" fill="{INK_MUTED}">REFRESHED DAILY</text>
{''.join(cells)}
<g class="f" {d(2.40)}>
  {labels}
  <text x="{legend_x - 8:.1f}" y="{gy + 7 * step + 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{INK_MUTED}">less</text>
  {legend}
  <text x="{right:.1f}" y="{gy + 7 * step + 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{INK_MUTED}">more</text>
</g>
"""
    return write_card(
        out_dir,
        "heatmap.svg",
        svg(
            W,
            h,
            body,
            ["disp-600", "mono-400"],
            f"Contribution graph: {total:,} contributions in the last year",
            static=static,
        ),
    )


def render_activity(data: dict[str, Any], out_dir: str | Path, static: bool = False) -> Path:
    """Render Card 3: 12-month contribution bar chart and streak/day KPIs."""
    h = 340
    monthly = data["monthly"][-12:]
    completed = monthly[:-1] or monthly
    best = max(completed, key=lambda m: m["total"])
    top = max(1, max(m["total"] for m in monthly))
    x0, x1, base, maxh, gap = 40, 596, 290, 136, 10
    bw = (x1 - x0 - gap * (len(monthly) - 1)) / max(1, len(monthly))

    bars = []
    for i, m in enumerate(monthly):
        partial = i == len(monthly) - 1
        is_best = m is best and m["total"] > 0
        bh = max(4, round(m["total"] / top * maxh))
        x = x0 + i * (bw + gap)
        fill = CYAN if is_best else (BAR_PARTIAL if partial else BAR_MUTED)
        stroke_attr = f' stroke="{CYAN}" stroke-opacity="0.35" stroke-width="1"' if partial and not is_best else ""
        label = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")
        bars.append(
            f'<rect class="g" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x:.1f}" y="{base - bh}" '
            f'width="{bw:.1f}" height="{bh}" rx="4" fill="{fill}"{stroke_attr}><title>{label}: {m["total"]:,}</title></rect>'
            f'<text class="f" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x + bw / 2:.1f}" y="{base + 22}" '
            f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{INK_MUTED}">{label}</text>'
        )
        if is_best:
            bars.append(
                f'<text class="p" style="animation-delay:3.20s" x="{x + bw / 2:.1f}" y="{base - bh - 10}" '
                f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{CYAN}">{m["total"]:,}</text>'
            )

    cs = int(data["current_streak"]["length"])
    ls = int(data["longest_streak"]["length"])
    streak_note = "current streak, and the longest" if cs >= ls and cs > 0 else f"current streak, longest {ls}"
    total_days = len(data["days"])
    best_count = int(data["best_day"]["count"])
    best_date = data["best_day"].get("date")
    if best_date and best_count > 0:
        best_fmt = datetime.date.fromisoformat(best_date).strftime("%b %d").replace(" 0", " ")
        best_note = f"busiest day ({best_fmt})"
    else:
        best_note = "on the busiest day"

    day_word = "day" if cs == 1 else "days"
    stats = [
        (f'{cs} <tspan fill="{CYAN}">{day_word}</tspan>', streak_note),
        (f'{int(data["active_days"])}<tspan fill="{INK_MUTED}"> / {total_days}</tspan>', "days with a commit"),
        (f"{best_count}", best_note),
    ]

    side = []
    for i, (big, small) in enumerate(stats):
        y = 98 + i * 92
        side.append(
            f'<g class="r" {d(2.60 + i * 0.15)}>'
            f'<text x="644" y="{y}" font-family="{DISP}" font-weight="800" font-size="36" fill="{INK_FG}">{big}</text>'
            f'<text x="644" y="{y + 24}" font-family="{SANS}" font-weight="400" font-size="13" fill="{INK_MUTED}">{escape(small)}</text>'
            f"</g>"
        )
        if i < 2:
            side.append(
                f'<rect class="f" {d(2.60)} x="644" y="{y + 44}" width="196" height="1" fill="{CYAN}" opacity="0.16"/>'
            )

    total = int(data["total_contributions"])
    body = f"""
{card_surface(W, h, "actbg")}
<text class="f" {d(1.90)} x="40" y="56" font-family="{MONO}" font-size="11.5" letter-spacing="1" fill="{INK_MUTED}">THE LAST 12 MONTHS ON GITHUB</text>
<text class="r" {d(2.00)} x="38" y="108" font-family="{DISP}" font-weight="800" font-size="46" fill="{INK_FG}">{total:,} <tspan fill="{CYAN}">contributions</tspan></text>
{''.join(bars)}
{''.join(side)}
"""
    return write_card(
        out_dir,
        "activity.svg",
        svg(
            W,
            h,
            body,
            ["disp-800", "sans-400", "mono-400"],
            f"{total:,} contributions in the last year, {cs}-day streak",
            static=static,
        ),
    )


def count_up(
    num: str,
    word: str,
    x: float,
    y: float,
    attrs: str,
    begin: float,
    static: bool = False,
    dur: float = 1.1,
    frames: int = 18,
) -> str:
    """Animate numeric counter using SMIL <set> frames (or render final frame when static=True)."""
    m = re.match(r"([\d.]+)(.*)", num)
    if not m:
        return f'<text x="{x}" y="{y}" {attrs}>{escape(num)} {escape(word)}</text>'
    val, suf = float(m.group(1)), m.group(2)
    dec = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
    tail = f" {escape(word)}"
    if static:
        return f'<text x="{x}" y="{y}" {attrs}>{escape(num)}{tail}</text>'

    out = []
    for i in range(frames + 1):
        ease = 1 - (1 - i / frames) ** 3
        txt = num if i == frames else f"{val * ease:.{dec}f}{suf}"
        on = begin + dur * i / frames
        off = (
            ""
            if i == frames
            else f'<set attributeName="opacity" to="0" begin="{begin + dur * (i + 1) / frames:.3f}s"/>'
        )
        out.append(
            f'<text x="{x}" y="{y}" {attrs} opacity="0">{escape(txt)}{tail}'
            f'<set attributeName="opacity" to="1" begin="{on:.3f}s"/>{off}</text>'
        )
    return "".join(out)


def render_tile(
    out_dir: str | Path,
    name: str,
    label: str,
    color: str,
    on: str,
    num: str,
    word: str,
    blurb: str,
    delay: float,
    pos: int,
    static: bool = False,
) -> Path:
    """Render Cards 4-6: one animated spotlight world tile."""
    lines = wrap(blurb, 31)
    blurb_svg = "".join(
        f'<text class="r" {d(delay + 0.75 + i * 0.1)} x="24" y="{148 + i * 20}" font-family="{SANS}" '
        f'font-weight="400" font-size="13.5" fill="{on}" opacity=".90">{escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    body = f"""
<defs>
  <clipPath id="card"><rect width="{TILE_W:.3f}" height="{TILE_H}" rx="14"/></clipPath>
  <clipPath id="slot"><rect x="0" y="60" width="{TILE_W:.3f}" height="64"/></clipPath>
  <linearGradient id="gl" x1="0" x2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".35"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
</defs>
<g class="ti" {d(delay)}>
  <g clip-path="url(#card)">
    <rect width="{TILE_W:.3f}" height="{TILE_H}" fill="{color}"/>
    <circle class="rg" {d(delay + 0.50)} cx="{TILE_W - 40:.3f}" cy="{TILE_H - 40}" r="60" fill="none" stroke="{on}" stroke-opacity=".45" stroke-width="2"/>
    <rect class="sh" style="animation-delay:{delay + 1.4:.2f}s" x="0" y="-20" width="90" height="{TILE_H + 40}" fill="url(#gl)" transform="translate(-260 0)"/>
  </g>
  <text class="sl" {d(delay + 0.35)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{on}">{escape(label)}</text>
  <g class="ai" {d(delay + 0.50)}>
    <text class="n" style="animation-delay:{delay + 1.3:.2f}s" x="249" y="38" font-family="{MONO}" font-size="14" fill="{on}">&#8594;</text>
  </g>
  <g clip-path="url(#slot)">
    <g class="ro" {d(delay + 0.45)}>
      {count_up(num, word, 22, 110, f'font-family="{DISP}" font-weight="800" font-size="38" letter-spacing="-1" fill="{on}"', delay + 0.45, static=static)}
    </g>
  </g>
  {blurb_svg}
</g>
"""
    return write_card(
        out_dir,
        f"{name}.svg",
        svg(
            TILE_W,
            TILE_H,
            body,
            ["disp-800", "sans-400", "mono-400"],
            f"{label}: {num} {word}. {blurb}",
            static=static,
            left=4 * pos,
            right=8 - 4 * pos,
        ),
    )


def render_section_title(
    out_dir: str | Path,
    text: str,
    accent: str,
    theme: str,
    static: bool = False,
) -> Path:
    """Render Cards 7-8: light/dark adaptive section header."""
    fg = INK_FG if theme == "dark" else INK_LIGHT
    accent_color = CYAN if theme == "dark" else COBALT
    body = (
        f'<text class="r" {d(4.40)} x="2" y="42" font-family="{DISP}" font-weight="600" '
        f'font-size="30" letter-spacing="-0.6" fill="{fg}">{escape(text)} '
        f'<tspan fill="{accent_color}">{escape(accent)}</tspan></text>'
    )
    return write_card(
        out_dir,
        f"title-coding-{theme}.svg",
        svg(
            W,
            58,
            body,
            ["disp-600"],
            f"{text} {accent}",
            static=static,
            bottom=0,
        ),
    )


def render_repo_card(
    out_dir: str | Path,
    idx: int,
    name: str,
    desc: str,
    lang: str,
    fallback_tag: str,
    color: str,
    stars: int,
    static: bool = False,
) -> Path:
    """Render Cards 9-11: featured repository card."""
    delay = 4.60 + idx * 0.12
    meta = f"{lang}  ·  ★ {stars}" if stars > 0 else f"{lang}  ·  {fallback_tag}"
    lines = wrap(desc, 31)
    body = f"""
{card_surface(REPO_W, REPO_H, f"repobg{idx}")}
<g class="r" {d(delay)}>
  <rect x="22" y="29" width="8" height="8" rx="2" fill="{color}"/>
  <text x="38" y="38" font-family="{SANS}" font-weight="600" font-size="15.5" fill="{INK_FG}">{escape(name)}</text>
  <text class="nu" style="animation-delay:{delay + 0.8:.2f}s" x="252" y="38" font-family="{MONO}" font-size="13" fill="{color}">&#8599;</text>
  {text_lines(22, 74, lines, 20, f'font-family="{SANS}" font-weight="400" font-size="13.5" fill="{INK_BODY}"')}
  <text x="22" y="{REPO_H - 24}" font-family="{MONO}" font-size="12" fill="{INK_MUTED}">{escape(meta)}</text>
</g>
"""
    return write_card(
        out_dir,
        f"repo-{name}.svg",
        svg(
            REPO_W,
            REPO_H,
            body,
            ["sans-400", "sans-600", "mono-400"],
            f"{name}: {desc}",
            static=static,
            left=4 * idx,
            right=8 - 4 * idx,
        ),
    )


def fetch_repo_stars(username: str) -> dict[str, int]:
    """Fetch public stargazer counts for featured repos; degrade gracefully offline."""
    stars: dict[str, int] = {}
    try:
        import requests

        headers = {"User-Agent": "profile-readme-bot/1.0"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        for name, *_ in REPOS:
            resp = requests.get(
                f"https://api.github.com/repos/{username}/{name}",
                headers=headers,
                timeout=10,
            )
            if resp.ok:
                stars[name] = int(resp.json().get("stargazers_count", 0))
    except Exception as exc:
        print(f"stars unavailable: {exc}")
    return stars


def render_all(
    data: dict[str, Any],
    out_dir: str | Path = DEFAULT_OUT,
    static: bool = False,
    stars: dict[str, int] | None = None,
) -> list[Path]:
    """Render all 11 SVG cards into out_dir without mutating data."""
    username = data.get("username", "Mahardika-Ramadhana")
    star_map = stars if stars is not None else fetch_repo_stars(username)

    written = [
        render_hero(data, out_dir, static=static),
        render_heatmap(data, out_dir, static=static),
        render_activity(data, out_dir, static=static),
        render_tile(
            out_dir,
            "robotics",
            "ROBOTICS",
            CYAN,
            VOID,
            "3",
            "podiums",
            "HVAC 2026 Japan (1st Athletics, 3rd Sprint & Dance) & ROS 2 GMRT Fukuro.",
            3.10,
            0,
            static=static,
        ),
        render_tile(
            out_dir,
            "ai",
            "AI & ML",
            CRIMSON,
            "#ffffff",
            "10K+",
            "runs",
            "UGM neural research, custom C++ engines, YOLOv11 edge-AI & RL systems.",
            3.35,
            1,
            static=static,
        ),
        render_tile(
            out_dir,
            "honors",
            "HONORS",
            COBALT,
            INK_FG,
            "5",
            "titles",
            "HVAC 2026 Japan 1st, OSN Informatics & Math 1st, 2x UGM Chess Champ.",
            3.60,
            2,
            static=static,
        ),
        render_section_title(out_dir, "Featured", "repositories", "dark", static=static),
        render_section_title(out_dir, "Featured", "repositories", "light", static=static),
    ]

    for idx, (name, desc, lang, tag, color) in enumerate(REPOS):
        written.append(
            render_repo_card(
                out_dir,
                idx,
                name,
                desc,
                lang,
                tag,
                color,
                int(star_map.get(name, 0)),
                static=static,
            )
        )

    return written


def main() -> None:
    """Load data/contributions.json and render all SVG cards."""
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    static = bool(os.environ.get("STATIC"))
    out_dir = os.environ.get("OUT_DIR", DEFAULT_OUT)
    render_all(data, out_dir=out_dir, static=static)


if __name__ == "__main__":
    main()

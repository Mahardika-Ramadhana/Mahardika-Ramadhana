#!/usr/bin/env python3
"""
Render the Mahardika-Ramadhana profile README's cards as animated SVGs into cards/.

Design: Cross-Stitch Ember & Aida Linen matched to the user's cross-stitch
burning-car profile picture (warm woven Aida linen surfaces, charcoal soot
typography, saddle-brown vintage sedan accents, and fiery red/orange/gold
ember stitches; Cabinet Grotesk, General Sans, JetBrains Mono).

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

# ---- Design tokens matched to cross-stitch burning-car profile picture -----
LINEN_TOP = "#f4ecda"
LINEN_BASE = "#ebe1cd"
LINEN_BOT = "#e5d9c2"
LINEN_WEAVE = "#cbbca2"
LINEN_PINHOLE = "#b3a082"
LINEN_BORDER = "#bfae91"
LINEN_STITCH = "#a69274"

SOOT_DARK = "#1f1c14"
SMOKE_MID = "#252219"
SMOKE_LIGHT = "#464032"
INK_MUTED = "#736450"
ON_DARK = "#f6eedd"

WALNUT_DARK = "#5e331b"
WALNUT = "#6e3d21"
WALNUT_MID = "#8a502c"
WALNUT_LIGHT = "#b5794c"
CHROME = "#d0cabd"

BLAZE_TILE = "#b83217"
BLAZE_TEXT = "#b53015"
BLAZE_RED = "#cf3b1a"
EMBER_ORANGE = "#e66b26"
FLAME_GOLD = "#f0b443"
FLAME_CREAM = "#f7df94"
AMBER_REPO = "#c97816"

HEATMAP_RAMP = ["#dfd4be", "#f2c66d", "#eb8c34", "#de5622", "#bd2e16", "#6f1a10"]
BAR_MUTED = "#8e7b63"
BAR_PARTIAL = "#d6c8b0"

STITCH_PALETTE: dict[str, tuple[str, str]] = {
    "M": ("#232018", "smk1"),
    "S": ("#403a2c", "smk2"),
    "R": (BLAZE_RED, "flk1"),
    "O": (EMBER_ORANGE, "flk2"),
    "Y": (FLAME_GOLD, "flk1"),
    "W": (FLAME_CREAM, "flk2"),
    "K": ("#1e1b14", ""),
    "D": (WALNUT_DARK, ""),
    "B": (WALNUT_MID, ""),
    "T": (WALNUT_LIGHT, ""),
    "C": (CHROME, ""),
    "L": (BLAZE_RED, ""),
}

STITCH_DRAW_ORDER = ("S", "M", "R", "O", "Y", "W", "T", "B", "D", "L", "C", "K")

BURNING_CAR_GRID = (
    ".................................SSSS.",
    ".......................SSSS....SSMMMSS",
    ".....................SSMMMSSSSSSMMMMMS",
    "....................SSMMMMMSSMMMMMMMMM",
    "....................SMMRMMMMMMMMMMMMMS",
    "...................SMMRRMMMMMMMMMMMMSS",
    "..................SMRROROMMMMMMMMSSSS.",
    "................SSRROOYOROMMMMMMMSSS..",
    "............RR..SRROOYYOROMMMRMMSSS...",
    "...........RRO..RROYYWYOROMMRRMMSS....",
    "..........RROORRROYYWWYOROORROMMSS....",
    ".........RROYYOROOYWWYYORROYYORMS.....",
    "........RROOYYKWWWWKKWWKOYOYYRORM.....",
    ".......RROOYWWKYOYWKYOYWKYOYWRORM.....",
    "......RROOYYYYKYYYYKYYYYKYYYORRR......",
    "..TTTTTTTTTTYYYYTTTTTTTYYYYTTTTTTTD...",
    ".KCCKCCKBBBBBBBBBBBBBBBBBBBBBBBBBBBD..",
    "KCKKCKKBBBBKKKKBBBBBBBBBBBKKKKBBBBBL..",
    "CCCCCCCBDDKKCCKKDDDDDDDDDKKCCKKDDDDK..",
    ".KKKKKKBBDKKCCKKCCCCCCCCCKKCCKKDKKK...",
    "...KKK....KKKKKK..........KKKK........",
    "...........KKKK.......................",
)

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
        BLAZE_RED,
    ),
    (
        "mlaku-mulu",
        "NestJS & Prisma backend API for tourist and trip management.",
        "TypeScript",
        "NestJS",
        WALNUT,
    ),
    (
        "neetcode-gpt",
        "GPT built from scratch in PyTorch: attention, Transformers & RMSNorm.",
        "Python",
        "PyTorch",
        AMBER_REPO,
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
@keyframes flk1{0%,100%{opacity:1;transform:none}45%{opacity:.82;transform:translateY(-1.5px)}70%{opacity:.96;transform:translateY(-.6px)}}
@keyframes flk2{0%,100%{opacity:.95;transform:none}35%{opacity:.76;transform:translateY(-1.8px)}80%{opacity:1;transform:translateY(-.4px)}}
@keyframes smk1{0%,100%{opacity:.95;transform:none}50%{opacity:.80;transform:translate(2.2px,-2.8px)}}
@keyframes smk2{0%,100%{opacity:.92;transform:none}50%{opacity:.75;transform:translate(3.0px,-3.4px)}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
.live{animation:pulse 1.6s ease-in-out infinite}
.n{transform-box:fill-box;animation:nudge 1.8s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
.flk1{transform-box:fill-box;animation:flk1 1.6s ease-in-out infinite}
.flk2{transform-box:fill-box;animation:flk2 2.1s ease-in-out infinite}
.smk1{transform-box:fill-box;animation:smk1 3.8s ease-in-out infinite}
.smk2{transform-box:fill-box;animation:smk2 4.6s ease-in-out infinite}
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
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.rg,.flk1,.flk2,.smk1,.smk2{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}}
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
            ".flk1,.flk2,.smk1,.smk2{animation:none!important;opacity:1!important;transform:none!important}"
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


def cross_stitch_mark(
    x: float,
    y: float,
    size: float,
    color: str,
    stroke_width: float = 1.8,
    cls: str = "",
) -> str:
    """Draw a diagonal cross-stitch X mark using an SVG path."""
    cls_attr = f' class="{cls}"' if cls else ""
    d_attr = f"M{x:.1f} {y:.1f}l{size:.1f} {size:.1f}M{x + size:.1f} {y:.1f}l{-size:.1f} {size:.1f}"
    return (
        f'<path{cls_attr} d="{d_attr}" fill="none" stroke="{color}" '
        f'stroke-width="{stroke_width:.2f}" stroke-linecap="round"/>'
    )


def aida_pattern_def(
    pattern_id: str,
    weave_color: str = LINEN_WEAVE,
    pinhole_color: str = LINEN_PINHOLE,
    opacity_scale: float = 1.0,
) -> str:
    """Define an 8x8 woven Aida cloth pattern with subtle threads and pinholes."""
    weave_op = 0.28 * opacity_scale
    hole_op = 0.34 * opacity_scale
    return (
        f'<pattern id="{pattern_id}" width="8" height="8" patternUnits="userSpaceOnUse">'
        f'<line x1="0" y1="4" x2="8" y2="4" stroke="{weave_color}" stroke-opacity="{weave_op:.3f}" stroke-width="0.9"/>'
        f'<line x1="4" y1="0" x2="4" y2="8" stroke="{weave_color}" stroke-opacity="{weave_op:.3f}" stroke-width="0.9"/>'
        f'<rect x="0" y="0" width="1.1" height="1.1" fill="{pinhole_color}" fill-opacity="{hole_op:.3f}"/>'
        f"</pattern>"
    )


def card_surface(w: float, h: int, grad_id: str = "cardbg", extra_defs: str = "") -> str:
    """Return warm woven Aida linen gradient surface, weave pattern, and stitched frame."""
    return (
        f"<defs>"
        f'<linearGradient id="{grad_id}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{LINEN_TOP}"/>'
        f'<stop offset="1" stop-color="{LINEN_BOT}"/>'
        f"</linearGradient>"
        f'<clipPath id="{grad_id}-clip"><rect width="{w:.3f}" height="{h}" rx="14"/></clipPath>'
        f"{aida_pattern_def(f'{grad_id}-aida')}"
        f"{extra_defs}"
        f"</defs>"
        f'<g clip-path="url(#{grad_id}-clip)">'
        f'<rect width="{w:.3f}" height="{h}" fill="url(#{grad_id})"/>'
        f'<rect width="{w:.3f}" height="{h}" fill="url(#{grad_id}-aida)"/>'
        f"</g>"
        f'<rect x="0.5" y="0.5" width="{w - 1:.3f}" height="{h - 1}" rx="14" fill="none" '
        f'stroke="{LINEN_BORDER}" stroke-width="1"/>'
        f'<rect x="5.5" y="5.5" width="{w - 11:.3f}" height="{h - 11}" rx="10" fill="none" '
        f'stroke="{LINEN_STITCH}" stroke-opacity="0.48" stroke-width="1" stroke-dasharray="4 4"/>'
    )


def corner_stitches(w: float, h: int) -> str:
    """Draw 4 small cross-stitch clusters anchoring the hero card corners."""
    marks = []
    for cx, cy, dx, dy in (
        (16, 16, 10, 10),
        (w - 23, 16, -10, 10),
        (16, h - 23, 10, -10),
        (w - 23, h - 23, -10, -10),
    ):
        marks.append(cross_stitch_mark(cx, cy, 7, BLAZE_RED, stroke_width=1.8))
        marks.append(cross_stitch_mark(cx + dx, cy, 7, WALNUT_MID, stroke_width=1.6))
        marks.append(cross_stitch_mark(cx, cy + dy, 7, WALNUT_MID, stroke_width=1.6))
    return f'<g opacity="0.88">{"".join(marks)}</g>'


def render_burning_car(ox: float, oy: float, cell: float = 7.0) -> str:
    """Render the cross-stitch burning-car vignette batched by thread color and motion layer."""
    pad = cell * 0.16
    span = cell * 0.68
    stroke_w = cell * 0.32
    grouped: dict[str, list[str]] = {k: [] for k in STITCH_DRAW_ORDER}

    for r, row in enumerate(BURNING_CAR_GRID):
        y = oy + r * cell + pad
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            x = ox + c * cell
            grouped[ch].append(
                f"M{x + pad:.1f} {y:.1f}l{span:.1f} {span:.1f}"
                f"M{x + cell - pad:.1f} {y:.1f}l{-span:.1f} {span:.1f}"
            )

    paths = []
    for key in STITCH_DRAW_ORDER:
        segs = grouped[key]
        if not segs:
            continue
        color, cls = STITCH_PALETTE[key]
        cls_attr = f' class="{cls}"' if cls else ""
        paths.append(
            f'<path{cls_attr} d="{"".join(segs)}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke_w:.2f}" stroke-linecap="round"/>'
        )

    ground_y = oy + len(BURNING_CAR_GRID) * cell + 2
    ground = (
        f'<line x1="{ox + 3 * cell:.1f}" y1="{ground_y:.1f}" '
        f'x2="{ox + 34 * cell:.1f}" y2="{ground_y:.1f}" '
        f'stroke="{LINEN_STITCH}" stroke-opacity="0.45" stroke-width="1.5" stroke-dasharray="4 4"/>'
    )
    return f"<g>{ground}{''.join(paths)}</g>"


def render_hero(data: dict[str, Any], out_dir: str | Path, static: bool = False) -> Path:
    """Render Card 1: typography + cross-stitch burning-car hero card."""
    h = 330
    total = int(data["total_contributions"])

    shine_anim = (
        ""
        if static
        else '<animateTransform attributeName="gradientTransform" type="translate" '
        'values="-620 0;680 0;680 0" keyTimes="0;.45;1" dur="6.5s" begin="1.4s" repeatCount="indefinite"/>'
    )
    name_fill = SOOT_DARK if static else "url(#shine)"

    extra_defs = (
        f'<radialGradient id="heroglow" cx="78%" cy="42%" r="44%">'
        f'<stop offset="0" stop-color="{EMBER_ORANGE}" stop-opacity="0.11"/>'
        f'<stop offset="1" stop-color="{EMBER_ORANGE}" stop-opacity="0"/>'
        f"</radialGradient>"
        f'<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="620" y2="0">'
        f'<stop offset="0" stop-color="{SOOT_DARK}"/><stop offset=".40" stop-color="{SOOT_DARK}"/>'
        f'<stop offset=".48" stop-color="{BLAZE_RED}"/><stop offset=".52" stop-color="{EMBER_ORANGE}"/>'
        f'<stop offset=".60" stop-color="{SOOT_DARK}"/><stop offset="1" stop-color="{SOOT_DARK}"/>'
        f"{shine_anim}"
        f"</linearGradient>"
    )

    tagline = [
        "Autonomous robotics, ROS 2 bipedal kinematics & C++ deep learning",
        "at Universitas Gadjah Mada — 1st Place Global HVAC 2026 Japan.",
    ]

    body = f"""
{card_surface(W, h, "herobg", extra_defs)}
<g clip-path="url(#herobg-clip)">
  <rect width="{W}" height="{h}" fill="url(#heroglow)"/>
</g>
{corner_stitches(W, h)}
<g class="f" {d(0)}>
  {cross_stitch_mark(44, 37, 8, BLAZE_RED, stroke_width=2.0, cls="live")}
  <text x="62" y="45" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{INK_MUTED}">ROBOTICS SOFTWARE &amp; AI ENGINEER // UGM</text>
  <text x="{W - 44}" y="45" text-anchor="end" font-family="{MONO}" font-size="11.5" letter-spacing="0.8" fill="{INK_MUTED}">YOGYAKARTA, ID  &#183;  <tspan fill="{BLAZE_TEXT}">{total:,}</tspan> COMMITS / YR</text>
</g>
<text class="r" {d(0.15)} x="42" y="138" font-family="{DISP}" font-weight="800" font-size="78" letter-spacing="-2.2" fill="{SOOT_DARK}">Mahardika</text>
<text class="r" {d(0.30)} x="42" y="214" font-family="{DISP}" font-weight="800" font-size="78" letter-spacing="-2.2" fill="{name_fill}">Ramadhana</text>
<g class="f" {d(0.35)}>
  {render_burning_car(566, 68, 7.0)}
</g>
<g class="r" {d(0.50)}>
  {text_lines(44, 250, tagline, 24, f'font-family="{SANS}" font-weight="400" font-size="16.5" fill="{SMOKE_LIGHT}"')}
</g>
<g class="f" {d(0.72)}>
  <text x="44" y="306" font-family="{MONO}" font-size="12.5" fill="{SOOT_DARK}">mahardikaramadhana.vercel.app</text>
  <text class="nu" x="268" y="306" font-family="{MONO}" font-size="13" fill="{BLAZE_RED}">&#8599;</text>
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
    """Map daily contribution count to a 0..5 ember intensity bucket."""
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
    """Render Card 2: ember-thread daily contribution heatmap on Aida linen."""
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
            f'y="{gy + row * step}" width="{cell}" height="{cell}" rx="2" fill="{HEATMAP_RAMP[level_for(c)]}">'
            f'<title>{escape(day["date"])}: {c} contribution{suffix}</title></rect>'
        )

    legend_x = right - len(HEATMAP_RAMP) * 14 - 32
    labels = "".join(
        f'<text x="{gx + col * step:.1f}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{INK_MUTED}">{m}</text>'
        for col, m in months
        if gx + col * step < legend_x - 64
    )
    legend = "".join(
        f'<rect x="{legend_x + i * 14:.1f}" y="{gy + 7 * step + 6}" width="11" height="11" rx="2" fill="{col_hex}"/>'
        for i, col_hex in enumerate(HEATMAP_RAMP)
    )
    h = gy + 7 * step + 48
    total = int(data["total_contributions"])
    body = f"""
{card_surface(W, h, "heatbg")}
<text class="r" {d(0.80)} x="{gx:.1f}" y="54" font-family="{DISP}" font-weight="600" font-size="32" fill="{SOOT_DARK}">Every day, <tspan fill="{BLAZE_TEXT}">in ember</tspan></text>
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
        fill = BLAZE_RED if is_best else (BAR_PARTIAL if partial else BAR_MUTED)
        stroke_attr = (
            f' stroke="{BLAZE_TEXT}" stroke-opacity="0.55" stroke-width="1" stroke-dasharray="3 2"'
            if partial and not is_best
            else ""
        )
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
                f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{BLAZE_TEXT}">{m["total"]:,}</text>'
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
        (f'{cs} <tspan fill="{BLAZE_TEXT}">{day_word}</tspan>', streak_note),
        (f'{int(data["active_days"])}<tspan fill="{INK_MUTED}"> / {total_days}</tspan>', "days with a commit"),
        (f"{best_count}", best_note),
    ]

    side = []
    for i, (big, small) in enumerate(stats):
        y = 98 + i * 92
        side.append(
            f'<g class="r" {d(2.60 + i * 0.15)}>'
            f'<text x="644" y="{y}" font-family="{DISP}" font-weight="800" font-size="36" fill="{SOOT_DARK}">{big}</text>'
            f'<text x="644" y="{y + 24}" font-family="{SANS}" font-weight="400" font-size="13" fill="{INK_MUTED}">{escape(small)}</text>'
            f"</g>"
        )
        if i < 2:
            side.append(
                f'<line class="f" {d(2.60)} x1="644" y1="{y + 44}" x2="840" y2="{y + 44}" '
                f'stroke="{LINEN_STITCH}" stroke-opacity="0.65" stroke-width="1" stroke-dasharray="4 3"/>'
            )

    total = int(data["total_contributions"])
    body = f"""
{card_surface(W, h, "actbg")}
<text class="f" {d(1.90)} x="40" y="56" font-family="{MONO}" font-size="11.5" letter-spacing="1" fill="{INK_MUTED}">THE LAST 12 MONTHS ON GITHUB</text>
<text class="r" {d(2.00)} x="38" y="108" font-family="{DISP}" font-weight="800" font-size="46" fill="{SOOT_DARK}">{total:,} <tspan fill="{BLAZE_TEXT}">contributions</tspan></text>
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
    accent: str | None = None,
) -> Path:
    """Render Cards 4-6: one animated dyed-thread spotlight tile."""
    ring_color = accent or on
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
  {aida_pattern_def(f"weave-{name}", weave_color="#ffffff", pinhole_color="#000000", opacity_scale=0.35)}
  <linearGradient id="gl" x1="0" x2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".28"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
</defs>
<g class="ti" {d(delay)}>
  <g clip-path="url(#card)">
    <rect width="{TILE_W:.3f}" height="{TILE_H}" fill="{color}"/>
    <rect width="{TILE_W:.3f}" height="{TILE_H}" fill="url(#weave-{name})"/>
    <rect x="5.5" y="5.5" width="{TILE_W - 11:.3f}" height="{TILE_H - 11}" rx="10" fill="none" stroke="{ring_color}" stroke-opacity="0.32" stroke-width="1" stroke-dasharray="4 4"/>
    <circle class="rg" {d(delay + 0.50)} cx="{TILE_W - 40:.3f}" cy="{TILE_H - 40}" r="60" fill="none" stroke="{ring_color}" stroke-opacity=".45" stroke-width="2"/>
    <rect class="sh" style="animation-delay:{delay + 1.4:.2f}s" x="0" y="-20" width="90" height="{TILE_H + 40}" fill="url(#gl)" transform="translate(-260 0)"/>
  </g>
  <text class="sl" {d(delay + 0.35)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{on}">{escape(label)}</text>
  <g class="ai" {d(delay + 0.50)}>
    <text class="n" style="animation-delay:{delay + 1.3:.2f}s" x="249" y="38" font-family="{MONO}" font-size="14" fill="{ring_color}">&#8594;</text>
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
    fg = ON_DARK if theme == "dark" else SOOT_DARK
    accent_color = EMBER_ORANGE if theme == "dark" else BLAZE_TILE
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
  {cross_stitch_mark(22, 29, 8, color, stroke_width=2.0)}
  <text x="38" y="38" font-family="{SANS}" font-weight="600" font-size="15.5" fill="{SOOT_DARK}">{escape(name)}</text>
  <text class="nu" style="animation-delay:{delay + 0.8:.2f}s" x="252" y="38" font-family="{MONO}" font-size="13" fill="{color}">&#8599;</text>
  {text_lines(22, 74, lines, 20, f'font-family="{SANS}" font-weight="400" font-size="13.5" fill="{SMOKE_LIGHT}"')}
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
            BLAZE_TILE,
            ON_DARK,
            "3",
            "podiums",
            "HVAC 2026 Japan (1st Athletics, 3rd Sprint & Dance) & ROS 2 GMRT Fukuro.",
            3.10,
            0,
            static=static,
            accent=FLAME_CREAM,
        ),
        render_tile(
            out_dir,
            "ai",
            "AI & ML",
            SMOKE_MID,
            ON_DARK,
            "10K+",
            "runs",
            "UGM neural research, custom C++ engines, YOLOv11 edge-AI & RL systems.",
            3.35,
            1,
            static=static,
            accent=FLAME_GOLD,
        ),
        render_tile(
            out_dir,
            "honors",
            "HONORS",
            WALNUT,
            ON_DARK,
            "5",
            "titles",
            "HVAC 2026 Japan 1st, OSN Informatics & Math 1st, 2x UGM Chess Champ.",
            3.60,
            2,
            static=static,
            accent=FLAME_CREAM,
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

#!/usr/bin/env python3
"""
Download portfolio variable fonts and subset local JetBrains Mono into compact
static WOFF 1.0 files in fonts/ for embedding inside standalone SVG <img> cards.
"""
import io
import os
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FONTS_DIR = os.path.join(ROOT, "fonts")

CABINET_URL = "https://mahardikaramadhana.vercel.app/fonts/cabinet-grotesk-variable.woff2"
GENERAL_URL = "https://mahardikaramadhana.vercel.app/fonts/general-sans-variable.woff2"
JETBRAINS_PATH = "/home/dika/.local/share/fonts/JetBrainsMonoNF/JetBrainsMonoNLNerdFontMono-Regular.ttf"

UNICODE_SPEC = (
    "U+0020-007E,U+00A0,U+00B7,U+2013-2014,U+2018-2019,U+201C-201D,U+2192,U+2197,U+2605"
)


def fetch_font_bytes(url: str) -> bytes:
    """Download font bytes from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-font-builder/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def subset_to_woff(font: TTFont, out_path: str, weight_class: int) -> None:
    """Subset an in-memory TTFont to printable ASCII + symbols and save as WOFF 1.0."""
    if "OS/2" in font:
        font["OS/2"].usWeightClass = weight_class

    options = subset.Options()
    options.flavor = "woff"
    options.layout_features = ["kern", "liga", "calt"]
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6]
    options.desubroutinize = True

    unicodes = subset.parse_unicodes(UNICODE_SPEC)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    font.save(out_path)


def build_all_fonts() -> None:
    """Instantiate and subset all required static WOFF fonts."""
    cabinet_bytes = fetch_font_bytes(CABINET_URL)
    general_bytes = fetch_font_bytes(GENERAL_URL)

    jobs = [
        ("cabinet-800.woff", cabinet_bytes, 800),
        ("cabinet-600.woff", cabinet_bytes, 600),
        ("general-400.woff", general_bytes, 400),
        ("general-600.woff", general_bytes, 600),
    ]

    for filename, raw_bytes, weight in jobs:
        var_font = TTFont(io.BytesIO(raw_bytes))
        static_font = instantiateVariableFont(var_font, {"wght": float(weight)})
        out_path = os.path.join(FONTS_DIR, filename)
        subset_to_woff(static_font, out_path, weight)

    with open(JETBRAINS_PATH, "rb") as f:
        jb_font = TTFont(io.BytesIO(f.read()))
    subset_to_woff(jb_font, os.path.join(FONTS_DIR, "jetbrains-400.woff"), 400)


def verify_fonts() -> None:
    """Print size, weight class, and name metadata for each generated WOFF file."""
    for fn in sorted(os.listdir(FONTS_DIR)):
        if not fn.endswith(".woff"):
            continue
        path = os.path.join(FONTS_DIR, fn)
        size = os.path.getsize(path)
        font = TTFont(path)
        names = {r.nameID: r.toUnicode() for r in font["name"].names if r.nameID in (1, 2, 4, 6)}
        weight = font["OS/2"].usWeightClass if "OS/2" in font else None
        italic = bool(font["OS/2"].fsSelection & 1) if "OS/2" in font else None
        print(f"{fn}: {size} bytes, weight={weight}, italic={italic}, names={names}")


if __name__ == "__main__":
    build_all_fonts()
    verify_fonts()

#!/usr/bin/env python3
"""
Build Chart — Generate standards-compliant SVG charts from data and type.

The LLM picks *what* data to visualize and which chart type fits.
This script decides *how* to render it — consistent spacing, colors,
fonts, and accessibility.

Design language: "editorial data exhibit" (Green Energy Thailand brand).
  - Forest-green marks (#2d5016); amber (#c67b33) for the highlighted item and
    line/area endpoints; a 3-hue green/amber/slate set for true categories.
  - Magnitude charts use ONE hue, not a rainbow.
  - Each figure is a baked cream card (#f3f0e8 panel + hairline) so it reads as
    a magazine exhibit set apart from body text and travels atomically into WP/Astro.
  - Lora title, IBM Plex Sans data/labels, Source Serif italic source — the fonts
    already loaded on the frontend.
  - Ink is baked charcoal (not currentColor): the site is light-only, and a baked
    light panel needs a guaranteed-dark ink. (Tradeoff: no auto dark-theme flip.)

Usage:
    python scripts/build_chart.py --type horizontal-bar --title "Chart Title" --data '{"labels":["A","B"],"values":[1,2]}'
    python scripts/build_chart.py --type donut --title "Mix" --data data.json --source "IEA, 2025" --unit "%"

Output:
    <figure><svg>...</svg></figure> block (stdout or --output file)
"""

import argparse
import json
import math
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Design constants (enforced, not LLM-discretionary)
# ---------------------------------------------------------------------------

W = 560
GREEN = "#2d5016"       # forest — primary magnitude hue
GREEN_LT = "#3a6b1e"
AMBER = "#c67b33"       # highlight / accent / endpoint
SLATE = "#7a8a6f"       # third categorical hue (muted sage)
INK = "#2c2c2c"         # charcoal — baked text
MUTE = "#6b6b6b"        # muted text (source, axis)
PANEL = "#f3f0e8"       # baked card background (sits on cream #faf9f6)
TRACK = "#e6e1d6"       # faint bar track
LINE = "#d4d0c8"        # hairline border / grid tone

# Categorical set for true multi-category charts (identity, fixed order — never cycled past 3)
CAT = [GREEN, AMBER, SLATE, GREEN_LT]

SERIF = "'Lora', Georgia, serif"
SANS = "'IBM Plex Sans', system-ui, sans-serif"
SOURCE_F = "'Source Serif 4', Georgia, serif"


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _get_color(index: int, label: str = "", highlight: str = "") -> str:
    """Categorical hue by fixed order; the highlighted label always amber."""
    if highlight and label == highlight:
        return AMBER
    return CAT[index % len(CAT)]


def _frame(height: float, unit: str, title: str, source: str, body: str) -> str:
    """Wrap plotted body in the editorial card (panel + eyebrow + title + source)."""
    src = ""
    if source:
        src = (f'<text x="32" y="{height-20:.0f}" font-size="11" font-style="italic" '
               f'font-family="{SOURCE_F}" fill="{MUTE}">Source: {_esc(source)}</text>')
    eyebrow = ""
    if unit:
        eyebrow = (f'<rect x="32" y="26" width="7" height="7" rx="1.5" fill="{AMBER}"/>'
                   f'<text x="45" y="33" font-size="11" font-weight="600" letter-spacing="1.2" '
                   f'font-family="{SANS}" fill="{AMBER}">{_esc(unit.upper())}</text>')
    title_y = 56 if unit else 44
    # Shrink long titles so they don't overflow the 560-wide card at 19px.
    tsize = 19 if len(title) <= 44 else (16 if len(title) <= 56 else 14)
    return (
        f'<figure style="margin:1.5rem 0">\n'
        f'<svg viewBox="0 0 {W} {height:.0f}" style="max-width:100%;height:auto" '
        f'role="img" aria-label="{_esc(title)}">\n'
        f'<title>{_esc(title)}</title>\n'
        f'<rect x="1.5" y="1.5" width="{W-3}" height="{height-3:.0f}" rx="14" '
        f'fill="{PANEL}" stroke="{LINE}" stroke-width="1"/>\n'
        f'{eyebrow}\n'
        f'<text x="32" y="{title_y}" font-size="{tsize}" font-weight="700" '
        f'font-family="{SERIF}" fill="{INK}">{_esc(title)}</text>\n'
        f'{body}\n{src}\n</svg>\n</figure>'
    )


# ---------------------------------------------------------------------------
# Chart type implementations
# ---------------------------------------------------------------------------

def _horizontal_bar(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    values = data["values"]
    highlight = data.get("highlight", "")
    unit = kwargs.get("unit") or ""
    source = kwargs.get("source", "")
    n = len(labels)
    mx = max(values) if values else 1

    top = 78 if unit else 66
    row_h = 50
    bar_h = 20
    axis_x, end_x = 32, 512
    height = top + row_h * n + 44

    body = []
    for i, (lab, val) in enumerate(zip(labels, values)):
        ry = top + i * row_h
        w = (val / mx) * (end_x - axis_x) if mx else 0
        hi = bool(highlight) and lab == highlight
        c = AMBER if hi else GREEN
        body.append(f'<text x="{axis_x}" y="{ry+2:.0f}" font-size="12.5" font-family="{SANS}" '
                    f'fill="{INK}" opacity="0.85">{_esc(lab)}</text>')
        body.append(f'<rect x="{axis_x}" y="{ry+10:.0f}" width="{end_x-axis_x}" height="{bar_h}" rx="5" fill="{TRACK}"/>')
        body.append(f'<rect x="{axis_x}" y="{ry+10:.0f}" width="{w:.0f}" height="{bar_h}" rx="5" fill="{c}"/>')
        body.append(f'<text x="{axis_x+w+8:.0f}" y="{ry+24:.0f}" font-size="13" font-weight="600" '
                    f'font-family="{SANS}" fill="{AMBER if hi else INK}">{_fmt(val)}</text>')
    return _frame(height, unit, title, source, "\n".join(body))


def _lollipop(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    values = data["values"]
    highlight = data.get("highlight", "")
    unit = kwargs.get("unit") or ""
    source = kwargs.get("source", "")
    n = len(labels)
    mx = max(values) if values else 1

    top = 78 if unit else 66
    row_h = 50
    axis_x, end_x = 32, 500
    height = top + row_h * n + 44

    body = []
    for i, (lab, val) in enumerate(zip(labels, values)):
        ry = top + i * row_h
        cy = ry + 20
        w = (val / mx) * (end_x - axis_x) if mx else 0
        hi = bool(highlight) and lab == highlight
        c = AMBER if hi else GREEN
        body.append(f'<text x="{axis_x}" y="{ry+2:.0f}" font-size="12.5" font-family="{SANS}" '
                    f'fill="{INK}" opacity="0.85">{_esc(lab)}</text>')
        body.append(f'<line x1="{axis_x}" y1="{cy:.0f}" x2="{axis_x+w:.0f}" y2="{cy:.0f}" stroke="{c}" stroke-width="2.5"/>')
        body.append(f'<circle cx="{axis_x+w:.0f}" cy="{cy:.0f}" r="6.5" fill="{c}"/>')
        body.append(f'<text x="{axis_x+w+14:.0f}" y="{cy+4:.0f}" font-size="13" font-weight="600" '
                    f'font-family="{SANS}" fill="{AMBER if hi else INK}">{_fmt(val)}</text>')
    return _frame(height, unit, title, source, "\n".join(body))


def _donut(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    values = data["values"]
    center = data.get("center_text", "")
    unit = kwargs.get("unit") or ""
    source = kwargs.get("source", "")
    total = sum(values) if values else 1

    top = 78 if unit else 66
    cx, cy, oR, iR = 150, top + 90, 78, 48
    height = top + 200

    body = []
    ang = -90
    for i, (lab, val) in enumerate(zip(labels, values)):
        sweep = (val / total) * 360
        end = ang + sweep
        large = 1 if sweep > 180 else 0
        sxo = cx + oR * math.cos(math.radians(ang)); syo = cy + oR * math.sin(math.radians(ang))
        exo = cx + oR * math.cos(math.radians(end)); eyo = cy + oR * math.sin(math.radians(end))
        sxi = cx + iR * math.cos(math.radians(end)); syi = cy + iR * math.sin(math.radians(end))
        exi = cx + iR * math.cos(math.radians(ang)); eyi = cy + iR * math.sin(math.radians(ang))
        col = CAT[i % len(CAT)]
        body.append(f'<path d="M {sxo:.1f} {syo:.1f} A {oR} {oR} 0 {large} 1 {exo:.1f} {eyo:.1f} '
                    f'L {sxi:.1f} {syi:.1f} A {iR} {iR} 0 {large} 0 {exi:.1f} {eyi:.1f} Z" '
                    f'fill="{col}" stroke="{PANEL}" stroke-width="2"/>')
        ang = end
    if center:
        body.append(f'<text x="{cx}" y="{cy+7:.0f}" text-anchor="middle" font-size="24" '
                    f'font-weight="700" font-family="{SERIF}" fill="{INK}">{_esc(center)}</text>')
    lx, ly = 300, top + 40
    for i, (lab, val) in enumerate(zip(labels, values)):
        yy = ly + i * 26
        body.append(f'<rect x="{lx}" y="{yy-9:.0f}" width="11" height="11" rx="2.5" fill="{CAT[i%len(CAT)]}"/>')
        body.append(f'<text x="{lx+18}" y="{yy:.0f}" font-size="12.5" font-family="{SANS}" '
                    f'fill="{INK}" opacity="0.85">{_esc(lab)} · {_fmt(val)}</text>')
    return _frame(height, unit, title, source, "\n".join(body))


def _xy_plot(title, data, unit, source, filled):
    labels = data["labels"]
    values = data["values"]
    n = len(labels)
    mn, mx = min(values), max(values)
    rng = (mx - mn) or 1
    left, right = 52, 524
    top = 82 if unit else 70
    bot = top + 180
    cw, chh = right - left, bot - top
    height = bot + 58

    body = []
    for i in range(5):
        gy = top + (chh / 4) * i
        body.append(f'<line x1="{left}" y1="{gy:.0f}" x2="{right}" y2="{gy:.0f}" stroke="{INK}" opacity="0.07"/>')
        val = round(mx - (rng / 4) * i, 2)  # round to kill float noise on axis labels
        body.append(f'<text x="{left-8}" y="{gy+4:.0f}" text-anchor="end" font-size="10" '
                    f'font-family="{SANS}" fill="{MUTE}">{_fmt(val)}</text>')
    pts = [(left + (i / max(n-1, 1)) * cw, bot - ((v - mn) / rng) * chh) for i, v in enumerate(values)]
    if filled:
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" {pts[-1][0]:.1f},{bot} {pts[0][0]:.1f},{bot}"
        body.append(f'<polygon points="{poly}" fill="{GREEN}" opacity="0.13"/>')
    body.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)}" '
                f'fill="none" stroke="{GREEN}" stroke-width="2.5"/>')
    for i, (x, y) in enumerate(pts):
        last = i == len(pts) - 1
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{5 if last else 4}" fill="{AMBER if last else GREEN}"/>')
    ex, ey = pts[-1]
    body.append(f'<text x="{ex:.1f}" y="{ey-12:.0f}" text-anchor="end" font-size="13" font-weight="600" '
                f'font-family="{SANS}" fill="{AMBER}">{_fmt(values[-1])}</text>')
    for i, lab in enumerate(labels):
        x = left + (i / max(n-1, 1)) * cw
        body.append(f'<text x="{x:.1f}" y="{bot+20:.0f}" text-anchor="middle" font-size="11" '
                    f'font-family="{SANS}" fill="{INK}" opacity="0.75">{_esc(lab)}</text>')
    return _frame(height, unit, title, source, "\n".join(body))


def _line(title: str, data: dict, **kwargs) -> str:
    return _xy_plot(title, data, kwargs.get("unit") or "", kwargs.get("source", ""), filled=False)


def _area(title: str, data: dict, **kwargs) -> str:
    return _xy_plot(title, data, kwargs.get("unit") or "", kwargs.get("source", ""), filled=True)


def _grouped_bar(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    series = data.get("series", [])
    unit = kwargs.get("unit") or ""
    source = kwargs.get("source", "")
    n, ns = len(labels), len(series)

    top = 82 if unit else 70
    left, right = 44, 528
    plot_top, plot_bot = top, top + 180
    cw, ch = right - left, plot_bot - top
    gw = cw / n
    bw = (gw * 0.62) / max(ns, 1)
    gap = gw * 0.19
    allv = [v for s in series for v in s["values"]]
    mx = max(allv) if allv else 1
    height = plot_bot + 92

    body = []
    for i in range(5):
        gy = plot_top + (ch / 4) * i
        body.append(f'<line x1="{left}" y1="{gy:.0f}" x2="{right}" y2="{gy:.0f}" stroke="{INK}" opacity="0.07"/>')
        val = round(mx - (mx / 4) * i, 2)  # round to kill float noise on axis labels
        body.append(f'<text x="{left-8}" y="{gy+4:.0f}" text-anchor="end" font-size="10" '
                    f'font-family="{SANS}" fill="{MUTE}">{_fmt(val)}</text>')
    for gi, lab in enumerate(labels):
        gx = left + gi * gw + gap
        for si, s in enumerate(series):
            val = s["values"][gi]
            h = (val / mx) * ch if mx else 0
            x = gx + si * bw
            body.append(f'<rect x="{x:.1f}" y="{plot_bot-h:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                        f'rx="4" fill="{CAT[si%len(CAT)]}"/>')
        body.append(f'<text x="{left+gi*gw+gw/2:.1f}" y="{plot_bot+18:.0f}" text-anchor="middle" '
                    f'font-size="11" font-family="{SANS}" fill="{INK}" opacity="0.8">{_esc(lab)}</text>')
    lx = left
    for si, s in enumerate(series):
        body.append(f'<rect x="{lx}" y="{plot_bot+38:.0f}" width="11" height="11" rx="2.5" fill="{CAT[si%len(CAT)]}"/>')
        body.append(f'<text x="{lx+18}" y="{plot_bot+48:.0f}" font-size="11.5" font-family="{SANS}" '
                    f'fill="{INK}" opacity="0.85">{_esc(s["name"])}</text>')
        lx += 26 + len(str(s["name"])) * 7.5
    return _frame(height, unit, title, source, "\n".join(body))


def _fmt(v) -> str:
    """Render a number cleanly: drop the .0 on integers, keep real decimals."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


# ---------------------------------------------------------------------------
# Registry and main entry point
# ---------------------------------------------------------------------------

CHART_TYPES = {
    "horizontal-bar": _horizontal_bar,
    "lollipop": _lollipop,
    "donut": _donut,
    "line": _line,
    "grouped-bar": _grouped_bar,
    "area": _area,
}


def build_chart(
    chart_type: str,
    title: str,
    data: dict,
    subtitle: str | None = None,
    source: str = "",
    unit: str | None = None,
) -> str:
    """Build an SVG chart from type, title, and data.

    Args:
        chart_type: One of the CHART_TYPES keys
        title: Chart title displayed at top
        data: Dict with labels, values (and optional series, highlight, center_text, unit)
        subtitle: Legacy — used as the eyebrow unit label when `unit`/data["unit"] absent
        source: Source attribution text
        unit: Short unit/domain shown as the amber eyebrow (e.g. "MW", "US$ / MWh")

    Returns:
        Complete <figure><svg>...</svg></figure> HTML string
    """
    if chart_type not in CHART_TYPES:
        raise ValueError(f"Unknown chart type: {chart_type}. Must be one of: {', '.join(CHART_TYPES)}")

    labels = data.get("labels", [])
    values = data.get("values", [])
    series = data.get("series", [])

    if not labels:
        raise ValueError("Data must have non-empty 'labels'")
    if not values and not series:
        raise ValueError("Data must have non-empty 'values' or 'series'")

    eyebrow = unit or data.get("unit") or subtitle or ""
    figure = CHART_TYPES[chart_type](title, data, source=source, unit=eyebrow)
    # Emit as a single line: WordPress' wpautop turns newlines inside inline SVG
    # into injected <p>/</p> tags, which shatter the graphic on render. Old charts
    # survived precisely because they carried no newlines.
    return figure.replace("\n", "")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate SVG chart from data.")
    parser.add_argument("--type", required=True, choices=CHART_TYPES.keys(), help="Chart type")
    parser.add_argument("--title", required=True, help="Chart title")
    parser.add_argument("--subtitle", default=None, help="Legacy alias for --unit (eyebrow label)")
    parser.add_argument("--unit", default=None, help="Short unit/domain shown as the amber eyebrow")
    parser.add_argument("--source", default="", help="Source attribution")
    parser.add_argument("--data", required=True, help="JSON string or file path")
    parser.add_argument("--output", type=Path, default=None, help="Output file (default: stdout)")

    args = parser.parse_args()

    if Path(args.data).exists():
        data = json.loads(Path(args.data).read_text())
    else:
        data = json.loads(args.data)

    svg = build_chart(args.type, args.title, data, subtitle=args.subtitle, source=args.source, unit=args.unit)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg)
        print(f"Wrote: {args.output}")
    else:
        print(svg)


if __name__ == "__main__":
    main()

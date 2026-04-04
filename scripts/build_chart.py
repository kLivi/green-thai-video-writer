#!/usr/bin/env python3
"""
Build Chart — Generate standards-compliant SVG charts from data and type.

The LLM picks *what* data to visualize and which chart type fits.
This script decides *how* to render it — consistent spacing, colors,
fonts, dark-mode compliance, and accessibility.

Usage:
    python scripts/build_chart.py --type horizontal-bar --title "Chart Title" --data '{"labels":["A","B"],"values":[1,2]}'
    python scripts/build_chart.py --type donut --title "Mix" --data data.json --source "IEA, 2025"

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

VIEWBOX = "0 0 560 380"
FONT = "'Inter', system-ui, sans-serif"
COLORS = ["#f97316", "#38bdf8", "#a78bfa", "#22c55e", "#fb923c", "#818cf8", "#34d399"]
HIGHLIGHT_COLOR = "#f97316"  # orange — always used for highlighted item
GRID_STYLE = 'stroke="currentColor" opacity="0.08"'
SOURCE_STYLE = 'font-size="10" fill="currentColor" opacity="0.35"'
TEXT_FILL = 'fill="currentColor"'


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _svg_open(title: str, desc: str = "") -> str:
    aria = title
    desc_block = f"<desc>{desc}</desc>" if desc else ""
    return (
        f'<svg viewBox="{VIEWBOX}" '
        f"style=\"max-width: 100%; height: auto; font-family: {FONT}\" "
        f'role="img" aria-label="{_esc(aria)}">\n'
        f"<title>{_esc(title)}</title>\n"
        f"{desc_block}\n"
    )


def _svg_close() -> str:
    return "</svg>"


def _svg_title_block(title: str, subtitle: str | None = None) -> str:
    lines = f'<text x="280" y="28" text-anchor="middle" font-size="16" font-weight="700" {TEXT_FILL}>{_esc(title)}</text>\n'
    if subtitle:
        lines += f'<text x="280" y="48" text-anchor="middle" font-size="11" {TEXT_FILL} opacity="0.45">{_esc(subtitle)}</text>\n'
    return lines


def _svg_source(source: str) -> str:
    if not source:
        return ""
    return f'<text x="280" y="370" text-anchor="middle" {SOURCE_STYLE}>Source: {_esc(source)}</text>\n'


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _get_color(index: int, label: str = "", highlight: str = "") -> str:
    if highlight and label == highlight:
        return HIGHLIGHT_COLOR
    return COLORS[index % len(COLORS)]


# ---------------------------------------------------------------------------
# Chart type implementations
# ---------------------------------------------------------------------------

def _horizontal_bar(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    values = data["values"]
    highlight = data.get("highlight", "")
    subtitle = kwargs.get("subtitle")
    source = kwargs.get("source", "")
    n = len(labels)

    max_val = max(values) if values else 1
    chart_top = 60 if subtitle else 50
    bar_area_height = 300
    bar_height = min(24, bar_area_height // n - 8)
    spacing = bar_area_height / n
    bar_width_max = 350
    label_x = 140

    svg = _svg_open(title)
    svg += _svg_title_block(title, subtitle)

    for i, (label, val) in enumerate(zip(labels, values)):
        y = chart_top + i * spacing
        cy = y + bar_height / 2
        w = (val / max_val) * bar_width_max if max_val else 0
        color = _get_color(i, label, highlight)

        svg += f'<text x="{label_x - 5}" y="{cy + 4}" text-anchor="end" font-size="12" {TEXT_FILL} opacity="0.8">{_esc(label)}</text>\n'
        svg += f'<rect x="{label_x}" y="{y}" width="{w:.0f}" height="{bar_height}" rx="3" fill="{color}"/>\n'
        svg += f'<text x="{label_x + w + 6:.0f}" y="{cy + 4}" font-size="11" {TEXT_FILL} opacity="0.8">{val}</text>\n'

    svg += _svg_source(source)
    svg += _svg_close()
    return f"<figure>\n{svg}\n</figure>"


def _lollipop(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    values = data["values"]
    highlight = data.get("highlight", "")
    subtitle = kwargs.get("subtitle")
    source = kwargs.get("source", "")
    n = len(labels)

    max_val = max(values) if values else 1
    chart_top = 60 if subtitle else 50
    area_height = 300
    spacing = area_height / n
    line_max = 350
    label_x = 140

    svg = _svg_open(title)
    svg += _svg_title_block(title, subtitle)

    for i, (label, val) in enumerate(zip(labels, values)):
        cy = chart_top + i * spacing + spacing / 2
        w = (val / max_val) * line_max if max_val else 0
        color = _get_color(i, label, highlight)

        svg += f'<text x="{label_x - 5}" y="{cy + 4}" text-anchor="end" font-size="12" {TEXT_FILL} opacity="0.8">{_esc(label)}</text>\n'
        svg += f'<line x1="{label_x}" y1="{cy}" x2="{label_x + w:.0f}" y2="{cy}" stroke="{color}" stroke-width="2"/>\n'
        svg += f'<circle cx="{label_x + w:.0f}" cy="{cy}" r="5" fill="{color}"/>\n'
        svg += f'<text x="{label_x + w + 10:.0f}" y="{cy + 4}" font-size="11" {TEXT_FILL} opacity="0.8">{val}</text>\n'

    svg += _svg_source(source)
    svg += _svg_close()
    return f"<figure>\n{svg}\n</figure>"


def _donut(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    values = data["values"]
    center_text = data.get("center_text", "")
    subtitle = kwargs.get("subtitle")
    source = kwargs.get("source", "")

    total = sum(values) if values else 1
    cx, cy = 200, 200
    outer_r = 100
    inner_r = 60

    svg = _svg_open(title)
    svg += _svg_title_block(title, subtitle)

    # Draw arcs
    start_angle = -90  # Start from top
    for i, (label, val) in enumerate(zip(labels, values)):
        fraction = val / total
        sweep_angle = fraction * 360
        color = _get_color(i)

        # Calculate arc path
        end_angle = start_angle + sweep_angle
        large_arc = 1 if sweep_angle > 180 else 0

        sx_outer = cx + outer_r * math.cos(math.radians(start_angle))
        sy_outer = cy + outer_r * math.sin(math.radians(start_angle))
        ex_outer = cx + outer_r * math.cos(math.radians(end_angle))
        ey_outer = cy + outer_r * math.sin(math.radians(end_angle))
        sx_inner = cx + inner_r * math.cos(math.radians(end_angle))
        sy_inner = cy + inner_r * math.sin(math.radians(end_angle))
        ex_inner = cx + inner_r * math.cos(math.radians(start_angle))
        ey_inner = cy + inner_r * math.sin(math.radians(start_angle))

        path = (
            f"M {sx_outer:.1f} {sy_outer:.1f} "
            f"A {outer_r} {outer_r} 0 {large_arc} 1 {ex_outer:.1f} {ey_outer:.1f} "
            f"L {sx_inner:.1f} {sy_inner:.1f} "
            f"A {inner_r} {inner_r} 0 {large_arc} 0 {ex_inner:.1f} {ey_inner:.1f} Z"
        )
        svg += f'<path d="{path}" fill="{color}"/>\n'
        start_angle = end_angle

    # Center text
    if center_text:
        svg += f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" font-size="22" font-weight="700" {TEXT_FILL}>{_esc(center_text)}</text>\n'

    # Legend (right side)
    legend_x = 340
    legend_y = 130
    for i, (label, val) in enumerate(zip(labels, values)):
        color = _get_color(i)
        ly = legend_y + i * 22
        svg += f'<rect x="{legend_x}" y="{ly - 8}" width="10" height="10" rx="2" fill="{color}"/>\n'
        svg += f'<text x="{legend_x + 16}" y="{ly}" font-size="11" {TEXT_FILL} opacity="0.8">{_esc(label)} ({val})</text>\n'

    svg += _svg_source(source)
    svg += _svg_close()
    return f"<figure>\n{svg}\n</figure>"


def _line(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    values = data["values"]
    subtitle = kwargs.get("subtitle")
    source = kwargs.get("source", "")
    n = len(labels)

    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val if max_val != min_val else 1

    chart_left = 60
    chart_right = 520
    chart_top = 70
    chart_bottom = 320
    chart_w = chart_right - chart_left
    chart_h = chart_bottom - chart_top

    svg = _svg_open(title)
    svg += _svg_title_block(title, subtitle)

    # Grid lines
    for i in range(5):
        gy = chart_top + (chart_h / 4) * i
        svg += f'<line x1="{chart_left}" y1="{gy:.0f}" x2="{chart_right}" y2="{gy:.0f}" {GRID_STYLE}/>\n'

    # Points and line
    points = []
    for i, (label, val) in enumerate(zip(labels, values)):
        x = chart_left + (i / max(n - 1, 1)) * chart_w
        y = chart_bottom - ((val - min_val) / val_range) * chart_h
        points.append((x, y))

    # Polyline
    points_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    svg += f'<polyline points="{points_str}" fill="none" stroke="{HIGHLIGHT_COLOR}" stroke-width="2.5"/>\n'

    # Circles on points
    for x, y in points:
        svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{HIGHLIGHT_COLOR}"/>\n'

    # X-axis labels
    for i, label in enumerate(labels):
        x = chart_left + (i / max(n - 1, 1)) * chart_w
        svg += f'<text x="{x:.1f}" y="{chart_bottom + 20}" text-anchor="middle" font-size="11" {TEXT_FILL} opacity="0.7">{_esc(label)}</text>\n'

    # Y-axis labels
    for i in range(5):
        gy = chart_top + (chart_h / 4) * i
        val = max_val - (val_range / 4) * i
        svg += f'<text x="{chart_left - 8}" y="{gy + 4:.0f}" text-anchor="end" font-size="10" {TEXT_FILL} opacity="0.6">{val:.0f}</text>\n'

    svg += _svg_source(source)
    svg += _svg_close()
    return f"<figure>\n{svg}\n</figure>"


def _grouped_bar(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    series_list = data.get("series", [])
    subtitle = kwargs.get("subtitle")
    source = kwargs.get("source", "")
    n = len(labels)
    n_series = len(series_list)

    all_vals = [v for s in series_list for v in s["values"]]
    max_val = max(all_vals) if all_vals else 1

    chart_left = 60
    chart_right = 520
    chart_top = 70
    chart_bottom = 310
    chart_w = chart_right - chart_left
    chart_h = chart_bottom - chart_top
    group_width = chart_w / n
    bar_width = (group_width * 0.7) / max(n_series, 1)
    gap = group_width * 0.15

    svg = _svg_open(title)
    svg += _svg_title_block(title, subtitle)

    # Grid lines
    for i in range(5):
        gy = chart_top + (chart_h / 4) * i
        svg += f'<line x1="{chart_left}" y1="{gy:.0f}" x2="{chart_right}" y2="{gy:.0f}" {GRID_STYLE}/>\n'

    # Bars
    for gi, label in enumerate(labels):
        group_x = chart_left + gi * group_width + gap
        for si, series in enumerate(series_list):
            val = series["values"][gi]
            h = (val / max_val) * chart_h if max_val else 0
            x = group_x + si * bar_width
            y = chart_bottom - h
            color = COLORS[si % len(COLORS)]
            svg += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{h:.1f}" rx="2" fill="{color}"/>\n'

        # X-axis label
        lx = chart_left + gi * group_width + group_width / 2
        svg += f'<text x="{lx:.1f}" y="{chart_bottom + 18}" text-anchor="middle" font-size="11" {TEXT_FILL} opacity="0.7">{_esc(label)}</text>\n'

    # Y-axis labels
    for i in range(5):
        gy = chart_top + (chart_h / 4) * i
        val = max_val - (max_val / 4) * i
        svg += f'<text x="{chart_left - 8}" y="{gy + 4:.0f}" text-anchor="end" font-size="10" {TEXT_FILL} opacity="0.6">{val:.0f}</text>\n'

    # Legend
    legend_y = chart_bottom + 40
    legend_x = chart_left
    for si, series in enumerate(series_list):
        color = COLORS[si % len(COLORS)]
        lx = legend_x + si * 100
        svg += f'<rect x="{lx}" y="{legend_y - 8}" width="10" height="10" rx="2" fill="{color}"/>\n'
        svg += f'<text x="{lx + 16}" y="{legend_y}" font-size="11" {TEXT_FILL} opacity="0.8">{_esc(series["name"])}</text>\n'

    svg += _svg_source(source)
    svg += _svg_close()
    return f"<figure>\n{svg}\n</figure>"


def _area(title: str, data: dict, **kwargs) -> str:
    labels = data["labels"]
    values = data["values"]
    subtitle = kwargs.get("subtitle")
    source = kwargs.get("source", "")
    n = len(labels)

    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val if max_val != min_val else 1

    chart_left = 60
    chart_right = 520
    chart_top = 70
    chart_bottom = 320
    chart_w = chart_right - chart_left
    chart_h = chart_bottom - chart_top

    svg = _svg_open(title)
    svg += _svg_title_block(title, subtitle)

    # Grid lines
    for i in range(5):
        gy = chart_top + (chart_h / 4) * i
        svg += f'<line x1="{chart_left}" y1="{gy:.0f}" x2="{chart_right}" y2="{gy:.0f}" {GRID_STYLE}/>\n'

    # Points
    points = []
    for i, (label, val) in enumerate(zip(labels, values)):
        x = chart_left + (i / max(n - 1, 1)) * chart_w
        y = chart_bottom - ((val - min_val) / val_range) * chart_h
        points.append((x, y))

    # Filled area polygon
    polygon_points = [f"{x:.1f},{y:.1f}" for x, y in points]
    polygon_points.append(f"{points[-1][0]:.1f},{chart_bottom}")
    polygon_points.append(f"{points[0][0]:.1f},{chart_bottom}")
    svg += f'<polygon points="{" ".join(polygon_points)}" fill="{HIGHLIGHT_COLOR}" opacity="0.15"/>\n'

    # Line
    line_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    svg += f'<polyline points="{line_str}" fill="none" stroke="{HIGHLIGHT_COLOR}" stroke-width="2.5"/>\n'

    # Circle points
    for x, y in points:
        svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{HIGHLIGHT_COLOR}"/>\n'

    # X-axis labels
    for i, label in enumerate(labels):
        x = chart_left + (i / max(n - 1, 1)) * chart_w
        svg += f'<text x="{x:.1f}" y="{chart_bottom + 20}" text-anchor="middle" font-size="11" {TEXT_FILL} opacity="0.7">{_esc(label)}</text>\n'

    # Y-axis labels
    for i in range(5):
        gy = chart_top + (chart_h / 4) * i
        val = max_val - (val_range / 4) * i
        svg += f'<text x="{chart_left - 8}" y="{gy + 4:.0f}" text-anchor="end" font-size="10" {TEXT_FILL} opacity="0.6">{val:.2f}</text>\n'

    svg += _svg_source(source)
    svg += _svg_close()
    return f"<figure>\n{svg}\n</figure>"


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
) -> str:
    """Build an SVG chart from type, title, and data.

    Args:
        chart_type: One of the CHART_TYPES keys
        title: Chart title displayed at top
        data: Dict with labels, values (and optional series, highlight, center_text)
        subtitle: Optional subtitle below title
        source: Source attribution text

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

    return CHART_TYPES[chart_type](title, data, subtitle=subtitle, source=source)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate SVG chart from data.")
    parser.add_argument("--type", required=True, choices=CHART_TYPES.keys(), help="Chart type")
    parser.add_argument("--title", required=True, help="Chart title")
    parser.add_argument("--subtitle", default=None, help="Optional subtitle")
    parser.add_argument("--source", default="", help="Source attribution")
    parser.add_argument("--data", required=True, help="JSON string or file path")
    parser.add_argument("--output", type=Path, default=None, help="Output file (default: stdout)")

    args = parser.parse_args()

    # Parse data
    if Path(args.data).exists():
        data = json.loads(Path(args.data).read_text())
    else:
        data = json.loads(args.data)

    svg = build_chart(args.type, args.title, data, subtitle=args.subtitle, source=args.source)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg)
        print(f"Wrote: {args.output}")
    else:
        print(svg)


if __name__ == "__main__":
    main()

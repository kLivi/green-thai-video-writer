# Green Thai Video Writer — scripts/render_charts.py

> Source: /home/unify/Documents/green-energy-thailand/green-thai-video-writer/scripts/render_charts.py
> Collected: 2026-09-01
> Published: 2026-07-25

```python
#!/usr/bin/env python3
"""Render [CHART: {...}] markers into inline SVG — deterministically, in code.

The writing agent's only job is to emit the marker. It must never run
build_chart.py itself, never capture its stdout, and never hand-edit SVG into
the article. Every time that transcription step was left to the LLM it
eventually corrupted a chart:

  2026-06-30  a naive `\\[CHART:.*?\\]` regex stopped at the first ']' inside
              "labels":[...] and left a truncated JSON fragment in the post.
  2026-07-25  post 1590 shipped `...Fuel Type</title>` where build_chart.py
              emits `</text>`. One token. The </title> never closed the <text>,
              so the HTML parser swallowed the rest of the graphic and the
              chart rendered as an empty card.

Both are transcription failures, not chart-logic failures. This script removes
the transcription step: markers in, SVG out, no model in the loop.

Marker extraction uses json.JSONDecoder().raw_decode(), which consumes exactly
one JSON value and reports where it ended. That is what makes the 2026-06-30
bug structurally impossible — there is no regex to truncate.

Fails loudly (exit 1) on any malformed marker. A broken chart must stop the
publish, not ship as an empty box.

Usage:
    python3 scripts/render_charts.py output/article.html     # rewrite in place
    python3 scripts/render_charts.py output/article.html --check   # report only
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_chart import build_chart  # noqa: E402
from chart_inspect import inspect_svg, find_svgs  # noqa: E402

MARKER = "[CHART:"


class ChartMarkerError(RuntimeError):
    """A [CHART: ...] marker could not be parsed or built."""


def _iter_markers(html: str):
    """Yield (start, end, spec) for each marker. `end` is one past the ']'."""
    decoder = json.JSONDecoder()
    pos = 0
    while True:
        start = html.find(MARKER, pos)
        if start == -1:
            return
        brace = html.find("{", start)
        if brace == -1:
            raise ChartMarkerError(f"marker at offset {start}: no JSON object follows '{MARKER}'")
        try:
            spec, after = decoder.raw_decode(html, brace)
        except json.JSONDecodeError as exc:
            raise ChartMarkerError(f"marker at offset {start}: invalid JSON — {exc}") from exc
        close = after
        while close < len(html) and html[close].isspace():
            close += 1
        if close >= len(html) or html[close] != "]":
            raise ChartMarkerError(
                f"marker at offset {start}: expected ']' after the JSON, found "
                f"{html[close:close+12]!r}"
            )
        yield start, close + 1, spec
        pos = close + 1


def render_markers(html: str) -> tuple[str, int]:
    """Replace every [CHART: {...}] marker with its built <figure><svg>.

    Returns (rendered_html, marker_count). Idempotent: HTML with no markers
    comes back unchanged with a count of 0.
    """
    parts: list[str] = []
    last = 0
    count = 0

    for start, end, spec in _iter_markers(html):
        if not isinstance(spec, dict):
            raise ChartMarkerError(f"marker at offset {start}: JSON is not an object")
        missing = [k for k in ("type", "title", "data") if k not in spec]
        if missing:
            raise ChartMarkerError(f"marker at offset {start}: missing field(s) {missing}")
        try:
            svg = build_chart(
                spec["type"],
                spec["title"],
                spec["data"],
                subtitle=spec.get("subtitle"),
                source=spec.get("source", ""),
                unit=spec.get("unit"),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise ChartMarkerError(
                f"marker at offset {start} ({spec.get('title', '?')!r}): {exc}"
            ) from exc

        # Look at what we just drew. A chart that renders wrong is as bad as one
        # that fails to build, and this is the last point where stopping is cheap.
        # build_chart returns <figure><svg>…; inspect the <svg> inside it.
        inner = find_svgs(svg)
        flaws = inspect_svg(inner[0]) if inner else ["no <svg> in built figure"]
        if flaws:
            raise ChartMarkerError(f"{spec.get('title', '?')!r}: {'; '.join(flaws)}")

        parts.append(html[last:start])
        parts.append(svg)
        last = end
        count += 1

    parts.append(html[last:])
    rendered = "".join(parts)

    # Nothing that looks like a marker may survive — a leftover means the scan
    # missed a form we don't handle, and the post would ship raw JSON.
    if "[CHART" in rendered:
        stray = rendered[rendered.find("[CHART"):][:80]
        raise ChartMarkerError(f"a chart marker survived substitution: {stray!r}")

    return rendered, count


def main() -> int:
    ap = argparse.ArgumentParser(description="Render [CHART: ...] markers into inline SVG.")
    ap.add_argument("html", type=Path, help="Article HTML file")
    ap.add_argument("--check", action="store_true", help="Validate markers without writing")
    args = ap.parse_args()

    if not args.html.exists():
        print(f"FATAL: {args.html} not found", file=sys.stderr)
        return 2

    source = args.html.read_text(encoding="utf-8")
    try:
        rendered, count = render_markers(source)
    except ChartMarkerError as exc:
        print(f"CHART RENDER FAILED — {exc}", file=sys.stderr)
        return 1

    if count == 0:
        print(f"No [CHART: ...] markers in {args.html.name} — nothing to render.")
        return 0

    if args.check:
        print(f"{count} chart marker(s) in {args.html.name} parse and build cleanly.")
        return 0

    args.html.write_text(rendered, encoding="utf-8")
    print(f"Rendered {count} chart(s) into {args.html.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

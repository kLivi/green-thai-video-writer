# Green Thai Video Writer — shared citation_gate.py

> Source: /home/unify/Documents/green-energy-thailand/shared/citation_gate.py
> Collected: 2026-09-01
> Published: 2026-08-09

```python
"""Pre-upload citation gate runner, shared by all three GET pipelines.

Every pipeline's wordpress_upload.py calls run_citation_gate() at the same place:
before any WordPress API call, never behind a flag. The gate itself
(verify_citations.py) lives beside this file, so a fix to either lands in
claude-blog, green-thai-idea-writer, and green-thai-video-writer at once.

History: this block used to exist only in claude-blog's wordpress_upload.py.
The other two pipelines each carry their own copy of that script and never got
it, so their headless runs published unverified citations — that is how post
1786 shipped a claim its cited source did not make (2026-08-09).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

_SHARED_DIR = Path(__file__).resolve().parent
_GET_ROOT = _SHARED_DIR.parent

# Canonical Thai facts file. It lives under claude-blog/shared/ (referenced by
# path in three CLAUDE.md files) while the Python lives here — deliberate, so
# that moving the code did not invalidate that documented path.
THAI_FACTS = _GET_ROOT / "claude-blog" / "shared" / "thai-facts.md"

# Exit code for a citation hard-fail. Distinct from the generic exit 1 so a
# runner can treat it as do-not-retry and must NOT consume the queue item.
CITATION_FAIL_EXIT = 3


def run_citation_gate(
    html_file: Path,
    *,
    require_sources: bool,
    notify: Callable[[str, str, str], None] | None = None,
    log_blocks: Callable[[str, str], None] | None = None,
) -> None:
    """Verify every citation in sources.json before the caller touches WordPress.

    Reads sources.json next to html_file (where build_article.py writes it).
    Exits the process with CITATION_FAIL_EXIT on failure; returns None on pass.

    require_sources=True makes a missing sources.json a hard failure. An article
    with no citations must emit {"sources": []} rather than omitting the file —
    otherwise "nothing to cite" and "the writer forgot" are indistinguishable,
    which is precisely how an unverified article reaches WordPress.

    notify(stage, message, detail) surfaces failures on the pipeline's own
    channel (Discord); log_blocks(stdout, filename) records per-citation
    residuals. Both optional so a bare CLI caller works without them.
    """
    sources_path = Path(html_file).parent / "sources.json"

    if not sources_path.exists():
        if not require_sources:
            print(f"[citation-gate] no {sources_path.name} next to "
                  f"{Path(html_file).name} — skipping (gate not yet mandatory here).")
            return
        print(f"[citation-gate] BLOCKED — no {sources_path.name} next to "
              f"{Path(html_file).name}. An article with no citations must emit "
              f'{{"sources": []}}. No draft created.')
        if notify:
            notify(
                "citation gate",
                "sources.json missing — cannot verify citations",
                str(sources_path),
            )
        sys.exit(CITATION_FAIL_EXIT)

    cmd = [sys.executable, str(_SHARED_DIR / "verify_citations.py"), str(sources_path)]
    if THAI_FACTS.exists():
        cmd += ["--thai-facts", str(THAI_FACTS)]

    print(f"\n[citation-gate] Verifying citations in {sources_path.name} before upload...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    if result.returncode != 0:
        print("[citation-gate] BLOCKED — a cited source does not carry its number. "
              "No draft created.")
        if log_blocks:
            log_blocks(result.stdout, Path(html_file).name)
        if notify:
            notify(
                "citation gate",
                "Pre-upload citation verification failed (NUMBER_NOT_FOUND)",
                str(sources_path),
            )
        sys.exit(CITATION_FAIL_EXIT)

    print("[citation-gate] passed.")
```

"""Research-time citation gate: run the citation verifier while the researcher
is still in-loop, so a failed citation self-corrects (re-source or drop)
instead of blocking at publish.

This module is the deterministic core only — the LLM re-sourcing loop that
reacts to CHECK mode's RESOURCE_NEEDED output lives elsewhere. Reuses
verify_citations.py's fetch/classify layer rather than reimplementing it.

CLI contract:
    python3 scripts/research_gate.py <sources.json> [--floor N] [--thai-facts PATH]
    python3 scripts/research_gate.py <sources.json> --finalize [--floor N] [--thai-facts PATH]

Default --floor = 4.

CHECK mode (default): classify every citation. If any hard-fail
(NUMBER_NOT_FOUND) exists, print one "RESOURCE_NEEDED: ..." line per failing
citation plus a summary line, exit 10. Otherwise print a PASS line, exit 0.
Warnings (DEAD_LINK / UNVERIFIABLE_TRUSTED / THAI_FACTS_OK / PASS) never
count as hard-fails.

FINALIZE mode: classify every citation and make the deterministic
drop-or-hold call.
    - zero hard-fails -> nothing to drop, exit 0, file untouched.
    - hard-fails exist and remaining_valid >= floor -> DROP the failing
      cids, rewrite sources.json atomically (temp file + os.replace), exit 0.
    - hard-fails exist and remaining_valid < floor -> HOLD, do not modify
      sources.json, exit 20.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Citation modules are shared by all three GET pipelines — see ../../shared/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from citations import Citation, load_sources
from verify_citations import (classify, classify_thai_fact, resolve_internal_source,
                              resolve_quote, _fetch)

HARD_FAIL_VERDICT = "NUMBER_NOT_FOUND"

EXIT_PASS = 0
EXIT_RESOURCE_NEEDED = 10
EXIT_HOLD = 20


def classify_sources(
    sources: dict[str, Citation], thai_facts_text: str | None
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Classify every citation, reusing verify_citations' fetch/classify layer.

    Returns (verdicts, corrections): cid -> verdict for every citation, plus
    cid -> {field: value} for every field this gate resolves deterministically
    rather than trusting the agent to have authored:

      internal-verified   source_name + url, from thai-facts.md's allowlist
      web                 quote, sliced from the page we just fetched

    Both exist for the same reason: a field the agent fills from memory drifts.
    An invented source_name put an internal filename into five published
    articles; a retyped quote put "buildings accounting for" against a page
    reading "buildings account for". An internal-verified citation that clears
    classify_thai_fact but has no structured row to resolve against is turned
    into a hard fail — the agent's own source_name is never a fallback.
    """
    verdicts: dict[str, str] = {}
    corrections: dict[str, dict[str, str]] = {}
    for cid, c in sources.items():
        if c.source_type == "internal-verified":
            verdict = classify_thai_fact(c, thai_facts_text)
            if verdict == "THAI_FACTS_OK":
                resolved = (
                    None if thai_facts_text is None
                    else resolve_internal_source(c.value, thai_facts_text)
                )
                if resolved is None:
                    verdict = HARD_FAIL_VERDICT
                else:
                    corrections[cid] = {"source_name": resolved[0], "url": resolved[1]}
            verdicts[cid] = verdict
        else:
            text, code, unreadable = _fetch(c.url)
            verdicts[cid] = classify(c, text, code, unreadable)
            # Slice the quote out of the bytes we just fetched. Unresolvable
            # (paywall, dead link, or a value split across markup) leaves the
            # agent's text alone: the number check decides whether the citation
            # survives, and replacing evidence with a guess would be worse than
            # keeping an imperfect record.
            if text.strip():
                sliced = resolve_quote(c.value, text)
                if sliced is not None and sliced != c.quote:
                    corrections[cid] = {"quote": sliced}
    return verdicts, corrections


def _load_thai_facts_text(thai_facts_path: Path | None) -> str | None:
    if thai_facts_path is None:
        return None
    return Path(thai_facts_path).read_text(encoding="utf-8")


def _write_json_atomic(path: Path, data: dict) -> None:
    """Write `data` as JSON to `path` atomically: write to a temp file in the
    same directory, then os.replace() onto the target. Never truncates the
    target file in place."""
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.remove(tmp_name)
        except OSError:
            pass
        raise


def _run_check(sources: dict[str, Citation], verdicts: dict[str, str]) -> int:
    failing = [cid for cid, v in verdicts.items() if v == HARD_FAIL_VERDICT]
    if not failing:
        print(f"RESEARCH GATE PASSED: {len(sources)} citation(s), 0 need re-sourcing.")
        return EXIT_PASS

    for cid in failing:
        c = sources[cid]
        print(f"RESOURCE_NEEDED: {cid} | {c.value} | {c.source_name} | {c.url}")

    print(f"\nRESEARCH GATE: {len(failing)} citation(s) need re-sourcing.")
    return EXIT_RESOURCE_NEEDED


def _run_finalize(
    sources_path: Path,
    sources: dict[str, Citation],
    verdicts: dict[str, str],
    floor: int,
    corrections: dict[str, tuple[str, str]] | None = None,
) -> int:
    corrections = corrections or {}
    failing = [cid for cid, v in verdicts.items() if v == HARD_FAIL_VERDICT]
    if not failing and not corrections:
        print("FINALIZE: 0 hard-fails, nothing to drop.")
        return EXIT_PASS

    remaining_valid = len(sources) - len(failing)

    if failing and remaining_valid < floor:
        print(
            f"HOLD: dropping {len(failing)} failing citation(s) would leave "
            f"{remaining_valid} valid (< floor {floor})"
        )
        return EXIT_HOLD

    raw = json.loads(Path(sources_path).read_text(encoding="utf-8"))
    failing_set = set(failing)
    kept = []
    for rec in raw.get("sources", []):
        if rec.get("id") in failing_set:
            continue
        resolved = corrections.get(rec.get("id"))
        if resolved is not None:
            rec.update(resolved)
        kept.append(rec)
    raw["sources"] = kept
    _write_json_atomic(Path(sources_path), raw)

    if failing:
        print(f"DROPPED {len(failing)} failing citation(s): {', '.join(failing)}")
    if corrections:
        names = [cid for cid, f in corrections.items() if "source_name" in f]
        quotes = [cid for cid, f in corrections.items() if "quote" in f]
        if names:
            print(f"RESOLVED {len(names)} internal-verified source(s): {', '.join(names)}")
        if quotes:
            print(f"RESOLVED {len(quotes)} quote(s) from the fetched page: {', '.join(quotes)}")
    print(f"FINALIZE: {remaining_valid} citation(s) remain (>= floor {floor}). sources.json rewritten.")
    return EXIT_PASS


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", type=Path)
    ap.add_argument("--floor", type=int, default=4)
    ap.add_argument("--thai-facts", type=Path, default=None)
    ap.add_argument("--finalize", action="store_true")
    args = ap.parse_args(argv)

    sources = load_sources(args.sources)
    thai_facts_text = _load_thai_facts_text(args.thai_facts)
    verdicts, corrections = classify_sources(sources, thai_facts_text)

    if args.finalize:
        return _run_finalize(args.sources, sources, verdicts, args.floor, corrections)
    return _run_check(sources, verdicts)


if __name__ == "__main__":
    sys.exit(main())

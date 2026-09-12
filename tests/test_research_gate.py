"""Tests for scripts/research_gate.py — the research-time citation gate.

Offline/deterministic: monkeypatches the classify/fetch layer imported from
the shared verify_citations module so no real network calls happen.
"""
from __future__ import annotations
import json

import pytest

from scripts import research_gate


def _src(id, value="5,345 MW", claim="c", source_name="Mordor",
         url="https://m.com/a", quote="q", tier=2, source_type="web"):
    return {
        "id": id, "value": value, "claim": claim, "source_name": source_name,
        "url": url, "quote": quote, "tier": tier, "source_type": source_type,
    }


def _write_sources(tmp_path, records, extra_top_level=None):
    path = tmp_path / "sources.json"
    data = {"sources": records}
    if extra_top_level:
        data.update(extra_top_level)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _patch_verdicts(monkeypatch, verdict_map, default="PASS"):
    """Stub classify/classify_thai_fact/_fetch so verdicts are controlled purely
    by citation id, with no network access."""

    def fake_fetch(url):
        return "", 200, False

    def fake_classify(c, fetched_text, status_code, media_unreadable=False):
        return verdict_map.get(c.id, default)

    def fake_classify_thai_fact(c, thai_facts_text):
        return verdict_map.get(c.id, default)

    monkeypatch.setattr(research_gate, "_fetch", fake_fetch)
    monkeypatch.setattr(research_gate, "classify", fake_classify)
    monkeypatch.setattr(research_gate, "classify_thai_fact", fake_classify_thai_fact)


# --- CHECK mode ---

def test_check_all_pass_exits_0(tmp_path, monkeypatch, capsys):
    records = [_src("S1"), _src("S2"), _src("S3")]
    path = _write_sources(tmp_path, records)
    _patch_verdicts(monkeypatch, {}, default="PASS")

    rc = research_gate.main([str(path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "RESOURCE_NEEDED" not in out


def test_check_two_hard_fails_exits_10_and_prints_both(tmp_path, monkeypatch, capsys):
    records = [
        _src("S1", value="1 MW"),
        _src("S2", value="2 MW", source_name="Src2", url="https://b.com"),
        _src("S3", value="3 MW"),
    ]
    path = _write_sources(tmp_path, records)
    _patch_verdicts(
        monkeypatch,
        {"S1": "NUMBER_NOT_FOUND", "S2": "NUMBER_NOT_FOUND", "S3": "PASS"},
    )

    rc = research_gate.main([str(path)])

    assert rc == 10
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.startswith("RESOURCE_NEEDED:")]
    assert len(lines) == 2
    assert any(l == "RESOURCE_NEEDED: S1 | 1 MW | Mordor | https://m.com/a" for l in lines)
    assert any(l == "RESOURCE_NEEDED: S2 | 2 MW | Src2 | https://b.com" for l in lines)


def test_check_dead_link_warning_is_not_hard_fail(tmp_path, monkeypatch, capsys):
    records = [_src("S1"), _src("S2")]
    path = _write_sources(tmp_path, records)
    _patch_verdicts(monkeypatch, {"S1": "DEAD_LINK", "S2": "UNVERIFIABLE_TRUSTED"})

    rc = research_gate.main([str(path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "RESOURCE_NEEDED" not in out


# --- FINALIZE mode ---

def test_finalize_drop_path_rewrites_file(tmp_path, monkeypatch, capsys):
    records = [_src(f"S{i}") for i in range(1, 7)]  # S1..S6
    path = _write_sources(tmp_path, records)
    _patch_verdicts(monkeypatch, {"S1": "NUMBER_NOT_FOUND"})  # 1 fail, 5 valid

    rc = research_gate.main([str(path), "--finalize", "--floor", "4"])

    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [r["id"] for r in data["sources"]]
    assert ids == ["S2", "S3", "S4", "S5", "S6"]
    out = capsys.readouterr().out
    assert "S1" in out


def test_finalize_hold_path_leaves_file_unchanged(tmp_path, monkeypatch, capsys):
    records = [_src(f"S{i}") for i in range(1, 7)]  # S1..S6
    path = _write_sources(tmp_path, records)
    before = path.read_bytes()
    _patch_verdicts(
        monkeypatch,
        {"S1": "NUMBER_NOT_FOUND", "S2": "NUMBER_NOT_FOUND", "S3": "NUMBER_NOT_FOUND"},
    )  # 3 fail, 3 valid remain, floor 4

    rc = research_gate.main([str(path), "--finalize", "--floor", "4"])

    assert rc == 20
    after = path.read_bytes()
    assert after == before
    out = capsys.readouterr().out
    assert "HOLD" in out
    assert "3" in out


def test_finalize_no_hard_fails_no_rewrite(tmp_path, monkeypatch, capsys):
    records = [_src("S1"), _src("S2")]
    path = _write_sources(tmp_path, records)
    before = path.read_bytes()
    _patch_verdicts(monkeypatch, {}, default="PASS")

    rc = research_gate.main([str(path), "--finalize"])

    assert rc == 0
    assert path.read_bytes() == before


def test_finalize_atomicity_valid_json_and_fields_preserved(tmp_path, monkeypatch):
    records = [
        _src("S1", value="1 MW", claim="claim1", source_name="Name1",
             url="https://one.com", quote="quote one", tier=1),
        _src("S2", value="2 MW", claim="claim2", source_name="Name2",
             url="https://two.com", quote="quote two", tier=3),
        _src("S3", value="3 MW", claim="claim3", source_name="Name3",
             url="https://three.com", quote="quote three", tier=2),
    ]
    path = _write_sources(tmp_path, records)
    _patch_verdicts(monkeypatch, {"S2": "NUMBER_NOT_FOUND"})  # 1 fail, 2 valid, floor 2 -> drop

    rc = research_gate.main([str(path), "--finalize", "--floor", "2"])

    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [r["id"] for r in data["sources"]]
    assert ids == ["S1", "S3"]
    s1 = data["sources"][0]
    assert s1["value"] == "1 MW"
    assert s1["claim"] == "claim1"
    assert s1["source_name"] == "Name1"
    assert s1["url"] == "https://one.com"
    assert s1["quote"] == "quote one"
    assert s1["tier"] == 1
    s3 = data["sources"][1]
    assert s3["source_name"] == "Name3"
    assert s3["url"] == "https://three.com"


def test_finalize_boundary_remaining_equals_floor_drops(tmp_path, monkeypatch, capsys):
    records = [_src(f"S{i}") for i in range(1, 6)]  # S1..S5
    path = _write_sources(tmp_path, records)
    _patch_verdicts(monkeypatch, {"S1": "NUMBER_NOT_FOUND"})  # 1 fail, 4 valid, floor 4

    rc = research_gate.main([str(path), "--finalize", "--floor", "4"])

    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [r["id"] for r in data["sources"]]
    assert ids == ["S2", "S3", "S4", "S5"]


def test_finalize_boundary_remaining_below_floor_holds(tmp_path, monkeypatch, capsys):
    records = [_src(f"S{i}") for i in range(1, 6)]  # S1..S5
    path = _write_sources(tmp_path, records)
    before = path.read_bytes()
    _patch_verdicts(
        monkeypatch,
        {"S1": "NUMBER_NOT_FOUND", "S2": "NUMBER_NOT_FOUND"},
    )  # 2 fail, 3 valid remain, floor 4

    rc = research_gate.main([str(path), "--finalize", "--floor", "4"])

    assert rc == 20
    assert path.read_bytes() == before


def test_default_floor_is_4(tmp_path, monkeypatch):
    records = [_src(f"S{i}") for i in range(1, 6)]  # S1..S5
    path = _write_sources(tmp_path, records)
    # 1 fail, 4 remain -> exactly default floor -> drop allowed
    _patch_verdicts(monkeypatch, {"S1": "NUMBER_NOT_FOUND"})

    rc = research_gate.main([str(path), "--finalize"])

    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["sources"]) == 4


# --- internal-verified: deterministic source resolution at finalize ---
_THAI_FACTS_BLOCK = (
    "<!-- THAI-FACT-ALLOWLIST-START -->\n"
    "2.20 THB/kWh | MEA | https://www.mea.or.th/purchase\n"
    "<!-- THAI-FACT-ALLOWLIST-END -->\n"
)


def _write_thai_facts(tmp_path):
    p = tmp_path / "thai-facts.md"
    p.write_text(_THAI_FACTS_BLOCK, encoding="utf-8")
    return p


def test_internal_verified_source_gets_corrected_on_finalize(tmp_path, monkeypatch):
    # The agent-authored source_name is the exact leak that reached 5 live posts.
    records = [
        _src("S1", value="2.20 THB/kWh", source_name="thai-facts.md (canonical reference)",
             url="", source_type="internal-verified"),
        _src("S2", source_name="Mordor", url="https://m.com/a"),
    ]
    path = _write_sources(tmp_path, records)
    thai_facts = _write_thai_facts(tmp_path)
    _patch_verdicts(monkeypatch, {"S1": "THAI_FACTS_OK", "S2": "PASS"})

    rc = research_gate.main([str(path), "--finalize", "--thai-facts", str(thai_facts)])

    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    s1 = next(r for r in data["sources"] if r["id"] == "S1")
    assert s1["source_name"] == "MEA"
    assert s1["url"] == "https://www.mea.or.th/purchase"


def test_web_citations_are_never_rewritten(tmp_path, monkeypatch):
    records = [_src("S1", source_name="Mordor", url="https://m.com/a")]
    path = _write_sources(tmp_path, records)
    thai_facts = _write_thai_facts(tmp_path)
    _patch_verdicts(monkeypatch, {"S1": "PASS"})

    rc = research_gate.main([str(path), "--finalize", "--thai-facts", str(thai_facts)])

    assert rc == 0
    s1 = json.loads(path.read_text(encoding="utf-8"))["sources"][0]
    assert s1["source_name"] == "Mordor"
    assert s1["url"] == "https://m.com/a"


def test_unresolvable_internal_verified_is_dropped(tmp_path, monkeypatch):
    # Passes classify_thai_fact but has no structured row -> must hard-fail
    # rather than publish under the name the agent invented.
    records = [_src(f"S{i}", value=f"{i} MW") for i in range(1, 6)]
    records[0] = _src("S1", value="9.99 THB/kWh", source_name="agent invented",
                      url="", source_type="internal-verified")
    path = _write_sources(tmp_path, records)
    thai_facts = _write_thai_facts(tmp_path)
    _patch_verdicts(monkeypatch, {"S1": "THAI_FACTS_OK"}, default="PASS")

    rc = research_gate.main([str(path), "--finalize", "--floor", "4",
                            "--thai-facts", str(thai_facts)])

    assert rc == 0
    ids = [r["id"] for r in json.loads(path.read_text(encoding="utf-8"))["sources"]]
    assert "S1" not in ids


def test_internal_verified_without_thai_facts_flag_is_dropped(tmp_path, monkeypatch):
    # No --thai-facts means nothing to resolve against, so there is no source we
    # can stand behind — drop rather than trust the agent's.
    records = [_src(f"S{i}", value=f"{i} MW") for i in range(1, 6)]
    records[0] = _src("S1", value="2.20 THB/kWh", source_name="agent invented",
                      url="", source_type="internal-verified")
    path = _write_sources(tmp_path, records)
    _patch_verdicts(monkeypatch, {"S1": "THAI_FACTS_OK"}, default="PASS")

    rc = research_gate.main([str(path), "--finalize", "--floor", "4"])

    assert rc == 0
    ids = [r["id"] for r in json.loads(path.read_text(encoding="utf-8"))["sources"]]
    assert "S1" not in ids


def test_correction_alone_still_rewrites_file(tmp_path, monkeypatch):
    # Zero hard-fails but one correction pending: the file must still be written,
    # or the leaked source_name survives to publish.
    records = [_src("S1", value="2.20 THB/kWh", source_name="thai-facts.md (canonical reference)",
                    url="", source_type="internal-verified")]
    path = _write_sources(tmp_path, records)
    thai_facts = _write_thai_facts(tmp_path)
    _patch_verdicts(monkeypatch, {"S1": "THAI_FACTS_OK"})

    rc = research_gate.main([str(path), "--finalize", "--thai-facts", str(thai_facts)])

    assert rc == 0
    s1 = json.loads(path.read_text(encoding="utf-8"))["sources"][0]
    assert s1["source_name"] == "MEA"


def test_hold_does_not_rewrite_sources(tmp_path, monkeypatch):
    # Under floor -> HOLD. No corrections may be written either.
    records = [_src("S1", value="2.20 THB/kWh", source_name="thai-facts.md (canonical)",
                    url="", source_type="internal-verified"),
               _src("S2"), _src("S3")]
    path = _write_sources(tmp_path, records)
    thai_facts = _write_thai_facts(tmp_path)
    _patch_verdicts(monkeypatch, {"S1": "THAI_FACTS_OK", "S2": "NUMBER_NOT_FOUND",
                                  "S3": "NUMBER_NOT_FOUND"})
    before = path.read_text(encoding="utf-8")

    rc = research_gate.main([str(path), "--finalize", "--floor", "4",
                            "--thai-facts", str(thai_facts)])

    assert rc == 20
    assert path.read_text(encoding="utf-8") == before


# --- deterministic quote resolution at FINALIZE ----------------------------
# The agent no longer authors `quote`. FINALIZE slices it out of the page the
# gate already fetched, the same way source_name/url are resolved for
# internal-verified records.

def _patch_page(monkeypatch, verdict_map, page, default="PASS"):
    _patch_verdicts(monkeypatch, verdict_map, default=default)
    monkeypatch.setattr(research_gate, "_fetch", lambda url: (page, 200, False))


def test_finalize_rewrites_quote_from_the_fetched_page(tmp_path, monkeypatch):
    page = "<p>Thailand added 312 MW of rooftop capacity in 2025. Other text.</p>"
    records = [_src("S1", value="312 MW", quote="Thailand adding some 312 MW of rooftops")]
    path = _write_sources(tmp_path, records)
    _patch_page(monkeypatch, {}, page)

    rc = research_gate.main([str(path), "--finalize"])

    assert rc == 0
    s1 = json.loads(path.read_text(encoding="utf-8"))["sources"][0]
    assert s1["quote"] == "Thailand added 312 MW of rooftop capacity in 2025."


def test_finalize_keeps_agent_quote_when_no_sentence_carries_the_value(tmp_path, monkeypatch):
    """Unresolvable is not a licence to invent — the number check has its own say."""
    records = [_src("S1", value="312 MW", quote="original agent text")]
    path = _write_sources(tmp_path, records)
    _patch_page(monkeypatch, {}, "<p>Nothing numeric on this page.</p>")

    rc = research_gate.main([str(path), "--finalize"])

    assert rc == 0
    s1 = json.loads(path.read_text(encoding="utf-8"))["sources"][0]
    assert s1["quote"] == "original agent text"


def test_finalize_does_not_touch_internal_verified_quotes(tmp_path, monkeypatch):
    """No page was fetched for these — there is nothing to slice a quote from."""
    records = [_src("S1", value="2.20 THB/kWh", source_name="", url="",
                    quote="", source_type="internal-verified")]
    path = _write_sources(tmp_path, records)
    thai_facts = _write_thai_facts(tmp_path)
    _patch_page(monkeypatch, {"S1": "THAI_FACTS_OK"}, "<p>2.20 THB/kWh somewhere.</p>")

    rc = research_gate.main([str(path), "--finalize", "--thai-facts", str(thai_facts)])

    assert rc == 0
    s1 = json.loads(path.read_text(encoding="utf-8"))["sources"][0]
    assert s1["quote"] == ""
    assert s1["source_name"] == "MEA"


def test_hold_does_not_rewrite_resolved_quotes(tmp_path, monkeypatch):
    page = "<p>Thailand added 312 MW of rooftop capacity in 2025.</p>"
    records = [_src("S1", value="312 MW", quote="agent text"),
               _src("S2"), _src("S3")]
    path = _write_sources(tmp_path, records)
    _patch_page(monkeypatch, {"S2": "NUMBER_NOT_FOUND", "S3": "NUMBER_NOT_FOUND"}, page)
    before = path.read_text(encoding="utf-8")

    rc = research_gate.main([str(path), "--finalize", "--floor", "4"])

    assert rc == 20
    assert path.read_text(encoding="utf-8") == before


# --- video-writer specific: transcript source_type must pass through untouched ---

def test_transcript_record_finalizes_clean(tmp_path, monkeypatch):
    # No page to check; must never be treated as a hard-fail or get its
    # quote rewritten from an unrelated fetch of the video URL.
    records = [_src("S1", value="50 MW", source_name="", url="https://youtu.be/abc123?t=90",
                     quote="the plant produces 50 megawatts", source_type="transcript")]
    path = _write_sources(tmp_path, records)
    monkeypatch.setattr(research_gate, "_fetch", lambda url: ("", None, False))
    monkeypatch.setattr(research_gate, "classify", lambda c, text, code, unreadable=False: "TRANSCRIPT_OK")

    rc = research_gate.main([str(path), "--finalize"])

    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    s1 = data["sources"][0]
    assert s1["quote"] == "the plant produces 50 megawatts"
    assert s1["source_name"] == ""

"""Tests for verify_publish.py's self-citation check.

Wires shared/self_citations.find_self_citations() into the publish gate as a
hard FAIL so a leak blocks a new publish instead of only showing up on a
retroactive, manually-run sweep. Ported from claude-blog's identical gate
(commit 348ae7b / dee3a0d).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from verify_publish import check_self_citations  # noqa: E402


class TestCheckSelfCitations:
    def test_clean_content_passes(self):
        checks = check_self_citations("The Provincial Electricity Authority (PEA) sets the rate.")
        assert len(checks) == 1
        assert checks[0].ok is True
        assert checks[0].severity == "fail"  # hard check, just currently passing

    def test_brand_as_canonical_source_fails(self):
        checks = check_self_citations("Green Energy Thailand canonical Thai facts")
        assert len(checks) == 1
        assert checks[0].ok is False
        assert checks[0].severity == "fail"
        assert "BRAND_AS_SOURCE" in checks[0].detail

    def test_literal_internal_filename_fails(self):
        checks = check_self_citations("see thai-facts.md for the allowlist")
        assert checks[0].ok is False
        assert "INTERNAL_FILENAME" in checks[0].detail

    def test_chart_compiled_by_credit_still_passes(self):
        # Legitimate chart-source-credit convention — must not regress into a
        # false-positive block on every chart-bearing article.
        checks = check_self_citations("Source: DEDE, MEA/PEA regulations; compiled by Green Energy Thailand")
        assert checks[0].ok is True

    def test_video_transcript_attribution_unaffected(self):
        # This pipeline's own legitimate pattern: a claim sourced to the video
        # transcript itself, not a web URL. Must not be mistaken for self-citation.
        checks = check_self_citations("As stated in the video transcript at 04:12, the panel output was 6 GW.")
        assert checks[0].ok is True

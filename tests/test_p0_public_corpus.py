"""Public P0 corpus must not contain private profile records."""

from __future__ import annotations

import json
import re
from pathlib import Path


def test_public_p0b_projection_contains_cv_rows_only() -> None:
    root = Path(__file__).parents[1]
    projection = root / "data" / "fitcv-p0-corpus" / "p0b" / "candidate_evidence_projection.jsonl"
    reviewed = root / "data" / "fitcv-p0-corpus" / "p0b" / "reviewed_requirement_evidence.jsonl"
    manifest = json.loads(
        (root / "data" / "fitcv-p0-corpus" / "p0b" / "projection_manifest.json").read_text(encoding="utf-8")
    )
    rows = [json.loads(line) for line in projection.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert rows
    assert all(row["source_kind"] == "cv" for row in rows)
    assert all("private" not in row["source_file"].lower() for row in rows)
    assert "Colton Alexander" not in projection.read_text(encoding="utf-8")
    assert "Colton Alexander" not in reviewed.read_text(encoding="utf-8")
    evidence_fields = [
        value
        for row in rows
        for value in (row.get("raw_evidence_text"), row.get("source_section"))
        if isinstance(value, str)
    ]
    reviewed_fields = [
        value
        for line in reviewed.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for value in (
            json.loads(line).get("raw_evidence_text"),
            json.loads(line).get("provenance", {}).get("evidence", {}).get("source_section"),
        )
        if isinstance(value, str)
    ]
    for value in evidence_fields + reviewed_fields:
        assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value)
        assert not re.search(r"(?<!\d)\+?\d[\d ()-]{7,}\d(?!\d)", value)
    assert manifest["counts"]["records"] == len(rows)
    assert manifest["counts"]["private_profile_records"] == 0

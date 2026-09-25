import json
from pathlib import Path

from scripts.prepare_rag_impact_corpus import validate_corpus


ROOT = Path(__file__).resolve().parents[1]


def test_committed_fixture_satisfies_dataset_contract() -> None:
    fixture = json.loads(
        (ROOT / "tests" / "fixtures" / "rag_impact_benchmark.json").read_text(
            encoding="utf-8"
        )
    )
    assert validate_corpus(fixture) == []


def test_dataset_rejects_pii_and_split_overlap() -> None:
    fixture = json.loads(
        (ROOT / "tests" / "fixtures" / "rag_impact_benchmark.json").read_text(
            encoding="utf-8"
        )
    )
    fixture["jobs"]["pilot"][0]["description"] += " contact bad@example.com"
    fixture["jobs"]["pilot"][0]["scenario_id"] = fixture["jobs"]["development"][0]["scenario_id"]
    errors = validate_corpus(fixture)
    assert any("PII" in error for error in errors)
    assert any("duplicate scenario_id" in error for error in errors)


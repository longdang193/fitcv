from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from fitcv.evidence import retrieve_evidence_bundle


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = REPO_ROOT / "data/fitcv-p0-corpus/p0b/p0b_source_job_relevance_fixture_v2_human_frozen.json"
DEFAULT_PACKET = REPO_ROOT / "data/fitcv-p0-corpus/p0b/p0b_source_job_review_packet_v2_human_adjudicated.json"
DEFAULT_GROUP_MAP = REPO_ROOT / "data/fitcv-p0-corpus/p0b/p0b_source_job_source_group_map_v2.json"
DEFAULT_PROJECTION = REPO_ROOT / "data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl"
DEFAULT_POLICY = REPO_ROOT / "config/policy/cv_analysis.yaml"
DEFAULT_OUTPUT = REPO_ROOT / ".tmp/p0b-v2-relevance-evaluation.json"

THRESHOLDS = {
    "selected_requirement_recall": 0.80,
    "minimum_source_group_recall": 0.60,
    "incorrect_pairs": 0,
    "hard_negative_false_positives": 0,
    "validation_rate": 1.0,
    "minimum_rows": 100,
    "minimum_source_groups": 20,
}
LABEL_TO_GRADE = {"irrelevant": 0, "borderline": 1, "relevant": 2}
REVIEWER_LABEL_TO_GRADES = {"irrelevant": {0}, "borderline": {1}, "relevant": {2, 3}}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _packet_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for section in ("unanimous_rows", "disagreements")
        for row in packet.get(section, [])
    ]


def _error(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def validate_inputs(
    fixture: dict[str, Any],
    packet: dict[str, Any],
    group_map: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    fixture_rows = fixture.get("rows")
    packet_rows = _packet_rows(packet)
    mapped_rows = group_map.get("rows")
    source_groups = group_map.get("source_groups")

    if fixture.get("schema_version") != "p0b.source_job_relevance_fixture.v2":
        _error(errors, "fixture_schema_version_invalid")
    if fixture.get("status") != "frozen_human_adjudicated":
        _error(errors, "fixture_status_invalid")
    if not isinstance(fixture_rows, list):
        _error(errors, "fixture_rows_missing")
        fixture_rows = []
    if not isinstance(mapped_rows, dict) or not isinstance(source_groups, dict):
        _error(errors, "source_group_map_invalid")
        mapped_rows = {}
        source_groups = {}

    fixture_by_id = {}
    for row in fixture_rows:
        requirement_id = str(row.get("requirement_instance_id") or "")
        if not requirement_id or requirement_id in fixture_by_id:
            _error(errors, f"fixture_requirement_id_invalid:{requirement_id}")
        fixture_by_id[requirement_id] = row
        label = row.get("final_relevance_label")
        grade = row.get("final_relevance_grade")
        if label not in LABEL_TO_GRADE or grade != LABEL_TO_GRADE.get(label):
            _error(errors, f"fixture_label_grade_invalid:{requirement_id}")

    packet_by_id = {}
    for row in packet_rows:
        requirement_id = str(row.get("requirement_instance_id") or "")
        if not requirement_id or requirement_id in packet_by_id:
            _error(errors, f"packet_requirement_id_invalid:{requirement_id}")
        packet_by_id[requirement_id] = row
        if requirement_id not in fixture_by_id:
            _error(errors, f"packet_requirement_not_in_fixture:{requirement_id}")
            continue
        fixture_row = fixture_by_id[requirement_id]
        for field in ("source_record_id", "case_id", "requirement_text"):
            if row.get(field) != fixture_row.get(field):
                _error(errors, f"{requirement_id}:{field}_mismatch")
        for arm in ("reviewer_a", "reviewer_b"):
            review = row.get(arm)
            if not isinstance(review, dict):
                _error(errors, f"{requirement_id}:{arm}_missing")
                continue
            label = review.get("relevance_label")
            grade = review.get("relevance_grade")
            if label not in REVIEWER_LABEL_TO_GRADES or grade not in REVIEWER_LABEL_TO_GRADES.get(label, set()):
                _error(errors, f"{requirement_id}:{arm}_label_grade_invalid")

    if set(fixture_by_id) != set(packet_by_id):
        _error(errors, "fixture_packet_id_set_mismatch")

    map_by_id = {str(key): value for key, value in mapped_rows.items()}
    if set(fixture_by_id) != set(map_by_id):
        _error(errors, "fixture_group_map_id_set_mismatch")

    group_ids: set[str] = set()
    group_members: dict[str, set[str]] = {}
    for requirement_id, row in fixture_by_id.items():
        mapped = map_by_id.get(requirement_id, {})
        group_id = str(mapped.get("source_group_id") or "")
        group_ids.add(group_id)
        group_members.setdefault(group_id, set()).add(requirement_id)
        if not group_id or group_id not in source_groups:
            _error(errors, f"{requirement_id}:source_group_invalid")
        for field in ("source_record_id", "case_id"):
            if mapped.get(field) != row.get(field):
                _error(errors, f"{requirement_id}:group_map_{field}_mismatch")

    if len(fixture_rows) < THRESHOLDS["minimum_rows"]:
        _error(errors, "minimum_row_gate_failed")
    if len(group_ids) < THRESHOLDS["minimum_source_groups"]:
        _error(errors, "minimum_source_group_gate_failed")
    for group_id, requirement_ids in group_members.items():
        if group_id and set(source_groups.get(group_id, {}).get("requirement_ids", [])) != requirement_ids:
            _error(errors, f"{group_id}:group_membership_mismatch")

    return {
        "passed": not errors,
        "errors": errors,
        "fixture_rows": len(fixture_rows),
        "packet_rows": len(packet_rows),
        "source_groups": len(group_ids),
        "validation_cases": {"passed": len(group_ids) if not errors else 0, "total": len(group_ids)},
        "fixture_by_id": fixture_by_id,
        "packet_by_id": packet_by_id,
        "map_by_id": map_by_id,
    }


def _pair(requirement_id: str, gold_grade: int, predicted_grade: int) -> dict[str, Any]:
    return {
        "requirement_instance_id": requirement_id,
        "gold_grade": gold_grade,
        "predicted_grade": predicted_grade,
    }


def evaluate_arm(validation: dict[str, Any], arm: str) -> dict[str, Any]:
    fixture_by_id = validation["fixture_by_id"]
    packet_by_id = validation["packet_by_id"]
    map_by_id = validation["map_by_id"]
    incorrect_pairs: list[dict[str, Any]] = []
    hard_negative_false_positives: list[dict[str, Any]] = []
    group_stats: dict[str, dict[str, Any]] = {}
    true_positive = false_negative = 0

    for requirement_id, fixture_row in fixture_by_id.items():
        gold_grade = int(fixture_row["final_relevance_grade"])
        predicted_grade = int(packet_by_id[requirement_id][arm]["relevance_grade"])
        selected = predicted_grade >= 2
        gold_relevant = gold_grade >= 2
        if selected and gold_relevant:
            true_positive += 1
        elif not selected and gold_relevant:
            false_negative += 1
        if selected and gold_grade == 0:
            incorrect_pairs.append(_pair(requirement_id, gold_grade, predicted_grade))
        if selected and gold_grade == 1:
            hard_negative_false_positives.append(_pair(requirement_id, gold_grade, predicted_grade))

        group_id = map_by_id[requirement_id]["source_group_id"]
        stats = group_stats.setdefault(group_id, {"gold_relevant": 0, "selected_relevant": 0, "selected_total": 0})
        stats["gold_relevant"] += int(gold_relevant)
        stats["selected_relevant"] += int(selected and gold_relevant)
        stats["selected_total"] += int(selected)

    per_group = []
    for group_id in sorted(group_stats):
        stats = group_stats[group_id]
        gold_relevant = stats["gold_relevant"]
        per_group.append({
            "source_group_id": group_id,
            **stats,
            "recall": stats["selected_relevant"] / gold_relevant if gold_relevant else None,
        })
    eligible_groups = [row for row in per_group if row["recall"] is not None]
    selected_recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    minimum_group_recall = min((row["recall"] for row in eligible_groups), default=0.0)
    gates = {
        "selected_requirement_recall": selected_recall >= THRESHOLDS["selected_requirement_recall"],
        "minimum_source_group_recall": minimum_group_recall >= THRESHOLDS["minimum_source_group_recall"],
        "incorrect_pairs": len(incorrect_pairs) == THRESHOLDS["incorrect_pairs"],
        "hard_negative_false_positives": len(hard_negative_false_positives) == THRESHOLDS["hard_negative_false_positives"],
    }
    return {
        "selected_requirement_recall": selected_recall,
        "true_positive": true_positive,
        "false_negative": false_negative,
        "gold_relevant": true_positive + false_negative,
        "incorrect_pairs": incorrect_pairs,
        "hard_negative_false_positives": hard_negative_false_positives,
        "minimum_source_group_recall": minimum_group_recall,
        "per_source_group": per_group,
        "gates": gates,
        "eligible": validation["passed"] and all(gates.values()),
    }


def _evaluate_selected(validation: dict[str, Any], selected_by_id: dict[str, bool]) -> dict[str, Any]:
    fixture_by_id = validation["fixture_by_id"]
    map_by_id = validation["map_by_id"]
    incorrect_pairs: list[dict[str, Any]] = []
    hard_negative_false_positives: list[dict[str, Any]] = []
    group_stats: dict[str, dict[str, Any]] = {}
    true_positive = false_negative = 0

    for requirement_id, fixture_row in fixture_by_id.items():
        gold_grade = int(fixture_row["final_relevance_grade"])
        selected = bool(selected_by_id.get(requirement_id, False))
        gold_relevant = gold_grade >= 2
        if selected and gold_relevant:
            true_positive += 1
        elif not selected and gold_relevant:
            false_negative += 1
        if selected and gold_grade == 0:
            incorrect_pairs.append(_pair(requirement_id, gold_grade, 2))
        if selected and gold_grade == 1:
            hard_negative_false_positives.append(_pair(requirement_id, gold_grade, 2))

        group_id = map_by_id[requirement_id]["source_group_id"]
        stats = group_stats.setdefault(group_id, {"gold_relevant": 0, "selected_relevant": 0, "selected_total": 0})
        stats["gold_relevant"] += int(gold_relevant)
        stats["selected_relevant"] += int(selected and gold_relevant)
        stats["selected_total"] += int(selected)

    per_group = []
    for group_id in sorted(group_stats):
        stats = group_stats[group_id]
        gold_relevant = stats["gold_relevant"]
        per_group.append({
            "source_group_id": group_id,
            **stats,
            "recall": stats["selected_relevant"] / gold_relevant if gold_relevant else None,
        })
    eligible_groups = [row for row in per_group if row["recall"] is not None]
    selected_recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    minimum_group_recall = min((row["recall"] for row in eligible_groups), default=0.0)
    gates = {
        "selected_requirement_recall": selected_recall >= THRESHOLDS["selected_requirement_recall"],
        "minimum_source_group_recall": minimum_group_recall >= THRESHOLDS["minimum_source_group_recall"],
        "incorrect_pairs": len(incorrect_pairs) == THRESHOLDS["incorrect_pairs"],
        "hard_negative_false_positives": len(hard_negative_false_positives) == THRESHOLDS["hard_negative_false_positives"],
    }
    return {
        "predicted_selected": sum(selected_by_id.values()),
        "selected_requirement_recall": selected_recall,
        "true_positive": true_positive,
        "false_negative": false_negative,
        "gold_relevant": true_positive + false_negative,
        "incorrect_pairs": incorrect_pairs,
        "hard_negative_false_positives": hard_negative_false_positives,
        "minimum_source_group_recall": minimum_group_recall,
        "per_source_group": per_group,
        "gates": gates,
        "eligible": validation["passed"] and all(gates.values()),
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid_jsonl:{path}:{line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"jsonl_row_not_object:{path}:{line_number}")
        rows.append(row)
    return rows


def evaluate_actual_fitcv(
    fixture: dict[str, Any],
    packet: dict[str, Any],
    group_map: dict[str, Any],
    *,
    projection_path: Path = DEFAULT_PROJECTION,
    policy_path: Path = DEFAULT_POLICY,
) -> dict[str, Any]:
    validation = validate_inputs(fixture, packet, group_map)
    report: dict[str, Any] = {
        "source": "fitcv.retrieve_evidence_bundle",
        "projection": str(projection_path),
        "policy": str(policy_path),
        "validation": {
            key: value
            for key, value in validation.items()
            if key in {"passed", "errors", "fixture_rows", "packet_rows", "source_groups", "validation_cases"}
        },
    }
    if not validation["passed"]:
        return report

    projection = _load_jsonl(projection_path)
    profile = {
        "schema_version": "candidate-profile.v1",
        "_projected_evidence_pool": projection,
    }
    config = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    selected_by_id: dict[str, bool] = {}
    for requirement_id, row in validation["fixture_by_id"].items():
        bundle = retrieve_evidence_bundle(
            profile,
            {
                "responsibilities": [str(row["requirement_text"])],
                "title": str(row.get("title") or ""),
                "required_skills": [],
                "required_skill_entities": [],
            },
            top_k=2,
            config=config,
        )
        selected_by_id[requirement_id] = bool(bundle.get("selected_evidence"))

    report.update(_evaluate_selected(validation, selected_by_id))
    return report


def evaluate_documents(
    fixture: dict[str, Any],
    packet: dict[str, Any],
    group_map: dict[str, Any],
) -> dict[str, Any]:
    validation = validate_inputs(fixture, packet, group_map)
    report: dict[str, Any] = {
        "schema_version": "p0b.source_job_relevance_evaluation.v1",
        "fixture_schema_version": fixture.get("schema_version"),
        "thresholds": THRESHOLDS,
        "validation": {
            key: value
            for key, value in validation.items()
            if key in {"passed", "errors", "fixture_rows", "packet_rows", "source_groups", "validation_cases"}
        },
        "arms": {},
    }
    if validation["passed"]:
        report["arms"] = {arm: evaluate_arm(validation, arm) for arm in ("reviewer_a", "reviewer_b")}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate frozen P0-B source-job relevance fixture.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--group-map", type=Path, default=DEFAULT_GROUP_MAP)
    parser.add_argument("--projection", type=Path, default=DEFAULT_PROJECTION)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    fixture = load_json(args.fixture)
    packet = load_json(args.packet)
    group_map = load_json(args.group_map)
    report = evaluate_documents(fixture, packet, group_map)
    actual_fitcv = evaluate_actual_fitcv(
        fixture,
        packet,
        group_map,
        projection_path=args.projection,
        policy_path=args.policy,
    )
    report["actual_fitcv"] = actual_fitcv
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

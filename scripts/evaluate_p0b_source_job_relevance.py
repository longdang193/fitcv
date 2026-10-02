from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import subprocess
from pathlib import Path
from typing import Any

import yaml

from fitcv.evidence import retrieve_evidence_bundle
from scripts.render_acceptance_state import ALLOWED_STATUSES


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = REPO_ROOT / "data/fitcv-p0-corpus/p0b/p0b_source_job_relevance_fixture_v2_human_frozen.json"
DEFAULT_PACKET = REPO_ROOT / "data/fitcv-p0-corpus/p0b/p0b_source_job_review_packet_v2_human_adjudicated.json"
DEFAULT_GROUP_MAP = REPO_ROOT / "data/fitcv-p0-corpus/p0b/p0b_source_job_source_group_map_v2.json"
DEFAULT_PROJECTION = REPO_ROOT / "data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl"
DEFAULT_EVIDENCE_LINK_REVIEW = REPO_ROOT / "data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv"
DEFAULT_POLICY = REPO_ROOT / "config/policy/cv_analysis.yaml"
DEFAULT_OUTPUT = REPO_ROOT / ".tmp/p0b-v2-relevance-evaluation.json"
DEFAULT_ACCEPTANCE_STATE = REPO_ROOT / "config/acceptance_state.yaml"
DEFAULT_ORACLE_MANIFEST = REPO_ROOT / "data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1_manifest.json"


def _evaluated_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value if value else None


def _evaluation_provenance() -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
        )
        dirty = result.returncode != 0
    except OSError:
        dirty = True
    return {
        "evaluated_commit": _evaluated_commit(),
        "evaluated_worktree_dirty": dirty,
    }


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
QUALIFIER_VERDICTS = {
    "supported",
    "unsupported",
    "unknown",
    "contradicted",
    "satisfied",
    "not_applicable",
}
PUBLIC_REVIEW_COLUMNS = {
    "requirement_instance_id",
    "source_record_id",
    "requirement_text",
    "selected_evidence_ids",
    "accepted_evidence_ids",
    "support_verdict",
    "qualifier_verdict",
}
ORACLE_STATES = {"supported", "unsupported", "unjudged"}
REVIEW_SUPPORT_VERDICTS = {"supported", "unsupported", "unknown"}


def _oracle_state(row: dict[str, Any]) -> str:
    return str(row.get("support_state") or row.get("support_label") or "")


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
    relevance_counts = {label: 0 for label in LABEL_TO_GRADE}

    for requirement_id, fixture_row in fixture_by_id.items():
        gold_grade = int(fixture_row["final_relevance_grade"])
        relevance_counts[str(fixture_row["final_relevance_label"])] += 1
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
        stats = group_stats.setdefault(
            group_id,
            {"gold_relevant": 0, "selected_relevant": 0, "selected_total": 0},
        )
        stats["gold_relevant"] += int(gold_relevant)
        stats["selected_relevant"] += int(selected and gold_relevant)
        stats["selected_total"] += int(selected)

    per_group = []
    for group_id in sorted(group_stats):
        stats = group_stats[group_id]
        gold_relevant = stats["gold_relevant"]
        per_group.append(
            {
                "source_group_id": group_id,
                **stats,
                "recall": stats["selected_relevant"] / gold_relevant if gold_relevant else None,
            }
        )
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
        "relevance_counts": relevance_counts,
        "selected_requirement_recall": selected_recall,
        "true_positive": true_positive,
        "false_negative": false_negative,
        "gold_relevant": true_positive + false_negative,
        "incorrect_pair_count": len(incorrect_pairs),
        "hard_negative_false_positive_count": len(hard_negative_false_positives),
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


def _load_evidence_link_review(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _public_path(path: Path) -> Path:
    resolved = path.resolve()
    if "private" in str(resolved).casefold() or REPO_ROOT not in resolved.parents:
        raise ValueError(f"private_or_external_input:{path}")
    return resolved


def _load_acceptance_state(path: Path = DEFAULT_ACCEPTANCE_STATE) -> dict[str, Any]:
    return yaml.safe_load(_public_path(path).read_text(encoding="utf-8")) or {}


def _public_pair_id(requirement_id: str, evidence_id: str) -> str:
    return f"{requirement_id}::{evidence_id}"


def validate_public_inputs(
    projection: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    oracle: list[dict[str, Any]],
    acceptance_state: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    projection_by_id: dict[str, dict[str, Any]] = {}
    for row in projection:
        evidence_id = str(row.get("evidence_id") or "")
        if not evidence_id or evidence_id in projection_by_id:
            _error(errors, f"projection_evidence_id_invalid:{evidence_id}")
        if row.get("schema_version") != "candidate-evidence.v1":
            _error(errors, f"projection_schema_invalid:{evidence_id}")
        projection_by_id[evidence_id] = row

    review_ids: set[str] = set()
    selected_pairs: set[str] = set()
    accepted_pairs: set[str] = set()
    for row in review_rows:
        requirement_id = str(row.get("requirement_instance_id") or "")
        if not requirement_id or requirement_id in review_ids:
            _error(errors, f"review_requirement_id_invalid:{requirement_id}")
        review_ids.add(requirement_id)
        if not str(row.get("requirement_text") or "").strip():
            _error(errors, f"review_requirement_text_missing:{requirement_id}")
        selected_ids = _split_ids(row.get("selected_evidence_ids"))
        accepted_ids = _split_ids(row.get("accepted_evidence_ids"))
        if not accepted_ids <= selected_ids:
            _error(errors, f"accepted_not_selected:{requirement_id}")
        if not selected_ids <= set(projection_by_id):
            _error(errors, f"selected_not_in_projection:{requirement_id}")
        if not accepted_ids <= set(projection_by_id):
            _error(errors, f"accepted_not_in_projection:{requirement_id}")
        selected_pairs.update(_public_pair_id(requirement_id, evidence_id) for evidence_id in selected_ids)
        accepted_pairs.update(_public_pair_id(requirement_id, evidence_id) for evidence_id in accepted_ids)
        if row.get("support_verdict") not in REVIEW_SUPPORT_VERDICTS:
            _error(errors, f"support_verdict_invalid:{requirement_id}")
        if row.get("qualifier_verdict") not in QUALIFIER_VERDICTS:
            _error(errors, f"qualifier_verdict_invalid:{requirement_id}")

    oracle_by_pair: dict[str, dict[str, Any]] = {}
    oracle_pair_ids: set[str] = set()
    for row in oracle:
        requirement_id = str(row.get("requirement_instance_id") or "")
        evidence_id = str(row.get("evidence_id") or "")
        raw_pair_id = str(row.get("pair_id") or "")
        pair_id = _public_pair_id(requirement_id, evidence_id)
        if not requirement_id or not evidence_id or raw_pair_id in oracle_pair_ids or pair_id in oracle_by_pair:
            _error(errors, f"oracle_pair_invalid:{raw_pair_id or pair_id}")
        oracle_pair_ids.add(raw_pair_id)
        if _oracle_state(row) not in ORACLE_STATES:
            _error(errors, f"oracle_state_invalid:{pair_id}")
        if not str(row.get("adjudicator_id") or row.get("reviewer_id") or "").strip():
            _error(errors, f"oracle_adjudicator_missing:{pair_id}")
        if not str(row.get("reviewed_at") or "").strip():
            _error(errors, f"oracle_reviewed_at_missing:{pair_id}")
        if not str(row.get("source_ref") or row.get("evidence_source_ref") or "").strip():
            _error(errors, f"oracle_source_ref_missing:{pair_id}")
        if evidence_id not in projection_by_id:
            _error(errors, f"oracle_evidence_not_in_projection:{pair_id}")
        oracle_by_pair[pair_id] = row

    thresholds = dict(acceptance_state.get("support_thresholds") or {})
    threshold = thresholds.get("support_recall_threshold")
    threshold_valid = isinstance(threshold, (int, float)) and not isinstance(threshold, bool) and 0.0 <= float(threshold) <= 1.0
    if not threshold_valid:
        _error(errors, "support_recall_threshold_missing_or_invalid")
    status = dict(acceptance_state.get("statuses") or {})
    if status.get("p0_b") not in ALLOWED_STATUSES:
        _error(errors, "p0_b_status_invalid")
    oracle_pairs = set(oracle_by_pair)
    oracle_requirement_ids = {
        str(row.get("requirement_instance_id") or "")
        for row in oracle_by_pair.values()
    }
    if not oracle_requirement_ids <= review_ids:
        _error(errors, "review_requirement_set_incomplete")
    oracle_requirement_ids = {
        str(row.get("requirement_instance_id") or "")
        for row in oracle_by_pair.values()
    }
    evaluated_requirement_ids = {
        str(row.get("requirement_instance_id") or "")
        for row in oracle_by_pair.values()
    }
    scoped_selected_pairs = {
        pair_id
        for pair_id in selected_pairs
        if pair_id.split("::", 1)[0] in evaluated_requirement_ids
    }
    if not scoped_selected_pairs <= oracle_pairs:
        _error(errors, "selected_pair_not_in_oracle")
    judged_pairs = {
        pair_id for pair_id, row in oracle_by_pair.items()
        if _oracle_state(row) != "unjudged"
    }
    return {
        "passed": not errors,
        "errors": sorted(set(errors)),
        "projection_rows": len(projection),
        "review_rows": len(review_rows),
        "review_requirements": len(review_ids),
        "oracle_rows": len(oracle),
        "oracle_pairs": len(oracle_pairs),
        "oracle_coverage": len(judged_pairs) / len(oracle_pairs) if oracle_pairs else 0.0,
        "review_completeness": (
            len(oracle_requirement_ids & review_ids) / len(oracle_requirement_ids)
            if oracle_requirement_ids else 0.0
        ),
        "projection_by_id": projection_by_id,
        "review_ids": review_ids,
        "selected_pairs": scoped_selected_pairs,
        "accepted_pairs": {
            pair_id for pair_id in accepted_pairs
            if pair_id.split("::", 1)[0] in evaluated_requirement_ids
        },
        "oracle_by_pair": oracle_by_pair,
        "support_recall_threshold": threshold,
    }



def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_oracle_manifest(oracle_path: Path, manifest_path: Path, oracle: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError):
        return ["oracle_manifest_unreadable"]
    oracle_meta = dict(manifest.get("oracle") or {})
    labels_meta = dict(manifest.get("labels") or {})
    if manifest.get("schema_version") != "p0b.source_job_support_oracle_manifest.v1":
        errors.append("oracle_manifest_schema_invalid")
    if oracle_meta.get("path") and Path(str(oracle_meta["path"])).name != oracle_path.name:
        errors.append("oracle_manifest_path_mismatch")
    if oracle_meta.get("sha256") != _sha256_file(oracle_path):
        errors.append("oracle_manifest_hash_mismatch")
    if int(oracle_meta.get("rows") or -1) != len(oracle):
        errors.append("oracle_manifest_row_count_mismatch")
    requirement_ids = {str(row.get("requirement_instance_id") or "") for row in oracle}
    evidence_ids = {str(row.get("evidence_id") or "") for row in oracle}
    if int(oracle_meta.get("requirements") or -1) != len(requirement_ids):
        errors.append("oracle_manifest_requirement_count_mismatch")
    if int(oracle_meta.get("evidence_rows") or -1) != len(evidence_ids):
        errors.append("oracle_manifest_evidence_count_mismatch")
    expected_rows = len(requirement_ids) * len(evidence_ids)
    if len(oracle) != expected_rows:
        errors.append(f"oracle_expected_pair_count_mismatch:{len(oracle)}/{expected_rows}")
    counts: dict[str, int] = {}
    for row in oracle:
        state = _oracle_state(row)
        counts[state] = counts.get(state, 0) + 1
    if oracle_meta.get("label_counts") != dict(sorted(counts.items())):
        errors.append("oracle_manifest_label_counts_mismatch")
    if int(labels_meta.get("rows") or -1) != len(oracle):
        errors.append("oracle_label_row_count_mismatch")
    if bool(manifest.get("promotion_eligible")) and (not bool(labels_meta.get("human_review_complete")) or counts.get("unjudged", 0)):
        errors.append("oracle_manifest_promotion_provenance_invalid")
    return errors


def _runtime_requirement_metrics(
    oracle_by_pair: dict[str, dict[str, Any]],
    candidate_support: dict[str, set[str]],
    selected_support: dict[str, set[str]],
) -> dict[str, Any]:
    supported_by_requirement: dict[str, set[str]] = {}
    for pair_id, row in oracle_by_pair.items():
        if _oracle_state(row) != "supported":
            continue
        requirement_id = str(row.get("requirement_instance_id") or "")
        evidence_id = str(row.get("evidence_id") or "")
        supported_by_requirement.setdefault(requirement_id, set()).add(evidence_id)
    supported_requirements = set(supported_by_requirement)
    candidate_requirements = {
        requirement_id for requirement_id, evidence_ids in candidate_support.items() if evidence_ids
    }
    selected_requirements = {
        requirement_id for requirement_id, evidence_ids in selected_support.items() if evidence_ids
    }
    all_selected_pairs = {
        f"{requirement_id}::{evidence_id}"
        for requirement_id, evidence_ids in selected_support.items()
        for evidence_id in evidence_ids
    }
    evaluated_requirements = {
        str(row.get("requirement_instance_id") or "")
        for row in oracle_by_pair.values()
    }
    selected_pairs = {
        pair_id
        for pair_id in all_selected_pairs
        if pair_id.split("::", 1)[0] in evaluated_requirements
    }
    unscoped_selected_pairs = {
        pair_id
        for pair_id in all_selected_pairs
        if pair_id.split("::", 1)[0] not in supported_requirements
    }
    supported_pairs = {
        pair_id for pair_id, row in oracle_by_pair.items() if _oracle_state(row) == "supported"
    }
    unsupported_selected = selected_pairs - supported_pairs
    return {
        "supportable_requirements": len(supported_requirements),
        "candidate_requirement_recall": (
            len(candidate_requirements & supported_requirements) / len(supported_requirements)
            if supported_requirements else None
        ),
        "selected_requirement_coverage": (
            len(selected_requirements & supported_requirements) / len(supported_requirements)
            if supported_requirements else None
        ),
        "selected_pairs": len(selected_pairs),
        "unscoped_selected_pairs": len(unscoped_selected_pairs),
        "supported_selected_pairs": len(selected_pairs & supported_pairs),
        "assignment_precision": (
            len(selected_pairs & supported_pairs) / len(selected_pairs)
            if selected_pairs else None
        ),
        "unsupported_or_unknown_assignments": len(unsupported_selected),
    }


def _runtime_telemetry_summary(job_telemetry: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = sorted(
        float(item.get("retrieval_latency_ms") or 0.0)
        for item in job_telemetry
        if isinstance(item, dict)
    )
    counts = {key: 0 for key in ("canonical", "candidate", "verified", "selected", "assigned", "uncovered")}
    embedding_counts: dict[str, dict[str, int]] = {}
    for telemetry in job_telemetry:
        for key in counts:
            counts[key] += int(dict(telemetry.get("counts") or {}).get(key) or 0)
        for namespace, values in dict(telemetry.get("embedding_counts") or {}).items():
            target = embedding_counts.setdefault(namespace, {"fresh": 0, "reused": 0})
            for state in target:
                target[state] += int(dict(values or {}).get(state) or 0)
    p95_index = max(0, min(len(latencies) - 1, int(len(latencies) * 0.95) - 1)) if latencies else None
    return {
        "jobs": len(job_telemetry),
        "retrieval_latency_ms": {
            "p50": round(statistics.median(latencies), 3) if latencies else None,
            "p95": round(latencies[p95_index], 3) if p95_index is not None else None,
        },
        "counts": counts,
        "embedding_counts": embedding_counts,
    }


def evaluate_runtime_corpus(
    projection_path: Path,
    evidence_link_review_path: Path,
    oracle_path: Path,
    acceptance_state_path: Path = DEFAULT_ACCEPTANCE_STATE,
    oracle_manifest_path: Path = DEFAULT_ORACLE_MANIFEST,
    policy_path: Path = DEFAULT_POLICY,
    top_k: int = 2,
) -> dict[str, Any]:
    projection = _load_jsonl(_public_path(projection_path))
    review_rows = _load_evidence_link_review(_public_path(evidence_link_review_path))
    oracle = _load_jsonl(_public_path(oracle_path))
    acceptance_state = _load_acceptance_state(acceptance_state_path)
    validation = validate_public_inputs(projection, review_rows, oracle, acceptance_state)
    manifest_errors = _validate_oracle_manifest(oracle_path, oracle_manifest_path, oracle)
    validation["errors"] = sorted(set([*validation["errors"], *manifest_errors]))
    validation["passed"] = not validation["errors"]
    if not validation["passed"]:
        return {
            "schema_version": "p0b.runtime_acceptance.v2",
            **_evaluation_provenance(),
            "prediction_source": "fitcv.retrieve_evidence_bundle",
            "validation": {key: value for key, value in validation.items() if key not in {"projection_by_id", "review_ids", "selected_pairs", "accepted_pairs", "oracle_by_pair"}},
            "eligible": False,
            "status": "not_promotable",
        }

    config = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    profile = {"schema_version": "candidate-profile.v1", "_projected_evidence_pool": projection}
    rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for row in review_rows:
        rows_by_source.setdefault(str(row.get("source_record_id") or ""), []).append(row)
    job_outputs: list[dict[str, Any]] = []
    candidate_support: dict[str, set[str]] = {}
    selected_support: dict[str, set[str]] = {}
    for source_record_id, rows in sorted(rows_by_source.items()):
        job_context = {
            "responsibilities": [str(row.get("requirement_text") or "") for row in rows],
            "responsibility_entities": [
                {
                    "source_requirement_id": str(row.get("requirement_instance_id") or ""),
                    "text": str(row.get("requirement_text") or ""),
                }
                for row in rows
            ],
            "title": "",
            "required_skills": [],
            "required_skill_entities": [],
        }
        bundle = retrieve_evidence_bundle(profile, job_context, top_k=top_k, config=config)
        responsibility = dict((bundle.get("requirement_support") or {}).get("responsibility") or {})
        pool = {key: set(value) for key, value in dict(responsibility.get("pool") or {}).items()}
        selected = {key: set(value) for key, value in dict(responsibility.get("selected") or {}).items()}
        for requirement_id, evidence_ids in pool.items():
            candidate_support.setdefault(requirement_id, set()).update(evidence_ids)
        for requirement_id, evidence_ids in selected.items():
            selected_support.setdefault(requirement_id, set()).update(evidence_ids)
        job_outputs.append({
            "source_record_id": source_record_id,
            "requirement_count": len(rows),
            "candidate_evidence_ids": list(bundle.get("retrieved_evidence_ids") or []),
            "selected_evidence_ids": list(bundle.get("selected_evidence_ids") or []),
            "candidate_support": {key: sorted(value) for key, value in pool.items()},
            "selected_support": {key: sorted(value) for key, value in selected.items()},
            "stage_traces": dict(bundle.get("stage_traces") or {}),
            "runtime_telemetry": dict(bundle.get("runtime_telemetry") or {}),
        })
    metrics = _runtime_requirement_metrics(validation["oracle_by_pair"], candidate_support, selected_support)
    telemetry = _runtime_telemetry_summary(
        [dict(output.get("runtime_telemetry") or {}) for output in job_outputs]
    )
    thresholds = dict(acceptance_state.get("support_thresholds") or {})
    threshold = float(thresholds.get("support_recall_threshold") or 1.0)
    gates = {
        "oracle_integrity": not manifest_errors,
        "candidate_requirement_recall": metrics["candidate_requirement_recall"] is not None and metrics["candidate_requirement_recall"] >= threshold,
        "selected_requirement_coverage": metrics["selected_requirement_coverage"] is not None and metrics["selected_requirement_coverage"] >= threshold,
        "assignment_precision": metrics["assignment_precision"] == 1.0,
        "unsupported_assignments": metrics["unsupported_or_unknown_assignments"] == 0,
        "top_k": top_k == 2,
    }
    return {
        "schema_version": "p0b.runtime_acceptance.v2",
        **_evaluation_provenance(),
        "prediction_source": "fitcv.retrieve_evidence_bundle",
        "code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=REPO_ROOT).strip(),
        "policy_sha256": _sha256_file(policy_path),
        "projection_sha256": _sha256_file(projection_path),
        "oracle_manifest_sha256": _sha256_file(oracle_manifest_path),
        "top_k": top_k,
        "validation": {key: value for key, value in validation.items() if key not in {"projection_by_id", "review_ids", "selected_pairs", "accepted_pairs", "oracle_by_pair"}},
        "metrics": metrics,
        "telemetry": telemetry,
        "gates": gates,
        "job_outputs": job_outputs,
        "eligible": bool(validation["passed"] and all(gates.values())),
        "status": "promotable" if validation["passed"] and all(gates.values()) else "not_promotable",
    }

def evaluate_public_corpus(
    projection_path: Path,
    evidence_link_review_path: Path,
    oracle_path: Path,
    acceptance_state_path: Path = DEFAULT_ACCEPTANCE_STATE,
) -> dict[str, Any]:
    projection = _load_jsonl(_public_path(projection_path))
    review_rows = _load_evidence_link_review(_public_path(evidence_link_review_path))
    oracle = _load_jsonl(_public_path(oracle_path))
    acceptance_state = _load_acceptance_state(acceptance_state_path)
    validation = validate_public_inputs(projection, review_rows, oracle, acceptance_state)
    oracle_by_pair = validation["oracle_by_pair"]
    selected_pairs = validation["selected_pairs"]
    judged_selected = selected_pairs & set(oracle_by_pair)
    supported_pairs = {
        pair_id for pair_id, row in oracle_by_pair.items()
        if _oracle_state(row) == "supported"
    }
    unsupported_selected = {
        pair_id for pair_id in judged_selected
        if _oracle_state(oracle_by_pair[pair_id]) == "unsupported"
    }
    unjudged_selected = {
        pair_id for pair_id in judged_selected
        if _oracle_state(oracle_by_pair[pair_id]) == "unjudged"
    }
    true_positive = len(judged_selected & supported_pairs)
    false_negative = len(supported_pairs - judged_selected)
    support_recall = true_positive / len(supported_pairs) if supported_pairs else None
    threshold = validation["support_recall_threshold"]
    thresholds = dict(acceptance_state.get("support_thresholds") or {})
    gates = {
        "pair_false_positives": len(unsupported_selected) <= int(thresholds.get("maximum_pair_false_positives", -1)),
        "review_completeness": validation["review_completeness"] >= float(thresholds.get("minimum_review_completeness", 2.0)),
        "oracle_coverage": validation["oracle_coverage"] >= float(thresholds.get("minimum_oracle_coverage", 2.0)),
        "support_recall": support_recall is not None and isinstance(threshold, (int, float)) and support_recall >= float(threshold),
        "no_unjudged_selected": not unjudged_selected,
    }
    return {
        "schema_version": "p0b.public_source_job_evaluation.v1",
        **_evaluation_provenance(),
        "validation": {key: value for key, value in validation.items() if key not in {"projection_by_id", "review_ids", "selected_pairs", "accepted_pairs", "oracle_by_pair"}},
        "metrics": {
            "true_positive": true_positive,
            "false_negative": false_negative,
            "pair_false_positive": len(unsupported_selected),
            "unjudged_selected": len(unjudged_selected),
            "support_recall": support_recall,
            "relevance_recall": None,
        },
        "gates": gates,
        "eligible": bool(validation["passed"] and all(gates.values())),
        "status": "promotable" if validation["passed"] and all(gates.values()) else "not_promotable",
    }


def _split_ids(value: Any) -> set[str]:
    return {item.strip() for item in str(value or "").split(";") if item.strip()}


def evaluate_evidence_link_review(
    *,
    review_rows: list[dict[str, Any]],
    fixture_by_id: dict[str, dict[str, Any]],
    selected_by_source: dict[str, set[str]],
    selected_by_requirement: dict[str, set[str]],
    projection_ids: set[str],
    support_recall_threshold: float | None,
) -> dict[str, Any]:
    expected_ids = set(fixture_by_id)
    seen_ids: set[str] = set()
    validation_errors: list[str] = []
    supported_rows = 0
    covered_supported_rows = 0
    accepted_pairs = 0
    unsupported_selected_rows = 0
    qualifier_contradictions = 0
    invalid_verdicts = 0
    invalid_qualifier_verdicts = 0
    actual_pairs: set[tuple[str, str]] = set()
    gold_pairs: set[tuple[str, str]] = set()

    for row in review_rows:
        requirement_id = str(row.get("requirement_instance_id") or "")
        source_id = str(row.get("source_record_id") or "")
        historical_selected_ids = _split_ids(row.get("selected_evidence_ids"))
        accepted_ids = _split_ids(row.get("accepted_evidence_ids"))
        assigned_ids = selected_by_requirement.get(requirement_id, set())
        verdict = str(row.get("support_verdict") or "")
        qualifier_verdict = str(row.get("qualifier_verdict") or "")

        if requirement_id not in fixture_by_id:
            validation_errors.append(f"review_requirement_not_in_fixture:{requirement_id}")
        elif requirement_id in seen_ids:
            validation_errors.append(f"review_requirement_duplicate:{requirement_id}")
        else:
            seen_ids.add(requirement_id)
            expected_source_id = str(fixture_by_id[requirement_id].get("source_record_id") or "")
            if source_id != expected_source_id:
                validation_errors.append(f"review_source_record_mismatch:{requirement_id}")

        if verdict not in {"supported", "unsupported", "unknown"}:
            invalid_verdicts += 1
            validation_errors.append(f"review_support_verdict_invalid:{requirement_id}")
        if qualifier_verdict not in QUALIFIER_VERDICTS:
            invalid_qualifier_verdicts += 1
            validation_errors.append(f"review_qualifier_verdict_invalid:{requirement_id}")
        if not accepted_ids <= historical_selected_ids:
            validation_errors.append(f"review_accepted_ids_not_historical_selected:{requirement_id}")
        if not accepted_ids <= projection_ids:
            validation_errors.append(f"review_accepted_ids_not_in_projection:{requirement_id}")
        if verdict == "supported":
            supported_rows += 1
            gold_pairs.update((requirement_id, evidence_id) for evidence_id in accepted_ids)
            if not accepted_ids:
                validation_errors.append(f"supported_without_accepted_evidence:{requirement_id}")
            covered_supported_rows += int(bool(accepted_ids & assigned_ids))
        elif accepted_ids:
            validation_errors.append(f"non_supported_has_accepted_evidence:{requirement_id}")
        if verdict == "unsupported" and assigned_ids:
            unsupported_selected_rows += 1
        if qualifier_verdict == "contradicted":
            qualifier_contradictions += 1
        actual_pairs.update((requirement_id, evidence_id) for evidence_id in assigned_ids)
        accepted_pairs += len(accepted_ids)

    if len(review_rows) != len(expected_ids):
        validation_errors.append("review_coverage_incomplete")
    if seen_ids != expected_ids:
        validation_errors.append("review_requirement_set_mismatch")

    supported_requirement_recall = (
        covered_supported_rows / supported_rows if supported_rows else None
    )
    threshold_approved = (
        isinstance(support_recall_threshold, (int, float))
        and not isinstance(support_recall_threshold, bool)
        and 0.0 <= float(support_recall_threshold) <= 1.0
    )
    support_gate = {
        "threshold": support_recall_threshold,
        "threshold_approved": threshold_approved,
        "complete_review": not any(
            error in {"review_coverage_incomplete", "review_requirement_set_mismatch"}
            for error in validation_errors
        ),
        "valid_verdict_vocabulary": invalid_verdicts == 0,
        "valid_qualifier_vocabulary": invalid_qualifier_verdicts == 0,
        "accepted_ids_in_projection": not any(
            error.startswith("review_accepted_ids_not_in_projection:")
            for error in validation_errors
        ),
        "accepted_ids_in_historical_selection": not any(
            error.startswith("review_accepted_ids_not_historical_selected:")
            for error in validation_errors
        ),
        "supported_link_recall": (
            supported_requirement_recall is not None
            and threshold_approved
            and supported_requirement_recall >= float(support_recall_threshold)
        ),
        "unsupported_selected_assignments": unsupported_selected_rows == 0,
        "qualifier_contradictions": qualifier_contradictions == 0,
        "validation_errors": not validation_errors,
    }
    support_gate["passed"] = all(
        value for key, value in support_gate.items() if key != "threshold"
    )
    return {
        "rows": len(review_rows),
        "accepted_pairs": accepted_pairs,
        "supported_requirement_recall": supported_requirement_recall,
        "unsupported_selected_rows": unsupported_selected_rows,
        "qualifier_contradictions": qualifier_contradictions,
        "pair_true_positive": len(actual_pairs & gold_pairs),
        "pair_false_positive": len(actual_pairs - gold_pairs),
        "pair_false_negative": len(gold_pairs - actual_pairs),
        "pair_precision": (
            len(actual_pairs & gold_pairs) / len(actual_pairs) if actual_pairs else 1.0
        ),
        "pair_recall": (
            len(actual_pairs & gold_pairs) / len(gold_pairs) if gold_pairs else 1.0
        ),
        "validation_errors": sorted(set(validation_errors)),
        "status": "clean" if not validation_errors else "invalid",
        "support_gate": support_gate,
    }


def evaluate_actual_fitcv(
    fixture: dict[str, Any],
    packet: dict[str, Any],
    group_map: dict[str, Any],
    *,
    projection_path: Path = DEFAULT_PROJECTION,
    evidence_link_review_path: Path = DEFAULT_EVIDENCE_LINK_REVIEW,
    policy_path: Path = DEFAULT_POLICY,
    support_recall_threshold: float | None = None,
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
    report["status"] = "comparable"
    report["reason"] = "actual FitCV output evaluated using explicit requirement-scoped evidence assignments"
    rows_by_source: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for requirement_id, row in validation["fixture_by_id"].items():
        source_id = str(row["source_record_id"])
        rows_by_source.setdefault(source_id, []).append((requirement_id, row))

    job_outputs: list[dict[str, Any]] = []
    for rows in rows_by_source.values():
        first_row = rows[0][1]
        requirements = [str(row["requirement_text"]) for _, row in rows]
        job_context = {
            "responsibilities": requirements,
            "responsibility_entities": [
                {
                    "source_requirement_id": requirement_id,
                    "text": str(row["requirement_text"]),
                }
                for requirement_id, row in rows
            ],
            "title": str(first_row.get("title") or ""),
            "required_skills": [],
            "required_skill_entities": [],
        }
        bundle = retrieve_evidence_bundle(profile, job_context, top_k=2, config=config)
        job_outputs.append(
            {
                "source_record_id": str(first_row["source_record_id"]),
                "title": str(first_row.get("title") or ""),
                "requirement_count": len(rows),
                "selected_evidence_ids": list(bundle.get("selected_evidence_ids") or []),
                "selected_evidence_by_requirement": dict(
                    (bundle.get("requirement_support") or {})
                    .get("responsibility", {})
                    .get("selected", {})
                    or {}
                ),
                "retrieved_evidence_ids": list(bundle.get("retrieved_evidence_ids") or []),
                "selected_evidence_count": int(bundle.get("selected_evidence_count") or 0),
                "stage_traces": dict(bundle.get("stage_traces") or {}),
            }
        )

    report["job_outputs"] = job_outputs
    selected_by_source = {
        output["source_record_id"]: set(output["selected_evidence_ids"])
        for output in job_outputs
    }
    selected_by_requirement = {
        requirement_id: set(evidence_ids)
        for output in job_outputs
        for requirement_id, evidence_ids in output["selected_evidence_by_requirement"].items()
    }
    selected_by_id = {
        requirement_id: bool(selected_by_requirement.get(requirement_id))
        for requirement_id in validation["fixture_by_id"]
    }
    report["actual_metrics"] = _evaluate_selected(validation, selected_by_id)
    review_rows = _load_evidence_link_review(evidence_link_review_path)
    projection_ids = {
        str(item.get("evidence_id") or "")
        for item in projection
        if str(item.get("evidence_id") or "")
    }
    link_review = evaluate_evidence_link_review(
        review_rows=review_rows,
        fixture_by_id=validation["fixture_by_id"],
        selected_by_source=selected_by_source,
        selected_by_requirement=selected_by_requirement,
        projection_ids=projection_ids,
        support_recall_threshold=support_recall_threshold,
    )
    report["evidence_link_review"] = {
        "path": str(evidence_link_review_path),
        **link_review,
    }
    report["support_gate"] = dict(link_review["support_gate"])
    report["eligible"] = bool(
        report["actual_metrics"]["eligible"]
        and report["support_gate"]["passed"]
    )
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
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--group-map", type=Path)
    parser.add_argument("--projection", type=Path, default=DEFAULT_PROJECTION)
    parser.add_argument("--evidence-link-review", type=Path, default=DEFAULT_EVIDENCE_LINK_REVIEW)
    parser.add_argument("--oracle", type=Path)
    parser.add_argument("--oracle-manifest", type=Path, default=DEFAULT_ORACLE_MANIFEST)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--historical-review", action="store_true")
    parser.add_argument("--acceptance-state", type=Path, default=DEFAULT_ACCEPTANCE_STATE)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--support-recall-threshold", type=float, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if args.oracle:
        evaluator = evaluate_public_corpus if args.historical_review else evaluate_runtime_corpus
        kwargs = {
            "projection_path": args.projection,
            "evidence_link_review_path": args.evidence_link_review,
            "oracle_path": args.oracle,
            "acceptance_state_path": args.acceptance_state,
        }
        if not args.historical_review:
            kwargs.update({"oracle_manifest_path": args.oracle_manifest, "policy_path": args.policy, "top_k": args.top_k})
        report = evaluator(**kwargs)
    elif args.fixture and args.packet and args.group_map:
        fixture = load_json(args.fixture)
        packet = load_json(args.packet)
        group_map = load_json(args.group_map)
        report = evaluate_documents(fixture, packet, group_map)
        report["actual_fitcv"] = evaluate_actual_fitcv(
            fixture,
            packet,
            group_map,
            projection_path=args.projection,
            evidence_link_review_path=args.evidence_link_review,
            policy_path=args.policy,
            support_recall_threshold=args.support_recall_threshold,
        )
    else:
        report = {
            "schema_version": "p0b.public_source_job_evaluation.v1",
            "status": "not_promotable",
            "eligible": False,
            "validation": {"passed": False, "errors": ["oracle_input_required"]},
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("eligible") else 1


if __name__ == "__main__":
    raise SystemExit(main())

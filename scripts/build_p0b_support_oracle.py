from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path

ALLOWED = {"supported", "unsupported", "unjudged"}
LABEL_SCHEMA = "p0b.support_oracle_label.v1"
ORACLE_SCHEMA = "p0b.source_job_support_oracle.v1"
MANIFEST_SCHEMA = "p0b.source_job_support_oracle_manifest.v1"

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"row_not_object:{path}:{line_no}")
        rows.append(row)
    return rows

def expected_pair_id(requirement_id: str, evidence_id: str) -> str:
    return "pair_" + hashlib.sha256(f"{requirement_id}|{evidence_id}".encode()).hexdigest()[:24]

def build(projection_path: Path, labels_path: Path, output_path: Path, manifest_path: Path) -> dict:
    projection = load_jsonl(projection_path)
    labels = load_jsonl(labels_path)
    evidence = {str(x.get("evidence_id") or ""): x for x in projection}
    if len(evidence) != len(projection) or not evidence:
        raise ValueError("projection_evidence_ids_not_unique")
    seen = set()
    requirement_ids = set()
    reviewer_ids = set()
    cohort_ids = set()
    oracle = []
    for row in labels:
        if row.get("schema_version") != LABEL_SCHEMA:
            raise ValueError("label_schema_invalid")
        rid = str(row.get("requirement_instance_id") or "")
        eid = str(row.get("evidence_id") or "")
        pid = str(row.get("pair_id") or "")
        label = str(row.get("support_label") or "")
        if label not in ALLOWED:
            raise ValueError(f"label_invalid:{pid}")
        if eid not in evidence:
            raise ValueError(f"evidence_missing_from_projection:{eid}")
        if pid != expected_pair_id(rid, eid):
            raise ValueError(f"pair_id_invalid:{pid}")
        if pid in seen:
            raise ValueError(f"duplicate_pair_id:{pid}")
        seen.add(pid)
        requirement_ids.add(rid)
        reviewer_ids.add(str(row.get("reviewer_id") or ""))
        cohort_ids.add(str(row.get("cohort_id") or ""))
        src = row.get("source_reference") or {}
        if src.get("evidence_source_ref") != evidence[eid].get("source_ref"):
            raise ValueError(f"source_ref_mismatch:{pid}")
        oracle.append({
            "schema_version": ORACLE_SCHEMA,
            "cohort_id": row["cohort_id"],
            "pair_id": pid,
            "requirement_instance_id": rid,
            "source_record_id": str(row.get("source_record_id") or ""),
            "requirement_text": str(row.get("requirement_text") or ""),
            "evidence_id": eid,
            "evidence_source_ref": str(evidence[eid].get("source_ref") or ""),
            "support_label": label,
            "reviewer_id": str(row.get("reviewer_id") or ""),
            "reviewed_at": str(row.get("reviewed_at") or ""),
            "rationale": str(row.get("rationale") or ""),
        })
    if len(cohort_ids) != 1:
        raise ValueError("cohort_id_not_unique")
    expected = len(requirement_ids) * len(evidence)
    if len(oracle) != expected:
        raise ValueError(f"oracle_coverage_incomplete:{len(oracle)}/{expected}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in oracle),
        encoding="utf-8", newline="\n"
    )
    counts = Counter(row["support_label"] for row in oracle)
    all_human = bool(reviewer_ids) and all(x.startswith("human:") for x in reviewer_ids)
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "status": "validated_human_oracle" if all_human else "validated_draft_pending_human_acceptance",
        "cohort_id": next(iter(cohort_ids)),
        "projection": {
            "path": str(projection_path).replace("\\", "/"),
            "sha256": sha256_file(projection_path),
            "records": len(projection),
            "unique_evidence_ids": len(evidence),
        },
        "labels": {
            "path": str(labels_path).replace("\\", "/"),
            "sha256": sha256_file(labels_path),
            "rows": len(labels),
            "reviewer_ids": sorted(reviewer_ids),
            "human_review_complete": all_human,
        },
        "oracle": {
            "path": str(output_path).replace("\\", "/"),
            "sha256": sha256_file(output_path),
            "rows": len(oracle),
            "requirements": len(requirement_ids),
            "evidence_rows": len(evidence),
            "coverage": len(oracle) / expected if expected else 0.0,
            "label_counts": dict(sorted(counts.items())),
        },
        "promotion_eligible": all_human and len(oracle) == expected,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--projection", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args()
    manifest = build(a.projection, a.labels, a.output, a.manifest)
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

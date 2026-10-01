from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path

ALLOWED = {"supported", "unsupported", "unjudged"}

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def validate(oracle_path: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    oracle = load_jsonl(oracle_path)
    errors = []
    if manifest.get("schema_version") != "p0b.source_job_support_oracle_manifest.v1":
        errors.append("manifest_schema_invalid")
    if manifest.get("oracle", {}).get("sha256") != sha256_file(oracle_path):
        errors.append("oracle_hash_mismatch")
    pair_ids = [str(r.get("pair_id") or "") for r in oracle]
    if len(pair_ids) != len(set(pair_ids)):
        errors.append("duplicate_pair_id")
    if any(r.get("support_label") not in ALLOWED for r in oracle):
        errors.append("support_label_invalid")
    reqs = {r.get("requirement_instance_id") for r in oracle}
    evidence = {r.get("evidence_id") for r in oracle}
    expected = len(reqs) * len(evidence)
    if len(oracle) != expected:
        errors.append(f"coverage_incomplete:{len(oracle)}/{expected}")
    coverage = len(oracle) / expected if expected else 0.0
    if manifest.get("oracle", {}).get("coverage") != coverage:
        errors.append("coverage_manifest_mismatch")
    counts = Counter(r.get("support_label") for r in oracle)
    if manifest.get("oracle", {}).get("label_counts") != dict(sorted(counts.items())):
        errors.append("label_counts_mismatch")
    human_review_complete = bool(manifest.get("labels", {}).get("human_review_complete"))
    if human_review_complete:
        acceptance_ids = manifest.get("labels", {}).get("human_acceptance_ids") or []
        acceptance_dates = manifest.get("labels", {}).get("human_acceptance_dates") or []
        if not acceptance_ids or not all(str(x).startswith("human:") for x in acceptance_ids):
            errors.append("human_acceptance_provenance_invalid")
        if not acceptance_dates or not all(str(x) for x in acceptance_dates):
            errors.append("human_acceptance_date_missing")
    if manifest.get("promotion_eligible") and not human_review_complete:
        errors.append("promotion_without_human_review")
    if manifest.get("promotion_eligible") and counts.get("unjudged", 0):
        errors.append("promotion_with_unjudged_pairs")
    return {
        "status": "clean" if not errors else "blocked",
        "oracle_rows": len(oracle),
        "requirements": len(reqs),
        "evidence_rows": len(evidence),
        "coverage": coverage,
        "label_counts": dict(sorted(counts.items())),
        "unjudged": counts.get("unjudged", 0),
        "human_review_complete": human_review_complete,
        "promotion_eligible": bool(manifest.get("promotion_eligible")),
        "errors": errors,
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--oracle", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args()
    result = validate(a.oracle, a.manifest)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not result["errors"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

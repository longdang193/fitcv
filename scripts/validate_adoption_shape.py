"""
@meta
name: validate_adoption_shape
type: script
domain: docs
responsibility:
  - Validate required Mode B repo surfaces for managed architecture metadata.
  - Enforce the Phase 5 managed feature source, generated contract, and lineage shape.
  - Fail when generated architecture docs are stale.
inputs:
  - repo_config/adoption-mode.yaml
  - docs/features/
  - docs/stages/
  - docs/generated/
  - docs/intent/
  - scripts/sync_architecture_docs.py
outputs:
  - stdout validation report
tags:
  - docs
  - architecture
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re
from typing import Any, cast

import yaml


REQUIRED_DOC_PATHS = [
    "docs/setup.md",
    "docs/configuration.md",
    "docs/usage.md",
    "docs/pipeline.md",
    "docs/architecture.md",
    "docs/intent/README.md",
    "docs/intent/project-charter.md",
    "docs/intent/stakeholders.md",
    "docs/intent/success-outcomes.md",
    "docs/intent/constraints-and-non-goals.md",
]
FEATURE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
CAPABILITY_SUFFIX_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PROVES_PATTERN = re.compile(r"@proves\s+([a-z][a-z0-9_]*\.[a-z0-9]+(?:-[a-z0-9]+)*)")
SOURCE_ALLOWED_KEYS = {
    "feature_id",
    "name",
    "status",
    "type",
    "summary",
    "invariants",
    "domains",
    "depends_on",
    "capabilities",
    "stage_participation",
    "lineage_exceptions",
}
FORBIDDEN_LINEAGE_KEYS = {
    "generated_contract",
    "naming_policy",
    "capability_shape",
    "capability_ids",
    "refs",
    "refs_by_type",
}
LINEAGE_ALIAS_PATTERN = re.compile(r"(^|\s)[&*]id\d+\b", re.MULTILINE)
LINEAGE_EVIDENCE_FIELDS = ("code", "tests", "docs", "specs", "plans", "configs", "components")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Mode B adoption shape.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to this script's repo.",
    )
    return parser.parse_args(argv)


def read_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def requires_python_metadata(path: Path, repo_root: Path) -> bool:
    relative = relpath(path, repo_root)
    if "__pycache__" in path.parts:
        return False
    if path.name == "__init__.py":
        return False
    return relative.startswith("scripts/") or relative.startswith("tests/")


def has_meta_docstring(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    if content.startswith("#!"):
        _shebang, _newline, content = content.partition("\n")
    stripped = content.lstrip()
    return (
        stripped.startswith('"""\n@meta')
        or stripped.startswith("'''\n@meta")
        or stripped.startswith('"""')
        or stripped.startswith("'''")
    )


def collect_capability_ids(repo_root: Path) -> set[str]:
    capability_ids: set[str] = set()
    for source_path in sorted((repo_root / "docs" / "features").glob("*/feature.source.yaml")):
        payload = cast(dict[str, Any], read_yaml(source_path))
        for capability in cast(list[Any], payload.get("capabilities", [])):
            if not isinstance(capability, dict):
                continue
            capability_id = capability.get("capability_id")
            if isinstance(capability_id, str) and capability_id:
                capability_ids.add(capability_id)
    return capability_ids


def collect_phase_7_pilot_requirements(repo_root: Path) -> dict[str, dict[str, bool]]:
    adoption_path = repo_root / "repo_config" / "adoption-mode.yaml"
    if not adoption_path.exists():
        return {}
    payload = cast(dict[str, Any], read_yaml(adoption_path))
    pilot_payload = payload.get("phase_7_direct_evidence_pilot", {})
    if not isinstance(pilot_payload, dict):
        return {}
    capabilities_payload = pilot_payload.get("capabilities", {})
    if not isinstance(capabilities_payload, dict):
        return {}

    requirements: dict[str, dict[str, bool]] = {}
    for capability_id, rule_payload in capabilities_payload.items():
        if not isinstance(capability_id, str) or not isinstance(rule_payload, dict):
            continue
        requirements[capability_id] = {
            "require_code": bool(rule_payload.get("require_code", False)),
            "require_tests": bool(rule_payload.get("require_tests", False)),
        }
    return requirements


def load_sync_module(sync_script_path: Path):
    spec = importlib.util.spec_from_file_location("sync_architecture_docs", sync_script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load sync script from {sync_script_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_required_files(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_DOC_PATHS:
        target = repo_root / relative_path
        if not target.exists():
            errors.append(f"Missing required file: {relative_path}")
    return errors


def validate_python_file_metadata(repo_root: Path) -> list[str]:
    errors: list[str] = []
    known_capability_ids = collect_capability_ids(repo_root)
    for path in sorted(repo_root.rglob("*.py")):
        if not requires_python_metadata(path, repo_root):
            continue
        if not has_meta_docstring(path):
            errors.append(f"Missing required @meta docstring: {relpath(path, repo_root)}")
            continue
        content = path.read_text(encoding="utf-8")
        for capability_id in PROVES_PATTERN.findall(content):
            if capability_id not in known_capability_ids:
                errors.append(
                    f"Unknown @proves capability ID in {relpath(path, repo_root)}: {capability_id}"
                )
    return errors


def validate_feature_capability(feature_id: str, capability: dict[str, Any], owner: str, index: int) -> list[str]:
    errors: list[str] = []
    capability_id = capability.get("capability_id")
    statement = capability.get("statement")
    state = capability.get("state")
    if not isinstance(capability_id, str) or not capability_id:
        errors.append(f"Capability entry {index + 1} in {owner} must include capability_id.")
        return errors
    if not capability_id.startswith(f"{feature_id}."):
        errors.append(f"Capability ID must start with {feature_id}. in {owner}.")
    suffix = capability_id[len(feature_id) + 1 :] if capability_id.startswith(f"{feature_id}.") else ""
    if not CAPABILITY_SUFFIX_PATTERN.fullmatch(suffix):
        errors.append(f"Capability ID must use kebab-case suffixes in {owner}: {capability_id}")
    if not isinstance(statement, str) or not statement:
        errors.append(f"Capability entry {index + 1} in {owner} must include statement.")
    if not isinstance(state, str) or not state:
        errors.append(f"Capability entry {index + 1} in {owner} must include state.")
    return errors


def validate_feature_source(repo_root: Path, source_path: Path, lineage_path: Path) -> list[str]:
    errors: list[str] = []
    payload = cast(dict[str, Any], read_yaml(source_path))
    owner = relpath(source_path, repo_root)
    feature_id = cast(str, payload.get("feature_id", ""))
    if feature_id != source_path.parent.name:
        errors.append(f"Feature directory and feature_id must match: {owner}")
    if not FEATURE_ID_PATTERN.fullmatch(feature_id):
        errors.append(f"Invalid feature_id naming policy in {owner}: {feature_id}")

    unknown_keys = sorted(set(payload) - SOURCE_ALLOWED_KEYS)
    if unknown_keys:
        errors.append(f"Feature source has unsupported keys in {owner}: {', '.join(unknown_keys)}")

    capabilities = payload.get("capabilities", [])
    if not isinstance(capabilities, list):
        errors.append(f"Capabilities must be a list in {owner}.")
    else:
        for index, capability in enumerate(capabilities):
            if not isinstance(capability, dict):
                errors.append(f"Managed features must use structured capability entries in {owner}.")
                continue
            errors.extend(validate_feature_capability(feature_id, capability, owner, index))

    if lineage_path.exists():
        raw_lineage = lineage_path.read_text(encoding="utf-8")
        if LINEAGE_ALIAS_PATTERN.search(raw_lineage):
            errors.append(
                f"YAML aliases are not allowed in {relpath(lineage_path, repo_root)}."
            )
            return errors
        try:
            lineage = cast(dict[str, Any], yaml.safe_load(raw_lineage))
        except yaml.YAMLError:
            errors.append(f"Invalid YAML in {relpath(lineage_path, repo_root)}.")
            return errors
        required_keys = {"feature_id", "source", "invariants", "capabilities", "timeline"}
        missing_keys = sorted(key for key in required_keys if key not in lineage)
        if missing_keys:
            errors.append(
                f"Feature lineage is missing required keys in {relpath(lineage_path, repo_root)}: {', '.join(missing_keys)}"
            )
        present_forbidden_keys = sorted(key for key in FORBIDDEN_LINEAGE_KEYS if key in lineage)
        if present_forbidden_keys:
            errors.append(
                f"Legacy lineage keys are not allowed in {relpath(lineage_path, repo_root)}: {', '.join(present_forbidden_keys)}"
            )
        if "capabilities" in lineage and not isinstance(lineage["capabilities"], dict):
            errors.append(
                f"Feature lineage capabilities must be a mapping in {relpath(lineage_path, repo_root)}."
            )
        if "timeline" in lineage and not isinstance(lineage["timeline"], list):
            errors.append(
                f"Feature lineage timeline must be a list in {relpath(lineage_path, repo_root)}."
            )
        capabilities_lineage = lineage.get("capabilities", {})
        if isinstance(capabilities_lineage, dict):
            for capability_id, capability_lineage in capabilities_lineage.items():
                if not isinstance(capability_lineage, dict):
                    errors.append(
                        f"Feature lineage entry must be a mapping for {capability_id} in {relpath(lineage_path, repo_root)}."
                    )
                    continue
                for field in LINEAGE_EVIDENCE_FIELDS:
                    evidence_paths = capability_lineage.get(field, [])
                    if not isinstance(evidence_paths, list):
                        errors.append(
                            f"Lineage field {field} must be a list for {capability_id} in {relpath(lineage_path, repo_root)}."
                        )
                        continue
                    for evidence_path in evidence_paths:
                        if not isinstance(evidence_path, str):
                            errors.append(
                                f"Lineage field {field} must contain string paths for {capability_id} in {relpath(lineage_path, repo_root)}."
                            )
                            continue
                        if not (repo_root / evidence_path).exists():
                            errors.append(
                                f"Lineage path does not exist for {capability_id} in {relpath(lineage_path, repo_root)}: {evidence_path}"
                            )
                if capability_lineage.get("completeness_status") == "complete":
                    code_paths = capability_lineage.get("code", [])
                    test_paths = capability_lineage.get("tests", [])
                    if not code_paths and not test_paths:
                        errors.append(
                            f"Complete lineage claims require direct code or test evidence in {relpath(lineage_path, repo_root)} for {capability_id}."
                        )
    return errors


def validate_features(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for feature_dir in sorted((repo_root / "docs" / "features").iterdir()):
        if not feature_dir.is_dir():
            continue
        feature_id = feature_dir.name
        source_path = feature_dir / "feature.source.yaml"
        contract_path = feature_dir / f"{feature_id}.yaml"
        lineage_path = feature_dir / "lineage.generated.yaml"
        history_path = feature_dir / "history.md"
        if not source_path.exists():
            errors.append(f"Missing feature source: {relpath(source_path, repo_root)}")
        if not contract_path.exists():
            errors.append(f"Missing feature contract: {relpath(contract_path, repo_root)}")
        if not lineage_path.exists():
            errors.append(f"Missing feature lineage: {relpath(lineage_path, repo_root)}")
        if not history_path.exists():
            errors.append(f"Missing feature history: {relpath(history_path, repo_root)}")
        if source_path.exists():
            errors.extend(validate_feature_source(repo_root, source_path, lineage_path))
    return errors


def validate_stages(repo_root: Path) -> list[str]:
    errors: list[str] = []
    stage_dir = repo_root / "docs" / "stages"
    stage_ids: set[str] = set()
    for contract_path in sorted(stage_dir.glob("*.yaml")):
        if contract_path.name.endswith(".source.yaml"):
            continue
        stage_ids.add(contract_path.stem)
    for source_path in sorted(stage_dir.glob("*.source.yaml")):
        stage_ids.add(source_path.name.replace(".source.yaml", ""))
    for stage_id in sorted(stage_ids):
        source_path = stage_dir / f"{stage_id}.source.yaml"
        contract_path = stage_dir / f"{stage_id}.yaml"
        if not source_path.exists():
            errors.append(f"Missing stage source: {relpath(source_path, repo_root)}")
        if not contract_path.exists():
            errors.append(f"Missing stage contract: {relpath(contract_path, repo_root)}")
    return errors


def validate_adoption_mode(repo_root: Path) -> list[str]:
    adoption_path = repo_root / "repo_config" / "adoption-mode.yaml"
    errors: list[str] = []
    if not adoption_path.exists():
        return ["Missing required file: repo_config/adoption-mode.yaml"]

    payload = cast(dict[str, Any], read_yaml(adoption_path))
    if payload.get("adoption_mode") != "managed_architecture_metadata":
        errors.append("adoption_mode must be `managed_architecture_metadata`.")
    if payload.get("managed_architecture_metadata") is not True:
        errors.append("managed_architecture_metadata must be true.")
    if payload.get("architecture_generator") != "scripts/sync_architecture_docs.py":
        errors.append("architecture_generator must be `scripts/sync_architecture_docs.py`.")

    starter_sync = cast(dict[str, Any], payload.get("starter_sync", {}))
    if not starter_sync.get("starter_baseline_ref"):
        errors.append("starter_sync.starter_baseline_ref is required.")
    if not starter_sync.get("last_shared_surface_review_at"):
        errors.append("starter_sync.last_shared_surface_review_at is required.")
    known_capability_ids = collect_capability_ids(repo_root)
    pilot_payload = payload.get("phase_7_direct_evidence_pilot")
    if pilot_payload is not None:
        if not isinstance(pilot_payload, dict):
            errors.append("phase_7_direct_evidence_pilot must be a mapping when present.")
        else:
            capabilities_payload = pilot_payload.get("capabilities", {})
            if not isinstance(capabilities_payload, dict):
                errors.append("phase_7_direct_evidence_pilot.capabilities must be a mapping.")
            else:
                for capability_id, rule_payload in capabilities_payload.items():
                    if not isinstance(capability_id, str):
                        errors.append("phase_7_direct_evidence_pilot capability IDs must be strings.")
                        continue
                    if capability_id not in known_capability_ids:
                        errors.append(
                            f"phase_7_direct_evidence_pilot references unknown capability: {capability_id}"
                        )
                    if not isinstance(rule_payload, dict):
                        errors.append(
                            f"phase_7_direct_evidence_pilot rules must be a mapping for {capability_id}."
                        )
                        continue
                    for field in ("require_code", "require_tests"):
                        if field in rule_payload and not isinstance(rule_payload[field], bool):
                            errors.append(
                                f"phase_7_direct_evidence_pilot.{capability_id}.{field} must be a boolean."
                            )
    return errors


def validate_phase_7_direct_evidence_pilot(repo_root: Path) -> list[str]:
    errors: list[str] = []
    requirements = collect_phase_7_pilot_requirements(repo_root)
    if not requirements:
        return errors

    for capability_id, requirement in sorted(requirements.items()):
        feature_id, _separator, _suffix = capability_id.partition(".")
        lineage_path = repo_root / "docs" / "features" / feature_id / "lineage.generated.yaml"
        if not lineage_path.exists():
            errors.append(
                f"Missing feature lineage for phase_7_direct_evidence_pilot capability: {capability_id}"
            )
            continue
        raw_lineage = lineage_path.read_text(encoding="utf-8")
        if LINEAGE_ALIAS_PATTERN.search(raw_lineage):
            errors.append(f"YAML aliases are not allowed in {relpath(lineage_path, repo_root)}.")
            continue
        try:
            lineage_payload = cast(dict[str, Any], yaml.safe_load(raw_lineage))
        except yaml.YAMLError:
            errors.append(f"Invalid YAML in {relpath(lineage_path, repo_root)}.")
            continue
        capabilities = lineage_payload.get("capabilities", {})
        if not isinstance(capabilities, dict):
            errors.append(
                f"Feature lineage capabilities must be a mapping for phase_7_direct_evidence_pilot capability: {capability_id}"
            )
            continue
        capability_lineage = capabilities.get(capability_id)
        if not isinstance(capability_lineage, dict):
            errors.append(
                f"Missing capability lineage for phase_7_direct_evidence_pilot capability: {capability_id}"
            )
            continue
        code_paths = capability_lineage.get("code", [])
        test_paths = capability_lineage.get("tests", [])
        if requirement.get("require_code") and not code_paths:
            errors.append(
                f"phase_7_direct_evidence_pilot requires code evidence for {capability_id}."
            )
        if requirement.get("require_tests") and not test_paths:
            errors.append(
                f"phase_7_direct_evidence_pilot requires test evidence for {capability_id}."
            )
    return errors


def validate_sync_freshness(repo_root: Path) -> list[str]:
    sync_script_path = repo_root / "scripts" / "sync_architecture_docs.py"
    if not sync_script_path.exists():
        return ["Missing required file: scripts/sync_architecture_docs.py"]

    sync_module = load_sync_module(sync_script_path)
    exit_code = sync_module.main(["--repo-root", str(repo_root), "--check"])
    if exit_code != 0:
        return ["Generated architecture docs are stale. Run scripts/sync_architecture_docs.py."]
    return []


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()

    errors: list[str] = []
    errors.extend(validate_required_files(repo_root))
    errors.extend(validate_python_file_metadata(repo_root))
    errors.extend(validate_features(repo_root))
    errors.extend(validate_stages(repo_root))
    errors.extend(validate_adoption_mode(repo_root))
    errors.extend(validate_phase_7_direct_evidence_pilot(repo_root))
    if not errors:
        errors.extend(validate_sync_freshness(repo_root))

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Mode B adoption shape is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

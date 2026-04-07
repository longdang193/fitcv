#!/usr/bin/env python3
"""
Generate cross-feature and stage views from docs/features/*/*.yaml and docs/stages/*.yaml.

Run this whenever a feature YAML changes:
    python .cursor/rules/operating-system/generate_features.py

Outputs (all derived — do not edit manually):
    docs/generated/features_index.yaml
    docs/generated/feature_overview.md
    docs/generated/feature_dependency_graph.yaml
    docs/generated/feature_capabilities_index.yaml
    docs/generated/features_by_status.yaml
    docs/generated/stages_index.yaml
    docs/generated/stage_overview.md
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FeatureStatus(str, Enum):
    PLANNED = "planned"
    BUILDING = "building"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class FeatureType(str, Enum):
    ADD = "add"
    MODIFY = "modify"
    REPLACE = "replace"
    DEPRECATE = "deprecate"


# ---------------------------------------------------------------------------
# Refs model (nested under feature YAML)
# ---------------------------------------------------------------------------

class FeatureRefs(BaseModel):
    docs: list[str] = Field(default_factory=list)
    spec: list[str] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)


class StageRefs(BaseModel):
    docs: list[str] = Field(default_factory=list)
    spec: list[str] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Core feature model
# ---------------------------------------------------------------------------

class Feature(BaseModel):
    """Validated, normalised representation of one feature YAML."""

    feature_id: str
    name: str
    version: str
    status: FeatureStatus = FeatureStatus.PLANNED
    type: FeatureType = FeatureType.ADD
    summary: str = ""
    owner: str = ""

    domains: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)

    capabilities: list[str] = Field(default_factory=list)
    refs: FeatureRefs = Field(default_factory=FeatureRefs)
    keywords: list[str] = Field(default_factory=list)

    # Populated at load time — not in YAML
    contract_path: str = ""
    history_path: str = ""

    @field_validator("version")
    @classmethod
    def version_must_be_semver(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"version '{v}' is not semver (x.y.z)")
        return v

    @model_validator(mode="before")
    @classmethod
    def _unwrap_root_key(cls, data: dict) -> dict:
        """Handle YAML files where the feature_id is the root key.

        Example:
            admin_control_plane_core:
              name: Admin Control Plane Core
              ...

        Unwraps into a flat dict with feature_id injected.
        """
        if len(data) == 1:
            root_key = next(iter(data))
            inner = data[root_key]
            if isinstance(inner, dict):
                inner["feature_id"] = root_key
                return inner
        return data


class Stage(BaseModel):
    """Validated, normalised representation of one stage YAML."""

    stage_id: str
    name: str
    summary: str = ""
    boundaries: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    primary_features: list[str] = Field(default_factory=list)
    related_features: list[str] = Field(default_factory=list)
    refs: StageRefs = Field(default_factory=StageRefs)
    keywords: list[str] = Field(default_factory=list)

    contract_path: str = ""

    @model_validator(mode="before")
    @classmethod
    def _unwrap_root_key(cls, data: dict) -> dict:
        if len(data) == 1:
            root_key = next(iter(data))
            inner = data[root_key]
            if isinstance(inner, dict):
                inner["stage_id"] = root_key
                return inner
        return data


# ---------------------------------------------------------------------------
# Output: features_index.yaml
# ---------------------------------------------------------------------------

def generate_features_index(features: list[Feature]) -> str:
    """Generate features_index.yaml matching the current format."""
    lines = [
        "# Generated Discovery — Do not edit manually",
        "# Source: docs/features/*/*.yaml",
        "# Regenerate when any feature YAML changes",
        "",
        "features:",
    ]
    for f in features:
        lines.append(f"  - feature_id: {f.feature_id}")
        lines.append(f"    version: {f.version}")
        lines.append(f"    status: {f.status.value}")
        lines.append(f"    type: {f.type.value}")
        lines.append(f"    owner: {f.owner}")
        lines.append(f"    domains: [{', '.join(f.domains)}]")
        lines.append(f"    contract: {f.contract_path}")
        lines.append(f"    history: {f.history_path}")
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Output: feature_overview.md
# ---------------------------------------------------------------------------

STATUS_ORDER = ["active", "building", "planned", "deprecated", "retired"]

STATUS_LEGEND = {
    "planned": "concept exists; entry created with invariants and domains",
    "building": "implementation underway",
    "active": "post-execution review complete",
    "deprecated": "replaced or removed",
}


def _build_dependency_tree(features: list[Feature]) -> str:
    """Build a text dependency tree for the overview.

    Output format matches the manually-authored reference:
        admin_control_plane_core
        ├── trigger_run_management
        │   └── multi_file_job_input
        ├── inspection_debugging
        └── ui_consistency_theming
    """
    # Build parent→children map from depends_on (inverse).
    # If feature X depends_on Y, then Y is X's parent → Y has child X.
    children_of: dict[str, list[str]] = defaultdict(list)
    all_ids = {f.feature_id for f in features}
    has_parent: set[str] = set()

    for f in features:
        for dep in f.depends_on:
            if dep in all_ids:
                children_of[dep].append(f.feature_id)
                has_parent.add(f.feature_id)

    # Sort children for deterministic output
    for k in children_of:
        children_of[k].sort()

    # Roots: features with no parent
    roots = sorted(fid for fid in all_ids if fid not in has_parent)

    def render(node: str, prefix: str = "") -> list[str]:
        kids = children_of.get(node, [])
        lines_out: list[str] = []
        for i, child in enumerate(kids):
            is_last = i == len(kids) - 1
            connector = "└── " if is_last else "├── "
            lines_out.append(f"{prefix}{connector}{child}")
            extension = "    " if is_last else "│   "
            lines_out.extend(render(child, prefix + extension))
        return lines_out

    tree_lines: list[str] = []
    for root in roots:
        tree_lines.append(root)
        tree_lines.extend(render(root))
        tree_lines.append("")

    return "\n".join(tree_lines).rstrip()


def generate_feature_overview_md(features: list[Feature]) -> str:
    """Generate feature_overview.md matching the current format."""
    lines = [
        "# Feature Overview",
        "",
        "> Generated — do not edit manually. Source: `docs/features/*/*.yaml`",
    ]

    # Group by status
    by_status: dict[str, list[Feature]] = defaultdict(list)
    for f in features:
        by_status[f.status.value].append(f)

    for status in STATUS_ORDER:
        group = by_status.get(status, [])
        if not group:
            continue

        lines.append("")
        lines.append(f"## {status.capitalize()}")
        lines.append("")
        lines.append("| Feature | Version | Type | Owner | Summary |")
        lines.append("|---|---|---|---|---|")
        for f in sorted(group, key=lambda x: x.feature_id):
            lines.append(
                f"| `{f.feature_id}` | {f.version} | {f.type.value} "
                f"| {f.owner} | {f.summary} |"
            )

    # Dependency graph
    tree = _build_dependency_tree(features)
    if tree:
        lines.append("")
        lines.append("## Dependency Graph")
        lines.append("")
        lines.append("```text")
        lines.append(tree)
        lines.append("```")

    # Status legend
    lines.append("")
    lines.append("## Status Legend")
    lines.append("")
    for status, meaning in STATUS_LEGEND.items():
        lines.append(f"- **{status}** — {meaning}")

    # Feature contracts section
    lines.append("")
    lines.append("## Feature Contracts")
    lines.append("")
    lines.append("Each feature has a contract at `docs/features/<feature_id>.yaml` and optional focused docs under `docs/features/<feature_id>/`:")
    lines.append("")
    lines.append("```text")
    lines.append("docs/features/<feature_id>.yaml")
    lines.append("docs/features/<feature_id>/history.md")
    lines.append("```")
    lines.append("")
    lines.append("For the machine-friendly index, see `docs/generated/features_index.yaml`.")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Output: feature_dependency_graph.yaml
# ---------------------------------------------------------------------------

def generate_dependency_graph_yaml(features: list[Feature]) -> str:
    """Generate feature_dependency_graph.yaml."""
    all_ids = {f.feature_id for f in features}
    # Build used_by (inverse of depends_on)
    used_by: dict[str, list[str]] = defaultdict(list)
    for f in features:
        for dep in f.depends_on:
            if dep in all_ids:
                used_by[dep].append(f.feature_id)

    graph: dict[str, dict[str, list[str]]] = {}
    for f in features:
        graph[f.feature_id] = {
            "depends_on": sorted(f.depends_on),
            "used_by": sorted(used_by.get(f.feature_id, [])),
        }

    data = {
        "graph": dict(sorted(graph.items())),
        "orphans": {
            "no_dependencies": sorted(
                fid for fid, v in graph.items() if not v["depends_on"]
            ),
            "no_dependents": sorted(
                fid for fid, v in graph.items() if not v["used_by"]
            ),
        },
        "_meta": {
            "generated_by": "generate_features.py",
            "note": "depends_on / used_by are canonical edges. "
                    "Inverse (used_by) are derived from depends_on.",
        },
    }
    return yaml.dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


# ---------------------------------------------------------------------------
# Output: feature_capabilities_index.yaml
# ---------------------------------------------------------------------------

def generate_capabilities_index_yaml(features: list[Feature]) -> str:
    """Generate feature_capabilities_index.yaml."""
    capabilities: list[dict[str, str]] = []
    keyword_map: dict[str, list[str]] = defaultdict(list)

    for f in features:
        for cap in f.capabilities:
            capabilities.append({"capability": cap, "feature_id": f.feature_id})
        for kw in f.keywords:
            keyword_map[kw.lower()].append(f.feature_id)

    data = {
        "capabilities": sorted(capabilities, key=lambda x: x["capability"]),
        "keywords": {k: sorted(set(v)) for k, v in sorted(keyword_map.items())},
        "_meta": {
            "generated_by": "generate_features.py",
            "note": "capabilities are verbatim from feature YAMLs; "
                    "keywords are from feature keywords fields.",
        },
    }
    return yaml.dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


# ---------------------------------------------------------------------------
# Output: features_by_status.yaml
# ---------------------------------------------------------------------------

def generate_by_status_yaml(features: list[Feature]) -> str:
    """Generate features_by_status.yaml."""
    by_status: dict[str, list[str]] = defaultdict(list)
    for f in features:
        by_status[f.status.value].append(f.feature_id)

    data = {
        status: sorted(by_status.get(status, []))
        for status in STATUS_ORDER
    }
    data["_meta"] = {
        "generated_by": "generate_features.py",
        "note": f"status_order: {STATUS_ORDER}",
    }
    return yaml.dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


# ---------------------------------------------------------------------------
# Output: stages_index.yaml
# ---------------------------------------------------------------------------

def generate_stages_index(stages: list[Stage]) -> str:
    """Generate stages_index.yaml."""
    lines = [
        "# Generated Discovery — Do not edit manually",
        "# Source: docs/stages/*.yaml",
        "# Regenerate when any stage YAML changes",
        "",
        "stages:",
    ]
    for s in stages:
        lines.append(f"  - stage_id: {s.stage_id}")
        lines.append(f"    name: {s.name}")
        lines.append(f"    depends_on: [{', '.join(s.depends_on)}]")
        lines.append(f"    primary_features: [{', '.join(s.primary_features)}]")
        lines.append(f"    related_features: [{', '.join(s.related_features)}]")
        lines.append(f"    contract: {s.contract_path}")
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Output: stage_overview.md
# ---------------------------------------------------------------------------

def generate_stage_overview_md(stages: list[Stage]) -> str:
    """Generate stage_overview.md."""
    lines = [
        "# Stage Overview",
        "",
        "> Generated — do not edit manually. Source: `docs/stages/*.yaml`",
        "",
    ]

    if not stages:
        lines.append("No active stage contracts are currently defined.")
        return "\n".join(lines) + "\n"

    lines.append("| Stage | Depends On | Primary Features | Summary |")
    lines.append("|---|---|---|---|")
    for s in sorted(stages, key=lambda x: x.stage_id):
        depends = ", ".join(f"`{dep}`" for dep in s.depends_on) if s.depends_on else "—"
        primary = ", ".join(f"`{fid}`" for fid in s.primary_features) if s.primary_features else "—"
        lines.append(
            f"| `{s.stage_id}` | {depends} | {primary} | {s.summary} |"
        )

    lines.append("")
    lines.append("## Stage Contracts")
    lines.append("")
    lines.append("Each stage has a contract at `docs/stages/<stage_id>.yaml`:")
    lines.append("")
    lines.append("```text")
    lines.append("docs/stages/<stage_id>.yaml")
    lines.append("```")
    lines.append("")
    lines.append("For the machine-friendly index, see `docs/generated/stages_index.yaml`.")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Validation (beyond Pydantic)
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    pass


def validate_all(features: list[Feature], root: Path) -> None:
    errors: list[str] = []
    ids_seen: set[str] = set()
    all_ids = {f.feature_id for f in features}

    for f in features:
        if f.feature_id in ids_seen:
            errors.append(f"DUPLICATE feature_id: {f.feature_id}")
        ids_seen.add(f.feature_id)

        for dep in f.depends_on:
            if dep not in all_ids:
                errors.append(
                    f"[{f.feature_id}] depends_on '{dep}' "
                    f"but no feature with that id exists"
                )

        for hist in f.refs.history:
            history_path = root / hist
            if not history_path.exists():
                errors.append(
                    f"[{f.feature_id}] refs.history '{hist}' "
                    f"does not exist on disk"
                )

    if errors:
        raise ValidationError("\n".join(errors))


def validate_stages(stages: list[Stage], root: Path) -> None:
    errors: list[str] = []
    ids_seen: set[str] = set()

    for s in stages:
        if s.stage_id in ids_seen:
            errors.append(f"DUPLICATE stage_id: {s.stage_id}")
        ids_seen.add(s.stage_id)

        for hist in s.refs.history:
            history_path = root / hist
            if not history_path.exists():
                errors.append(
                    f"[{s.stage_id}] refs.history '{hist}' does not exist on disk"
                )

    if errors:
        raise ValidationError("\n".join(errors))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[3]  # .cursor/rules/operating-system -> project root
FEATURES_DIR = ROOT / "docs" / "features"
STAGES_DIR = ROOT / "docs" / "stages"
GENERATED_DIR = ROOT / "docs" / "generated"


def _to_repo_relative(path: Path) -> str:
    """Return a repo-relative path with stable forward slashes."""
    return str(path.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    # Glob: docs/features/*/*.yaml
    feature_files = sorted(FEATURES_DIR.glob("*/*.yaml"))
    if not feature_files:
        print(
            "WARNING: no feature YAML files found in docs/features/*/",
            file=sys.stderr,
        )
        return 0

    features: list[Feature] = []
    for path in feature_files:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        model = Feature.model_validate(raw)
        model.contract_path = _to_repo_relative(path)
        model.history_path = _to_repo_relative(path.parent / "history.md")
        features.append(model)

    validate_all(features, ROOT)

    stages: list[Stage] = []
    for path in sorted(STAGES_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        model = Stage.model_validate(raw)
        model.contract_path = _to_repo_relative(path)
        stages.append(model)

    validate_stages(stages, ROOT)

    outputs = [
        ("features_index.yaml", generate_features_index(features)),
        ("feature_overview.md", generate_feature_overview_md(features)),
        ("feature_dependency_graph.yaml", generate_dependency_graph_yaml(features)),
        ("feature_capabilities_index.yaml", generate_capabilities_index_yaml(features)),
        ("features_by_status.yaml", generate_by_status_yaml(features)),
        ("stages_index.yaml", generate_stages_index(stages)),
        ("stage_overview.md", generate_stage_overview_md(stages)),
    ]

    for filename, content in outputs:
        out_path = GENERATED_DIR / filename
        out_path.write_text(content, encoding="utf-8")
        print(f"  wrote {out_path.relative_to(ROOT)}")

    print(
        f"\nGenerated {len(outputs)} files for {len(features)} features and "
        f"{len(stages)} stages."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

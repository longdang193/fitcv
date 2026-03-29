#!/usr/bin/env python3
"""
Generate cross-feature views from features/*.yaml.

Run this whenever a feature YAML changes:
    python scripts/docs/generate_features.py

Outputs (all derived — do not edit manually):
    docs/generated/features_index.yaml
    docs/generated/feature_overview.md
    docs/generated/feature_dependency_graph.yaml
    docs/generated/feature_file_map.yaml
    docs/generated/feature_capabilities_index.yaml
    docs/generated/features_by_status.yaml
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
    law: str = ""
    owner: str = ""

    domains: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    used_by: list[str] = Field(default_factory=list)

    files: list[str] = Field(default_factory=list)
    routes: list[str] = Field(default_factory=list)

    capabilities: list[str] = Field(default_factory=list)
    spec_refs: list[str] = Field(default_factory=list)
    plan_refs: list[str] = Field(default_factory=list)
    discovery_keywords: list[str] = Field(default_factory=list)

    history_ref: str = ""

    # Populated at load time — not in YAML
    path: str = ""

    @field_validator("version")
    @classmethod
    def version_must_be_semver(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"version '{v}' is not semver (x.y.z)")
        return v

    @model_validator(mode="before")
    @classmethod
    def _coerce_implementation_and_entrypoints(cls, data: dict) -> dict:
        impl = data.get("implementation", {})
        if isinstance(impl, dict):
            data["files"] = impl.get("files", [])

        ep = data.get("entrypoints", {})
        if isinstance(ep, dict):
            data["routes"] = ep.get("routes", [])

        return data


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class Meta(BaseModel):
    generated_by: str = "scripts/docs/generate_features.py"
    note: str = ""


class FeatureSummaryEntry(BaseModel):
    feature_id: str
    name: str
    version: str
    status: FeatureStatus
    type: FeatureType
    owner: str
    path: str


class FeaturesIndex(BaseModel):
    features: list[FeatureSummaryEntry]
    _meta: Meta

    @classmethod
    def from_features(cls, features: list[Feature]) -> "FeaturesIndex":
        return cls(
            features=[
                FeatureSummaryEntry(
                    feature_id=f.feature_id,
                    name=f.name,
                    version=f.version,
                    status=f.status,
                    type=f.type,
                    owner=f.owner,
                    path=f.path,
                )
                for f in features
            ],
            _meta=Meta(generated_by="scripts/docs/generate_features.py", count=len(features)),
        )


class DependencyGraph(BaseModel):
    graph: dict[str, dict[str, list[str]]]
    orphans: dict[str, list[str]]
    _meta: Meta

    @classmethod
    def from_features(cls, features: list[Feature]) -> "DependencyGraph":
        all_ids = {f.feature_id for f in features}
        graph: dict[str, dict[str, list[str]]] = {}
        for f in features:
            graph[f.feature_id] = {
                "depends_on": sorted(f.depends_on),
                "used_by": sorted(f.used_by),
            }
        return cls(
            graph=dict(sorted(graph.items())),
            orphans={
                "no_dependencies": sorted([fid for fid, v in graph.items() if not v["depends_on"]]),
                "no_dependents": sorted([fid for fid, v in graph.items() if not v["used_by"]]),
            },
            _meta=Meta(
                generated_by="scripts/docs/generate_features.py",
                note="depends_on / used_by are canonical edges. Inverse (used_by) are derived.",
            ),
        )


class FileMapEntry(BaseModel):
    owned_by: list[str]


class FileMap(BaseModel):
    files: dict[str, FileMapEntry]
    _index: dict[str, int]
    _meta: Meta

    @classmethod
    def from_features(cls, features: list[Feature]) -> "FileMap":
        file_to_owners: dict[str, list[str]] = defaultdict(list)
        for f in features:
            for file in f.files:
                file_to_owners[file].append(f.feature_id)
        sorted_map = dict(sorted(file_to_owners.items()))
        return cls(
            files={k: FileMapEntry(owned_by=sorted(v)) for k, v in sorted_map.items()},
            _index={"total_files": len(sorted_map), "total_features": len(features)},
            _meta=Meta(
                generated_by="scripts/docs/generate_features.py",
                note="One source file may be owned by multiple features.",
            ),
        )


class CapabilityEntry(BaseModel):
    capability: str
    feature_id: str


class CapabilitiesIndex(BaseModel):
    capabilities: list[CapabilityEntry]
    keywords: dict[str, list[str]]
    _meta: Meta

    @classmethod
    def from_features(cls, features: list[Feature]) -> "CapabilitiesIndex":
        capability_entries: list[CapabilityEntry] = []
        keyword_map: dict[str, list[str]] = defaultdict(list)

        for f in features:
            for cap in f.capabilities:
                capability_entries.append(CapabilityEntry(capability=cap, feature_id=f.feature_id))
            for kw in f.discovery_keywords:
                keyword_map[kw.lower()].append(f.feature_id)

        aliases: dict[str, list[str]] = {
            "filter": ["pipeline_performance", "inspection_debugging"],
            "cv": ["cv_system", "trigger_run_management"],
            "enrichment": ["pipeline_performance", "bounded_parallel_enrichment"],
            "settings": ["settings_system", "cv_system", "pipeline_performance"],
            "cancel": ["run_lifecycle_controls"],
            "archive": ["run_lifecycle_controls"],
            "ui": ["ui_consistency_theming", "inspection_debugging", "trigger_run_management"],
            "performance": ["pipeline_performance", "bounded_parallel_enrichment"],
        }
        for alias, fids in aliases.items():
            if alias not in keyword_map:
                keyword_map[alias] = sorted(set(fids))

        return cls(
            capabilities=sorted(capability_entries, key=lambda x: x.capability),
            keywords={k: sorted(set(v)) for k, v in sorted(keyword_map.items())},
            _meta=Meta(
                generated_by="scripts/docs/generate_features.py",
                note="capabilities are verbatim from feature YAMLs; keywords include aliases.",
            ),
        )


class FeaturesByStatus(BaseModel):
    planned: list[str] = Field(default_factory=list)
    building: list[str] = Field(default_factory=list)
    active: list[str] = Field(default_factory=list)
    deprecated: list[str] = Field(default_factory=list)
    retired: list[str] = Field(default_factory=list)
    _meta: Meta

    @classmethod
    def from_features(cls, features: list[Feature]) -> "FeaturesByStatus":
        by_status: dict[str, list[str]] = defaultdict(list)
        order = ["planned", "building", "active", "deprecated", "retired"]
        for f in features:
            by_status[f.status.value].append(f.feature_id)
        return cls(
            **{status: sorted(by_status.get(status, [])) for status in order},
            _meta=Meta(generated_by="scripts/docs/generate_features.py", note=f"status_order: {order}"),
        )


# ---------------------------------------------------------------------------
# YAML helpers (PyYAML)
# ---------------------------------------------------------------------------

def yaml_dump(model: BaseModel) -> str:
    """Serialize a Pydantic model to a YAML string."""
    return yaml.dump(
        model.model_dump(mode="json"),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


# ---------------------------------------------------------------------------
# Markdown generators
# ---------------------------------------------------------------------------

def generate_feature_overview_md(features: list[Feature]) -> str:
    lines = [
        "# Generated Feature Overview",
        "",
        "> **Auto-generated from `features/*.yaml`. Do not edit manually.**",
        "> Run `python scripts/docs/generate_features.py` after changing a feature YAML.",
        "",
        "## Legend",
        "",
        "| Status | Meaning |",
        "|---|---|",
        "| `planned` | Triaged, spec written |",
        "| `building` | Implementation in progress |",
        "| `active` | Deployed and in use |",
        "| `deprecated` | Replaced; avoid new usage |",
        "| `retired` | No longer used |",
        "",
        "## Feature Summary",
        "",
        "| Feature | Version | Type | Status | Owner | Path |",
        "|---|---:|---|---|---|---|",
    ]
    for f in sorted(features, key=lambda x: x.name):
        lines.append(
            f"| {f.name} | {f.version} | {f.type.value} | {f.status.value} | {f.owner} | `{f.path}` |"
        )

    lines += [
        "",
        "## Feature Details",
        "",
        *(f"- [{f.name}](../{f.path})" for f in sorted(features, key=lambda x: x.name)),
        "",
        "## Architectural Decisions",
        "",
        "See [`docs/decisions/`](docs/decisions/) for the authoritative ADR index.",
    ]
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
                errors.append(f"[{f.feature_id}] depends_on '{dep}' but no feature with that id exists")

        if f.history_ref:
            history_path = root / f.history_ref
            if not history_path.exists():
                errors.append(f"[{f.feature_id}] history_ref '{f.history_ref}' does not exist on disk")

    if errors:
        raise ValidationError("\n".join(errors))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = ROOT / "features"
GENERATED_DIR = ROOT / "docs" / "generated"


def main() -> int:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    feature_files = sorted(FEATURES_DIR.glob("*.yaml"))
    if not feature_files:
        print("WARNING: no feature YAML files found in features/", file=sys.stderr)
        return 0

    features: list[Feature] = []
    for path in feature_files:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        model = Feature.model_validate(raw)
        model.path = str(path.relative_to(ROOT))
        features.append(model)

    validate_all(features, ROOT)

    index = FeaturesIndex.from_features(features)
    dep_graph = DependencyGraph.from_features(features)
    file_map = FileMap.from_features(features)
    cap_index = CapabilitiesIndex.from_features(features)
    by_status = FeaturesByStatus.from_features(features)

    outputs = [
        ("features_index.yaml", yaml_dump(index)),
        ("feature_overview.md", generate_feature_overview_md(features)),
        ("feature_dependency_graph.yaml", yaml_dump(dep_graph)),
        ("feature_file_map.yaml", yaml_dump(file_map)),
        ("feature_capabilities_index.yaml", yaml_dump(cap_index)),
        ("features_by_status.yaml", yaml_dump(by_status)),
    ]

    for filename, content in outputs:
        out_path = GENERATED_DIR / filename
        out_path.write_text(content, encoding="utf-8")
        print(f"  wrote {out_path.relative_to(ROOT)}")

    print(f"\nGenerated {len(outputs)} files for {len(features)} features.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

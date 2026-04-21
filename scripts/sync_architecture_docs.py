"""
@meta
name: sync_architecture_docs
type: script
domain: docs
responsibility:
  - Refresh managed feature and stage contracts from source files.
  - Regenerate lineage and discovery outputs for the Mode B architecture-doc layer.
  - Detect stale generated architecture outputs when run in check mode.
inputs:
  - docs/features/*/feature.source.yaml
  - docs/stages/*.source.yaml
  - docs/features/*/*.yaml
  - docs/stages/*.yaml
outputs:
  - docs/features/*/<feature_id>.yaml
  - docs/features/*/lineage.generated.yaml
  - docs/stages/<stage_id>.yaml
  - docs/generated/features_index.yaml
  - docs/generated/feature_dependency_graph.yaml
  - docs/generated/feature_capabilities_index.yaml
  - docs/generated/feature_overview.md
  - docs/generated/features_by_status.yaml
  - docs/generated/stages_index.yaml
  - docs/generated/stage_overview.md
tags:
  - docs
  - architecture
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Any, NamedTuple, cast

import yaml


FEATURES_INDEX_HEADER = """# Generated Discovery — Do not edit manually
# Source: docs/features/*/feature.source.yaml and docs/features/*/<feature_id>.yaml
# Regenerate with scripts/sync_architecture_docs.py
"""

STAGES_INDEX_HEADER = """# Generated Discovery — Do not edit manually
# Source: docs/stages/*.source.yaml and docs/stages/*.yaml
# Regenerate with scripts/sync_architecture_docs.py
"""

FEATURE_OVERVIEW_HEADER = """# Feature Overview

> Generated — do not edit manually. Source: `docs/features/*/feature.source.yaml`
"""

STAGE_OVERVIEW_HEADER = """# Stage Overview

> Generated — do not edit manually. Source: `docs/stages/*.source.yaml`
"""

STATUS_ORDER = ["active", "building", "planned", "deprecated", "retired"]


class RenderedFile(NamedTuple):
    path: Path
    content: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync architecture docs from source files.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to this script's repo.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale generated files instead of writing them.",
    )
    return parser.parse_args(argv)


def read_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(payload: object) -> str:
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=False, width=1000)


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def normalize_text(content: str) -> str:
    return content.replace("\r\n", "\n").rstrip() + "\n"


def slugify_capability_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "capability"


def naming_policy() -> dict[str, object]:
    return {
        "feature_id_format": "underscore",
        "capability_id_format": "<feature_id>.<kebab-suffix>",
        "string_capabilities_allowed": False,
    }


def feature_source_paths(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "docs" / "features").glob("*/feature.source.yaml"))


def stage_source_paths(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "docs" / "stages").glob("*.source.yaml"))


def generated_feature_contract_path(source_path: Path) -> Path:
    return source_path.parent / f"{source_path.parent.name}.yaml"


def generated_lineage_path(source_path: Path) -> Path:
    return source_path.parent / "lineage.generated.yaml"


def generated_stage_contract_path(source_path: Path) -> Path:
    stage_id = source_path.name.replace(".source.yaml", "")
    return source_path.parent / f"{stage_id}.yaml"


def feature_contract_paths(repo_root: Path) -> list[Path]:
    contracts: list[Path] = []
    for path in sorted((repo_root / "docs" / "features").glob("*/*.yaml")):
        if path.name in {"feature.source.yaml", "lineage.generated.yaml"}:
            continue
        contracts.append(path)
    return contracts


def stage_contract_paths(repo_root: Path) -> list[Path]:
    contracts: list[Path] = []
    for path in sorted((repo_root / "docs" / "stages").glob("*.yaml")):
        if path.name.endswith(".source.yaml"):
            continue
        contracts.append(path)
    return contracts


def source_feature_ids(repo_root: Path) -> set[str]:
    return {path.parent.name for path in feature_source_paths(repo_root)}


def source_stage_ids(repo_root: Path) -> set[str]:
    return {path.name.replace(".source.yaml", "") for path in stage_source_paths(repo_root)}


def load_contract_body(path: Path) -> tuple[str, dict[str, object]]:
    payload = cast(dict[str, dict[str, object]], read_yaml(path))
    contract_id = next(iter(payload))
    return contract_id, cast(dict[str, object], payload[contract_id])


def load_feature_body_from_source(source_path: Path) -> tuple[str, dict[str, object]]:
    payload = cast(dict[str, object], read_yaml(source_path))
    feature_id = cast(str, payload["feature_id"])
    body = {key: value for key, value in payload.items() if key != "feature_id"}
    return feature_id, body


def load_stage_body_from_source(source_path: Path) -> tuple[str, dict[str, object]]:
    payload = cast(dict[str, object], read_yaml(source_path))
    stage_id = cast(str, payload["stage_id"])
    body = {key: value for key, value in payload.items() if key != "stage_id"}
    return stage_id, body


def iter_feature_records(repo_root: Path) -> list[tuple[str, dict[str, object], bool, Path]]:
    records: list[tuple[str, dict[str, object], bool, Path]] = []
    source_ids = source_feature_ids(repo_root)
    for source_path in feature_source_paths(repo_root):
        feature_id, body = load_feature_body_from_source(source_path)
        records.append((feature_id, body, True, source_path))
    for contract_path in feature_contract_paths(repo_root):
        if contract_path.parent.name in source_ids:
            continue
        feature_id, body = load_contract_body(contract_path)
        records.append((feature_id, body, False, contract_path))
    return sorted(records, key=lambda item: item[0])


def iter_stage_records(repo_root: Path) -> list[tuple[str, dict[str, object], bool, Path]]:
    records: list[tuple[str, dict[str, object], bool, Path]] = []
    source_ids = source_stage_ids(repo_root)
    for source_path in stage_source_paths(repo_root):
        stage_id, body = load_stage_body_from_source(source_path)
        records.append((stage_id, body, True, source_path))
    for contract_path in stage_contract_paths(repo_root):
        if contract_path.stem in source_ids:
            continue
        stage_id, body = load_contract_body(contract_path)
        records.append((stage_id, body, False, contract_path))
    return sorted(records, key=lambda item: item[0])


def normalize_capability_entry(
    feature_id: str, capability: object, position: int
) -> dict[str, object]:
    if isinstance(capability, str):
        capability_name = capability
        capability_id = f"{feature_id}.{slugify_capability_name(capability_name)}"
        return {
            "feature_id": feature_id,
            "capability_id": capability_id,
            "capability_name": capability_name,
            "summary": capability_name,
            "source_shape": "string",
        }

    payload = cast(dict[str, object], capability)
    capability_name = cast(str, payload.get("name", f"{feature_id} capability {position + 1}"))
    capability_id = cast(
        str,
        payload.get("capability_id", f"{feature_id}.{slugify_capability_name(capability_name)}"),
    )
    entry: dict[str, object] = {
        "feature_id": feature_id,
        "capability_id": capability_id,
        "capability_name": capability_name,
        "source_shape": "structured",
    }
    summary = payload.get("summary")
    if summary is not None:
        entry["summary"] = summary
    return entry


def capability_shape(capabilities: list[object]) -> str:
    has_strings = any(isinstance(capability, str) for capability in capabilities)
    has_structured = any(isinstance(capability, dict) for capability in capabilities)
    if has_strings and has_structured:
        return "mixed"
    if has_structured:
        return "structured"
    if has_strings:
        return "string"
    return "empty"


def normalize_refs(refs: object) -> dict[str, list[str]]:
    if not isinstance(refs, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for key, value in refs.items():
        if isinstance(value, list):
            normalized[str(key)] = [str(item) for item in value]
    return normalized


def render_feature_outputs(repo_root: Path, source_path: Path) -> list[RenderedFile]:
    feature_id, feature_body = load_feature_body_from_source(source_path)
    raw_capabilities = cast(list[object], feature_body.get("capabilities", []))
    normalized_capabilities = [
        normalize_capability_entry(feature_id, capability, index)
        for index, capability in enumerate(raw_capabilities)
    ]
    normalized_refs = normalize_refs(feature_body.get("refs", {}))
    lineage_payload = {
        "feature_id": feature_id,
        "source": relpath(source_path, repo_root),
        "generated_contract": relpath(generated_feature_contract_path(source_path), repo_root),
        "naming_policy": naming_policy(),
        "depends_on": feature_body.get("depends_on", []),
        "capability_shape": capability_shape(raw_capabilities),
        "capability_ids": [entry["capability_id"] for entry in normalized_capabilities],
        "capabilities": normalized_capabilities,
        "stage_participation": feature_body.get("stage_participation", []),
        "stage_summary": [
            {
                "stage_id": cast(dict[str, object], entry).get("stage_id"),
                "role": cast(dict[str, object], entry).get("role", "unknown"),
                "capability_ids": cast(dict[str, object], entry).get("capability_ids", []),
            }
            for entry in cast(list[object], feature_body.get("stage_participation", []))
            if isinstance(entry, dict)
        ],
        "refs": normalized_refs,
        "refs_by_type": normalized_refs,
    }
    return [
        RenderedFile(
            path=generated_feature_contract_path(source_path),
            content=dump_yaml({feature_id: feature_body}),
        ),
        RenderedFile(
            path=generated_lineage_path(source_path),
            content=dump_yaml(lineage_payload),
        ),
    ]


def render_stage_outputs(source_path: Path) -> list[RenderedFile]:
    stage_id, stage_body = load_stage_body_from_source(source_path)
    return [
        RenderedFile(
            path=generated_stage_contract_path(source_path),
            content=dump_yaml({stage_id: stage_body}),
        )
    ]


def build_features_index(repo_root: Path) -> RenderedFile:
    entries: list[dict[str, object]] = []
    for feature_id, body, source_managed, source_path in iter_feature_records(repo_root):
        contract_path = (
            generated_feature_contract_path(source_path)
            if source_managed
            else source_path
        )
        entries.append(
            {
                "feature_id": feature_id,
                "version": body.get("version", "source-managed"),
                "status": body.get("status", "unknown"),
                "type": body.get("type", "unknown"),
                "owner": body.get("owner", "unknown"),
                "domains": body.get("domains", []),
                "contract": relpath(contract_path, repo_root),
                "history": f"docs/features/{feature_id}/history.md",
            }
        )
    content = FEATURES_INDEX_HEADER + "\n\n" + dump_yaml({"features": entries})
    return RenderedFile(repo_root / "docs" / "generated" / "features_index.yaml", content)


def build_feature_dependency_graph(repo_root: Path) -> RenderedFile:
    graph: dict[str, dict[str, list[str]]] = {}
    for feature_id, body, _source_managed, _source_path in iter_feature_records(repo_root):
        graph[feature_id] = {
            "depends_on": cast(list[str], body.get("depends_on", [])),
            "used_by": [],
        }
    for feature_id, entry in graph.items():
        for dependency in entry["depends_on"]:
            if dependency in graph:
                graph[dependency]["used_by"].append(feature_id)
    for entry in graph.values():
        entry["depends_on"] = sorted(entry["depends_on"])
        entry["used_by"] = sorted(entry["used_by"])
    payload = {
        "graph": graph,
        "orphans": {
            "no_dependencies": sorted(
                feature_id for feature_id, entry in graph.items() if not entry["depends_on"]
            ),
            "no_dependents": sorted(
                feature_id for feature_id, entry in graph.items() if not entry["used_by"]
            ),
        },
        "_meta": {
            "generated_by": "scripts/sync_architecture_docs.py",
            "note": "depends_on / used_by are canonical edges. used_by is derived from depends_on.",
        },
    }
    return RenderedFile(
        repo_root / "docs" / "generated" / "feature_dependency_graph.yaml",
        dump_yaml(payload),
    )


def build_feature_capabilities_index(repo_root: Path) -> RenderedFile:
    entries: list[dict[str, object]] = []
    for feature_id, body, _source_managed, _source_path in iter_feature_records(repo_root):
        capabilities = cast(list[object], body.get("capabilities", []))
        for index, capability in enumerate(capabilities):
            entries.append(normalize_capability_entry(feature_id, capability, index))
    entries.sort(
        key=lambda entry: (
            cast(str, entry["feature_id"]),
            cast(str, entry["capability_id"]),
        )
    )
    return RenderedFile(
        repo_root / "docs" / "generated" / "feature_capabilities_index.yaml",
        dump_yaml({"capabilities": entries}),
    )


def build_features_by_status(repo_root: Path) -> RenderedFile:
    grouped: dict[str, list[str]] = {status: [] for status in STATUS_ORDER}
    for feature_id, body, _source_managed, _source_path in iter_feature_records(repo_root):
        status = cast(str, body.get("status", "unknown"))
        grouped.setdefault(status, [])
        grouped[status].append(feature_id)
    for feature_ids in grouped.values():
        feature_ids.sort()
    payload: dict[str, object] = {status: grouped.get(status, []) for status in STATUS_ORDER}
    payload["_meta"] = {
        "generated_by": "scripts/sync_architecture_docs.py",
        "note": f"status_order: {STATUS_ORDER}",
    }
    return RenderedFile(
        repo_root / "docs" / "generated" / "features_by_status.yaml",
        dump_yaml(payload),
    )


def build_feature_overview(repo_root: Path) -> RenderedFile:
    records = iter_feature_records(repo_root)
    grouped: dict[str, list[tuple[str, dict[str, object]]]] = {}
    for feature_id, body, _source_managed, _source_path in records:
        status = cast(str, body.get("status", "unknown"))
        grouped.setdefault(status, []).append((feature_id, body))

    lines = [FEATURE_OVERVIEW_HEADER]
    for status in STATUS_ORDER:
        if not grouped.get(status):
            continue
        lines.extend(
            [
                "",
                f"## {status.title()}",
                "",
                "| Feature | Type | Owner | Summary |",
                "|---|---|---|---|",
            ]
        )
        for feature_id, body in sorted(grouped[status], key=lambda item: item[0]):
            lines.append(
                f"| `{feature_id}` | {body.get('type', 'unknown')} | "
                f"{body.get('owner', 'unknown')} | {body.get('summary', '')} |"
            )
    lines.extend(
        [
            "",
            "## Feature Contracts",
            "",
            "Each managed feature uses the following shape:",
            "",
            "```text",
            "docs/features/<feature_id>/feature.source.yaml",
            "docs/features/<feature_id>/<feature_id>.yaml",
            "docs/features/<feature_id>/lineage.generated.yaml",
            "docs/features/<feature_id>/history.md",
            "```",
            "",
            "For the machine-friendly index, see `docs/generated/features_index.yaml`.",
            "",
        ]
    )
    return RenderedFile(repo_root / "docs" / "generated" / "feature_overview.md", "\n".join(lines))


def build_stages_index(repo_root: Path) -> RenderedFile:
    entries: list[dict[str, object]] = []
    for stage_id, body, source_managed, source_path in iter_stage_records(repo_root):
        contract_path = generated_stage_contract_path(source_path) if source_managed else source_path
        entries.append(
            {
                "stage_id": stage_id,
                "name": body.get("name", stage_id.replace("_", " ").title()),
                "depends_on": body.get("depends_on", []),
                "primary_features": body.get("primary_features", []),
                "related_features": body.get("related_features", []),
                "contract": relpath(contract_path, repo_root),
            }
        )
    content = STAGES_INDEX_HEADER + "\n\n" + dump_yaml({"stages": entries})
    return RenderedFile(repo_root / "docs" / "generated" / "stages_index.yaml", content)


def build_stage_overview(repo_root: Path) -> RenderedFile:
    lines = [
        STAGE_OVERVIEW_HEADER,
        "",
        "| Stage | Depends On | Primary Features | Summary |",
        "|---|---|---|---|",
    ]
    for stage_id, body, _source_managed, _source_path in iter_stage_records(repo_root):
        depends_on = cast(list[str], body.get("depends_on", []))
        primary_features = cast(list[str], body.get("primary_features", []))
        summary = cast(str, body.get("summary", ""))
        depends_display = ", ".join(f"`{value}`" for value in depends_on) if depends_on else "—"
        features_display = (
            ", ".join(f"`{value}`" for value in primary_features) if primary_features else "—"
        )
        lines.append(f"| `{stage_id}` | {depends_display} | {features_display} | {summary} |")
    lines.extend(
        [
            "",
            "## Stage Contracts",
            "",
            "Each managed stage uses the following shape:",
            "",
            "```text",
            "docs/stages/<stage_id>.source.yaml",
            "docs/stages/<stage_id>.yaml",
            "```",
            "",
            "For the machine-friendly index, see `docs/generated/stages_index.yaml`.",
            "",
        ]
    )
    return RenderedFile(repo_root / "docs" / "generated" / "stage_overview.md", "\n".join(lines))


def collect_rendered_files(repo_root: Path) -> list[RenderedFile]:
    rendered: list[RenderedFile] = []
    for source_path in feature_source_paths(repo_root):
        rendered.extend(render_feature_outputs(repo_root, source_path))
    for source_path in stage_source_paths(repo_root):
        rendered.extend(render_stage_outputs(source_path))
    rendered.extend(
        [
            build_features_index(repo_root),
            build_feature_dependency_graph(repo_root),
            build_feature_capabilities_index(repo_root),
            build_feature_overview(repo_root),
            build_features_by_status(repo_root),
            build_stages_index(repo_root),
            build_stage_overview(repo_root),
        ]
    )
    return rendered


def write_rendered_files(rendered_files: list[RenderedFile]) -> None:
    for rendered in rendered_files:
        rendered.path.parent.mkdir(parents=True, exist_ok=True)
        rendered.path.write_text(normalize_text(rendered.content), encoding="utf-8")


def stale_outputs(rendered_files: list[RenderedFile]) -> list[Path]:
    stale: list[Path] = []
    for rendered in rendered_files:
        expected = normalize_text(rendered.content)
        if not rendered.path.exists():
            stale.append(rendered.path)
            continue
        actual = normalize_text(rendered.path.read_text(encoding="utf-8"))
        if actual != expected:
            stale.append(rendered.path)
    return stale


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    rendered_files = collect_rendered_files(repo_root)
    if args.check:
        stale = stale_outputs(rendered_files)
        if stale:
            for path in stale:
                print(f"Stale generated file: {relpath(path, repo_root)}")
            return 1
        print("Architecture docs are up to date.")
        return 0

    write_rendered_files(rendered_files)
    print("Architecture docs synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
@meta
name: validate_adoption_shape
type: script
domain: docs
responsibility:
  - Validate the explicit starter adoption mode and architecture-doc shape.
  - Catch mixed legacy/managed feature metadata states and method-layer pseudo-features.
inputs:
  - repo_config/adoption-mode.yaml
  - docs/features/
  - docs/stages/
  - docs/generated/
  - docs/superpowers/specs/*.md
  - docs/superpowers/plans/*.md
outputs:
  - Exit status and human-readable adoption-shape validation results.
tags:
  - docs
  - validation
  - adoption
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any

import yaml


ALLOWED_MODES = {
    "starter_method_only",
    "managed_architecture_metadata",
    "legacy_compatibility",
}
METHOD_FEATURE_IDS = {"repo-operating-system"}
METHOD_FEATURE_PREFIXES = (
    "repo-",
    "agent-",
    "adapter-",
    "publication-",
    "docs-governance",
)
GENERATED_INDEX_NAMES = {
    "architecture_dag.yaml",
    "capability_lineage.yaml",
    "feature_capabilities_index.yaml",
    "feature_dependency_graph.yaml",
    "feature_overview.md",
    "features_by_status.yaml",
    "features_index.yaml",
}
FEATURE_CONTRACT_REQUIRED_KEYS = {
    "feature_id",
    "name",
    "status",
    "type",
    "summary",
    "invariants",
    "domains",
    "depends_on",
    "capabilities",
    "refs",
}
FEATURE_CONTRACT_REF_KEYS = {
    "code",
    "tests",
    "specs",
    "plans",
    "docs",
    "configs",
    "components",
}
FEATURE_CONTRACT_FRESHNESS_KEYS = {
    "revision",
    "latest_change_id",
    "last_updated_at",
}
FEATURE_CONTRACT_STRING_FIELDS = {
    "feature_id",
    "name",
    "status",
    "type",
    "summary",
}
FEATURE_CONTRACT_INVARIANT_REQUIRED_KEYS = {
    "invariant_id",
    "statement",
    "state",
}
FEATURE_CONTRACT_CAPABILITY_REQUIRED_KEYS = {
    "capability_id",
    "statement",
    "state",
}
STAGE_CONTRACT_REQUIRED_KEYS = {
    "stage_id",
    "name",
    "status",
    "purpose",
    "feature_refs",
    "capability_refs",
    "code_refs",
    "test_refs",
    "doc_refs",
    "config_refs",
    "component_refs",
}
STAGE_CONTRACT_STRING_LIST_OPTIONAL_KEYS = {
    "depends_on",
    "hands_off_to",
    "inputs",
    "outputs",
    "invariants",
    "human_notes",
}
CAPABILITY_LINEAGE_REQUIRED_KEYS = {"features"}
ARCHITECTURE_DAG_REQUIRED_KEYS = {"nodes", "edges"}
METADATA_SCAN_SUFFIXES = {".py", ".yaml", ".yml", ".sql", ".md"}
METADATA_SCAN_SKIP_DIRS = {
    ".git",
    ".tmp-tests",
    ".venv",
    ".agents",
    "venv",
    "node_modules",
    "docs",
    "agent-core",
    "repo_config",
    "scripts",
    "tests",
    "tools",
}
FEATURE_METADATA_PATTERNS = (
    "@capability",
    "@proves",
    "explains.features",
    "capability_id:",
    "capability_ids:",
)
REQUIRED_ROOT_PROJECT_DOCS = (
    "docs/setup.md",
    "docs/configuration.md",
    "docs/usage.md",
    "docs/pipeline.md",
    "docs/architecture.md",
)
REQUIRED_DOC_KEYWORDS = {
    "docs/setup.md": ("depend", "tool version", "install", "provision", "prerequisite", "bootstrap"),
    "docs/configuration.md": (
        "environment variable",
        "config file",
        "profile",
        "default",
        "override",
        "ownership",
        "repo_config",
        "configs",
    ),
    "docs/usage.md": ("command", "entrypoint", "run flow", "workflow", "operator", "developer flow", "run loop"),
    "docs/pipeline.md": ("stage", "workflow", "step", "handoff", "processing flow", "sequence"),
    "docs/architecture.md": ("component", "boundar", "integration", "information flow", "control flow"),
}
PLACEHOLDER_PATTERNS = ("todo", "tbd", "placeholder", "fill this in later")
REQUIRED_PROJECT_FOLDERS = (
    "docs/intent",
    "docs/operating_system",
    "docs/superpowers/specs",
    "docs/superpowers/plans",
    "repo_config",
    "scripts",
    "tests",
)
MANAGED_FEATURE_TEMPLATE_PATH = "docs/architecture_templates/feature.source.yaml"
YAML_ARCHITECTURE_TEMPLATE_PATH = "docs/architecture_templates/yaml-architecture.yaml"
MARKDOWN_FRONTMATTER_TEMPLATE_PATH = "docs/architecture_templates/markdown-frontmatter.md"
REQUIRED_STARTER_SYNC_SURFACE_CLASSES = {
    "repo_config",
    "operating_system_docs",
    "skills",
    "adapters",
    "generated_instruction_surfaces",
    "validation_and_sync_scripts",
}
ALLOWED_STARTER_SYNC_STATUSES = {"aligned", "customized", "deferred", "not_applicable"}
REQUIRED_LINEAGE_TOP_LEVEL_KEYS = {"feature_id", "source", "invariants", "capabilities", "timeline"}
LEGACY_LINEAGE_TOP_LEVEL_KEYS = {
    "generated_contract",
    "naming_policy",
    "capability_shape",
    "capability_ids",
    "refs",
    "refs_by_type",
}
LINEAGE_REQUIRED_CAPABILITY_KEYS = {
    "state",
    "statement",
    "satisfies",
    "code",
    "tests",
    "docs",
    "docs_evidence",
    "configs",
    "config_evidence",
    "components",
    "component_evidence",
    "specs",
    "plans",
    "evidence_gaps",
    "allowed_evidence_gaps",
    "lineage_exception_reason",
    "unresolved_evidence_gaps",
    "completeness_status",
}
LINEAGE_RICH_TIMELINE_KEYS = {
    "completed_at",
    "source_plan",
    "change_id",
    "summary",
    "capabilities",
    "verification",
    "outcome",
}
LINEAGE_COMPLETENESS_STATUSES = {"complete", "excepted", "incomplete"}


@dataclass(frozen=True)
class Finding:
    level: str
    path: str
    message: str
    fix: str


@dataclass(frozen=True)
class AdoptionConfig:
    mode: str
    managed_architecture_metadata: bool
    legacy_feature_contracts: bool
    architecture_generator: str
    payload: dict[str, Any]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate starter adoption mode and architecture-doc shape."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to validate. Defaults to this script's repository.",
    )
    parser.add_argument(
        "--adoption-mode",
        default="repo_config/adoption-mode.yaml",
        help="Path to adoption-mode.yaml relative to repo root.",
    )
    return parser


def relpath(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def add_error(findings: list[Finding], path: str, message: str, fix: str) -> None:
    findings.append(Finding("ERROR", path, message, fix))


def add_warning(findings: list[Finding], path: str, message: str, fix: str) -> None:
    findings.append(Finding("WARN", path, message, fix))


def parse_adoption_config(path: Path, findings: list[Finding], root: Path) -> AdoptionConfig | None:
    if not path.exists():
        add_error(
            findings,
            relpath(path, root),
            "Missing adoption mode source file.",
            "Create repo_config/adoption-mode.yaml and choose an adoption_mode.",
        )
        return None

    try:
        payload = load_yaml(path)
    except yaml.YAMLError as exc:
        add_error(
            findings,
            relpath(path, root),
            f"Could not parse adoption mode YAML: {exc}",
            "Fix YAML syntax.",
        )
        return None

    if not isinstance(payload, dict):
        add_error(
            findings,
            relpath(path, root),
            "Adoption mode file must be a top-level mapping.",
            "Use keys such as adoption_mode, managed_architecture_metadata, and legacy_feature_contracts.",
        )
        return None

    mode = payload.get("adoption_mode")
    managed = payload.get("managed_architecture_metadata")
    legacy = payload.get("legacy_feature_contracts")
    generator = payload.get("architecture_generator", "none")

    if mode not in ALLOWED_MODES:
        add_error(
            findings,
            relpath(path, root),
            f"Invalid adoption_mode: {mode!r}.",
            "Use one of: " + ", ".join(sorted(ALLOWED_MODES)) + ".",
        )
        return None

    if not isinstance(managed, bool):
        add_error(
            findings,
            relpath(path, root),
            "managed_architecture_metadata must be a boolean.",
            "Set managed_architecture_metadata to true or false.",
        )
        return None

    if not isinstance(legacy, bool):
        add_error(
            findings,
            relpath(path, root),
            "legacy_feature_contracts must be a boolean.",
            "Set legacy_feature_contracts to true or false.",
        )
        return None

    if not isinstance(generator, str):
        add_error(
            findings,
            relpath(path, root),
            "architecture_generator must be a string path or `none`.",
            "Set architecture_generator to none or a generator script path.",
        )
        return None

    config = AdoptionConfig(mode, managed, legacy, generator, payload)
    validate_mode_consistency(config, relpath(path, root), findings)
    validate_starter_sync_record(config, relpath(path, root), findings)
    return config


def validate_mode_consistency(config: AdoptionConfig, path: str, findings: list[Finding]) -> None:
    expected = {
        "starter_method_only": (False, False),
        "managed_architecture_metadata": (True, False),
        "legacy_compatibility": (False, True),
    }[config.mode]
    if (config.managed_architecture_metadata, config.legacy_feature_contracts) != expected:
        add_error(
            findings,
            path,
            "Adoption mode booleans do not match adoption_mode.",
            (
                f"For {config.mode}, set managed_architecture_metadata={str(expected[0]).lower()} "
                f"and legacy_feature_contracts={str(expected[1]).lower()}."
            ),
        )


def is_iso_like_date(value: Any) -> bool:
    if isinstance(value, (date, datetime)):
        return True
    if not isinstance(value, str):
        return False
    for parser in (date.fromisoformat, datetime.fromisoformat):
        try:
            parser(value)
            return True
        except ValueError:
            continue
    return False


def validate_starter_sync_record(config: AdoptionConfig, path: str, findings: list[Finding]) -> None:
    if config.mode != "managed_architecture_metadata":
        return

    starter_sync = config.payload.get("starter_sync")
    if not isinstance(starter_sync, dict):
        add_error(
            findings,
            path,
            "managed_architecture_metadata mode requires a starter_sync record.",
            (
                "Add starter_sync with starter_baseline_ref, last_shared_surface_review_at, "
                "and reviewed_surface_classes to repo_config/adoption-mode.yaml."
            ),
        )
        return

    baseline = starter_sync.get("starter_baseline_ref")
    if not isinstance(baseline, str) or not baseline.strip():
        add_error(
            findings,
            path,
            "starter_sync.starter_baseline_ref must be a non-empty string.",
            "Record the reviewed starter commit, tag, or comparable baseline reference.",
        )

    reviewed_at = starter_sync.get("last_shared_surface_review_at")
    if not is_iso_like_date(reviewed_at):
        add_error(
            findings,
            path,
            "starter_sync.last_shared_surface_review_at must be an ISO-8601 date or timestamp.",
            "Use a value such as 2026-04-21 or 2026-04-21T10:30:00.",
        )

    reviewed_surface_classes = starter_sync.get("reviewed_surface_classes")
    if not isinstance(reviewed_surface_classes, list) or not reviewed_surface_classes:
        add_error(
            findings,
            path,
            "starter_sync.reviewed_surface_classes must be a non-empty list.",
            "List the starter-owned surface classes reviewed for this Mode B sync.",
        )
    else:
        invalid_classes = [value for value in reviewed_surface_classes if not isinstance(value, str) or not value]
        if invalid_classes:
            add_error(
                findings,
                path,
                "starter_sync.reviewed_surface_classes entries must be non-empty strings.",
                "Use stable surface-class names such as repo_config or operating_system_docs.",
            )
        missing_classes = REQUIRED_STARTER_SYNC_SURFACE_CLASSES.difference(
            value for value in reviewed_surface_classes if isinstance(value, str)
        )
        if missing_classes:
            add_error(
                findings,
                path,
                "starter_sync.reviewed_surface_classes is missing required Mode B surface classes.",
                "Include: " + ", ".join(sorted(REQUIRED_STARTER_SYNC_SURFACE_CLASSES)) + ".",
            )

    divergences = starter_sync.get("divergences", [])
    if divergences is None:
        return
    if not isinstance(divergences, list):
        add_error(
            findings,
            path,
            "starter_sync.divergences must be a list when present.",
            "Use a list of divergence mappings or omit the field.",
        )
        return

    for index, divergence in enumerate(divergences):
        if not isinstance(divergence, dict):
            add_error(
                findings,
                path,
                f"starter_sync.divergences[{index}] must be a mapping.",
                "Use path/class/status/rationale fields for each declared divergence.",
            )
            continue

        divergence_path = divergence.get("path")
        divergence_class = divergence.get("class")
        status = divergence.get("status")
        rationale = divergence.get("rationale")

        if not isinstance(divergence_path, str) or not divergence_path.strip():
            add_error(
                findings,
                path,
                f"starter_sync.divergences[{index}].path must be a non-empty string.",
                "Record the customized shared-surface path.",
            )
        if not isinstance(divergence_class, str) or divergence_class not in REQUIRED_STARTER_SYNC_SURFACE_CLASSES:
            add_error(
                findings,
                path,
                f"starter_sync.divergences[{index}].class must be one of the reviewed surface classes.",
                "Use one of: " + ", ".join(sorted(REQUIRED_STARTER_SYNC_SURFACE_CLASSES)) + ".",
            )
        if not isinstance(status, str) or status not in ALLOWED_STARTER_SYNC_STATUSES:
            add_error(
                findings,
                path,
                f"starter_sync.divergences[{index}].status must be one of {sorted(ALLOWED_STARTER_SYNC_STATUSES)}.",
                "Use aligned, customized, deferred, or not_applicable.",
            )
        if not isinstance(rationale, str) or not rationale.strip():
            add_error(
                findings,
                path,
                f"starter_sync.divergences[{index}].rationale must be a non-empty string.",
                "Explain why the divergence is intentional.",
            )


def feature_roots(root: Path) -> list[Path]:
    features_root = root / "docs" / "features"
    if not features_root.exists():
        return []
    return sorted(path for path in features_root.iterdir() if path.is_dir())


def flat_feature_files(root: Path) -> list[Path]:
    features_root = root / "docs" / "features"
    if not features_root.exists():
        return []
    return sorted(path for path in features_root.glob("*.yaml") if path.is_file())


def managed_feature_contracts(root: Path) -> list[Path]:
    contracts: list[Path] = []
    for folder in feature_roots(root):
        contract = folder / f"{folder.name}.yaml"
        if contract.exists():
            contracts.append(contract)
    return sorted(contracts)


def stage_contract_files(root: Path) -> list[Path]:
    stages_root = root / "docs" / "stages"
    if not stages_root.exists():
        return []
    return sorted(
        path
        for path in stages_root.glob("*.yaml")
        if path.is_file() and not path.name.endswith(".source.yaml")
    )


def feature_source_files(root: Path) -> list[Path]:
    return sorted((root / "docs" / "features").glob("*/feature.source.yaml"))


def generated_architecture_files(root: Path) -> list[Path]:
    generated_root = root / "docs" / "generated"
    if not generated_root.exists():
        return []
    return sorted(
        path for path in generated_root.iterdir() if path.is_file() and path.name in GENERATED_INDEX_NAMES
    )


def is_empty_generated_scaffold(path: Path) -> bool:
    try:
        payload = load_yaml(path)
    except yaml.YAMLError:
        return False
    if path.name == "architecture_dag.yaml" and payload == {"nodes": [], "edges": []}:
        return True
    if path.name == "capability_lineage.yaml" and payload == {"features": {}}:
        return True
    return False


def feature_ids_from_shape(root: Path) -> set[str]:
    ids = {path.stem for path in flat_feature_files(root)}
    ids.update(path.name for path in feature_roots(root))
    return ids


def validate_method_feature_ids(root: Path, findings: list[Finding]) -> None:
    for feature_id in sorted(feature_ids_from_shape(root)):
        is_method_id = feature_id in METHOD_FEATURE_IDS or feature_id.startswith(METHOD_FEATURE_PREFIXES)
        if not is_method_id:
            continue
        candidate_paths = [root / "docs" / "features" / f"{feature_id}.yaml", root / "docs" / "features" / feature_id]
        existing_path = next((path for path in candidate_paths if path.exists()), candidate_paths[0])
        add_error(
            findings,
            relpath(existing_path, root),
            f"Method-layer pseudo-feature `{feature_id}` is not allowed.",
            "Move repo-method content to docs/operating_system/ or operating-system specs/plans with targets.",
        )


def validate_feature_dependencies(root: Path, findings: list[Finding]) -> None:
    feature_ids = feature_ids_from_shape(root)
    for path in flat_feature_files(root) + managed_feature_contracts(root) + feature_source_files(root):
        try:
            payload = load_yaml(path)
        except yaml.YAMLError as exc:
            add_error(findings, relpath(path, root), f"Could not parse feature YAML: {exc}", "Fix YAML syntax.")
            continue
        if not isinstance(payload, dict):
            continue
        body = payload
        if len(payload) == 1:
            only_value = next(iter(payload.values()))
            if isinstance(only_value, dict):
                body = only_value
        depends_on = body.get("depends_on", [])
        if depends_on is None:
            continue
        if not isinstance(depends_on, list):
            add_error(
                findings,
                relpath(path, root),
                "depends_on must be a list of feature IDs.",
                "Change depends_on to a list or remove it.",
            )
            continue
        for dependency in depends_on:
            if not isinstance(dependency, str):
                add_error(
                    findings,
                    relpath(path, root),
                    "depends_on entries must be strings.",
                    "Use product feature IDs only.",
                )
                continue
            if dependency not in feature_ids:
                add_error(
                    findings,
                    relpath(path, root),
                    f"depends_on references unknown feature `{dependency}`.",
                    "Use an existing product feature ID or move method-layer relationships into spec/plan targets.",
                )


def is_id_like(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", value))


def validate_capability_ids(root: Path, findings: list[Finding]) -> None:
    paths = flat_feature_files(root) + managed_feature_contracts(root) + feature_source_files(root)
    for path in paths:
        try:
            payload = load_yaml(path)
        except yaml.YAMLError:
            continue
        if not isinstance(payload, dict):
            continue
        body = payload
        if len(payload) == 1:
            only_value = next(iter(payload.values()))
            if isinstance(only_value, dict):
                body = only_value
        capability_ids = body.get("capability_ids", [])
        if capability_ids is None:
            continue
        if not isinstance(capability_ids, list):
            add_error(
                findings,
                relpath(path, root),
                "capability_ids must be a list.",
                "Use stable kebab-case capability IDs.",
            )
            continue
        for capability_id in capability_ids:
            if not isinstance(capability_id, str) or not is_id_like(capability_id):
                add_error(
                    findings,
                    relpath(path, root),
                    f"Invalid capability ID: {capability_id!r}.",
                    "Use stable kebab-case IDs, not prose sentences.",
                )


def validate_required_root_docs(root: Path, findings: list[Finding]) -> None:
    for relative_path in REQUIRED_ROOT_PROJECT_DOCS:
        path = root / Path(relative_path)
        if path.exists():
            continue
        add_error(
            findings,
            relative_path,
            "Missing required root project doc.",
            (
                "Add the required project doc at this path so setup, configuration, "
                "usage, pipeline, and architecture guidance remain present at the repo root."
            ),
        )
        continue

    for relative_path in REQUIRED_ROOT_PROJECT_DOCS:
        path = root / Path(relative_path)
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        if not re.search(r"(?m)^#\s+\S", text):
            add_error(
                findings,
                relative_path,
                "Required doc must include a top-level Markdown heading.",
                "Start the doc with a `#` heading that names the document purpose.",
            )
            continue

        body_lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not body_lines:
            add_error(
                findings,
                relative_path,
                "Required doc must contain more than a heading.",
                "Add substantive guidance below the H1 so the doc is not just a stub.",
            )
            continue

        body_text = " ".join(body_lines).lower()
        if sum(body_text.count(pattern) for pattern in PLACEHOLDER_PATTERNS) >= 2:
            add_error(
                findings,
                relative_path,
                "Required doc is still placeholder-only.",
                "Replace placeholder text with real project guidance before treating the doc as complete.",
            )
            continue

        keywords = REQUIRED_DOC_KEYWORDS.get(relative_path, ())
        if keywords and not any(keyword in body_text for keyword in keywords):
            add_error(
                findings,
                relative_path,
                "Required doc is missing expected semantic coverage.",
                (
                    "Add file-specific guidance so the doc covers its intended subject "
                    "instead of only generic prose."
                ),
            )


def validate_required_project_folders(root: Path, findings: list[Finding]) -> None:
    for relative_path in REQUIRED_PROJECT_FOLDERS:
        path = root / Path(relative_path)
        if path.exists() and path.is_dir():
            continue
        add_error(
            findings,
            f"{relative_path}/",
            "Missing required project folder.",
            (
                "Create this folder so the repo keeps a stable source-of-truth surface for "
                "intent, governance, planning artifacts, config, scripts, and tests."
            ),
        )

    intent_root = root / "docs" / "intent"
    if not intent_root.exists() or not intent_root.is_dir():
        return
    intent_markdown_files = sorted(intent_root.glob("*.md"))
    if intent_markdown_files:
        return
    add_error(
        findings,
        "docs/intent/",
        "Intent layer must contain at least one Markdown file.",
        "Add an intent doc such as docs/intent/README.md so project purpose is not implicit only in README.md.",
    )


def validate_managed_metadata_templates(root: Path, findings: list[Finding]) -> None:
    template_path = root / Path(MANAGED_FEATURE_TEMPLATE_PATH)
    if template_path.exists():
        try:
            payload = load_yaml(template_path)
        except yaml.YAMLError as exc:
            add_error(
                findings,
                MANAGED_FEATURE_TEMPLATE_PATH,
                f"Could not parse managed metadata template YAML: {exc}",
                "Fix the feature source template YAML syntax.",
            )
        else:
            if not isinstance(payload, dict):
                add_error(
                    findings,
                    MANAGED_FEATURE_TEMPLATE_PATH,
                    "Managed metadata feature template must be a top-level mapping.",
                    "Keep docs/architecture_templates/feature.source.yaml aligned with the managed feature schema.",
                )
            else:
                feature_id = payload.get("feature_id")
                if not isinstance(feature_id, str) or not feature_id:
                    add_error(
                        findings,
                        MANAGED_FEATURE_TEMPLATE_PATH,
                        "Managed metadata feature template is missing feature_id.",
                        "Set feature_id in the template so downstream capability examples can stay feature-qualified.",
                    )
                else:
                    stage_participation = payload.get("stage_participation", [])
                    if not isinstance(stage_participation, list):
                        add_error(
                            findings,
                            MANAGED_FEATURE_TEMPLATE_PATH,
                            "Managed metadata feature template stage_participation must be a list.",
                            "Use the same list shape as managed feature source files.",
                        )
                    else:
                        expected_prefix = f"{feature_id}."
                        for index, participation in enumerate(stage_participation):
                            if not isinstance(participation, dict):
                                continue
                            capability_ids = participation.get("capability_ids", [])
                            if capability_ids is None:
                                continue
                            if not isinstance(capability_ids, list):
                                add_error(
                                    findings,
                                    MANAGED_FEATURE_TEMPLATE_PATH,
                                    "Managed metadata feature template capability_ids must be a list.",
                                    "Use a list of feature-qualified capability IDs in stage_participation.",
                                )
                                continue
                            for capability_id in capability_ids:
                                if not isinstance(capability_id, str):
                                    continue
                                if capability_id.startswith(expected_prefix):
                                    continue
                                add_error(
                                    findings,
                                    MANAGED_FEATURE_TEMPLATE_PATH,
                                    (
                                        "Template capability_ids must use feature-qualified IDs under "
                                        f"stage_participation[{index}]."
                                    ),
                                    (
                                        f"Use `{expected_prefix}<capability_slug>` in the template so managed metadata "
                                        "examples preserve downstream capability qualification."
                                    ),
                                )

    yaml_template_path = root / Path(YAML_ARCHITECTURE_TEMPLATE_PATH)
    if yaml_template_path.exists():
        try:
            template_text = yaml_template_path.read_text(encoding="utf-8")
        except OSError:
            template_text = ""
        architecture_block_lines: list[str] = []
        metadata_started = False
        for line in template_text.splitlines():
            stripped = line.strip()
            if not stripped:
                if metadata_started:
                    break
                continue
            comment_body = extract_template_comment_body(line)
            if comment_body is None:
                break
            if comment_body == "@architecture":
                metadata_started = True
                continue
            if metadata_started:
                architecture_block_lines.append(comment_body)

        if architecture_block_lines:
            try:
                yaml_template_payload = yaml.safe_load("\n".join(architecture_block_lines))
            except yaml.YAMLError as exc:
                add_error(
                    findings,
                    YAML_ARCHITECTURE_TEMPLATE_PATH,
                    f"Could not parse YAML architecture template metadata: {exc}",
                    "Fix the fenced # @architecture metadata example syntax.",
                )
            else:
                if isinstance(yaml_template_payload, dict):
                    owner = yaml_template_payload.get("owner")
                    capabilities = yaml_template_payload.get("capabilities", [])
                    if isinstance(owner, str) and owner and isinstance(capabilities, list):
                        expected_prefix = f"{owner}."
                        for capability_id in capabilities:
                            if not isinstance(capability_id, str):
                                continue
                            if capability_id.startswith(expected_prefix):
                                continue
                            add_error(
                                findings,
                                YAML_ARCHITECTURE_TEMPLATE_PATH,
                                "YAML architecture template capabilities must use feature-qualified IDs.",
                                (
                                    f"Use `{expected_prefix}<capability_slug>` in the template so YAML "
                                    "# @architecture examples preserve downstream capability qualification."
                                ),
                            )

    markdown_template_path = root / Path(MARKDOWN_FRONTMATTER_TEMPLATE_PATH)
    if markdown_template_path.exists():
        try:
            markdown_text = markdown_template_path.read_text(encoding="utf-8")
        except OSError:
            markdown_text = ""
        fenced_match = re.search(
            r"```md\s*(---\n.*?\n---)\s*```",
            markdown_text,
            flags=re.DOTALL,
        )
        if fenced_match:
            frontmatter_block = fenced_match.group(1)
            try:
                _, yaml_block, _ = frontmatter_block.split("---", 2)
                frontmatter_payload = yaml.safe_load(yaml_block)
            except (ValueError, yaml.YAMLError) as exc:
                add_error(
                    findings,
                    MARKDOWN_FRONTMATTER_TEMPLATE_PATH,
                    f"Could not parse markdown frontmatter template: {exc}",
                    "Fix the fenced Markdown frontmatter example syntax.",
                )
            else:
                if isinstance(frontmatter_payload, dict):
                    explains = frontmatter_payload.get("explains", {})
                    if isinstance(explains, dict):
                        features = explains.get("features", [])
                        capabilities = explains.get("capabilities", [])
                        feature_id = features[0] if isinstance(features, list) and features else None
                        if isinstance(feature_id, str) and feature_id and isinstance(capabilities, list):
                            expected_prefix = f"{feature_id}."
                            for capability_id in capabilities:
                                if not isinstance(capability_id, str):
                                    continue
                                if capability_id.startswith(expected_prefix):
                                    continue
                                add_error(
                                    findings,
                                    MARKDOWN_FRONTMATTER_TEMPLATE_PATH,
                                    "Frontmatter template capabilities must use feature-qualified IDs.",
                                    (
                                        f"Use `{expected_prefix}<capability_slug>` in the fenced frontmatter "
                                        "example so doc metadata preserves downstream capability qualification."
                                    ),
                                )


def extract_template_comment_body(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    comment_body = stripped[1:]
    if comment_body.startswith(" "):
        comment_body = comment_body[1:]
    return comment_body


def has_generated_header(path: Path) -> bool:
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:300]
    except OSError:
        return False
    return "GENERATED FILE" in head or "Generated file" in head


def _validate_string_list(
    findings: list[Finding],
    *,
    root: Path,
    lineage_path: str,
    capability_id: str,
    field_name: str,
    value: object,
    check_paths: bool = False,
) -> None:
    if not isinstance(value, list):
        add_error(
            findings,
            lineage_path,
            f"{field_name} must be a list for lineage capability `{capability_id}`.",
            f"Regenerate the lineage file so `{field_name}` is emitted as a list.",
        )
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            add_error(
                findings,
                lineage_path,
                f"{field_name}[{index}] must be a non-empty string for lineage capability `{capability_id}`.",
                f"Regenerate the lineage file so `{field_name}` contains stable string values only.",
            )
            continue
        if check_paths and not (root / item).exists():
            add_error(
                findings,
                lineage_path,
                f"{field_name}[{index}] points to a missing path for lineage capability `{capability_id}`: {item}",
                "Refresh generated lineage so all referenced paths exist in the repo.",
            )


def _validate_evidence_nodes(
    findings: list[Finding],
    *,
    root: Path,
    lineage_path: str,
    capability_id: str,
    field_name: str,
    value: object,
) -> None:
    if not isinstance(value, list):
        add_error(
            findings,
            lineage_path,
            f"{field_name} must be a list for lineage capability `{capability_id}`.",
            f"Regenerate the lineage file so `{field_name}` is emitted as an evidence-node list.",
        )
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            add_error(
                findings,
                lineage_path,
                f"{field_name}[{index}] must be a mapping for lineage capability `{capability_id}`.",
                f"Regenerate the lineage file so `{field_name}` entries use the canonical evidence-node shape.",
            )
            continue
        path_value = item.get("path")
        confidence = item.get("confidence")
        source = item.get("source")
        if not isinstance(path_value, str) or not path_value.strip():
            add_error(
                findings,
                lineage_path,
                f"{field_name}[{index}] must include a non-empty `path` for lineage capability `{capability_id}`.",
                "Regenerate the lineage file so every evidence node records its source path.",
            )
        elif not (root / path_value).exists():
            add_error(
                findings,
                lineage_path,
                f"{field_name}[{index}] references a missing path for lineage capability `{capability_id}`: {path_value}",
                "Refresh generated lineage so all evidence node paths exist in the repo.",
            )
        if not isinstance(confidence, str) or not confidence.strip():
            add_error(
                findings,
                lineage_path,
                f"{field_name}[{index}] must include a non-empty `confidence` string for lineage capability `{capability_id}`.",
                "Regenerate the lineage file so every evidence node records confidence.",
            )
        if not isinstance(source, list) or not source or not all(
            isinstance(entry, str) and entry.strip() for entry in source
        ):
            add_error(
                findings,
                lineage_path,
                f"{field_name}[{index}] must include a non-empty string `source` list for lineage capability `{capability_id}`.",
                "Regenerate the lineage file so every evidence node records metadata sources.",
            )
        symbols = item.get("symbols")
        if symbols is not None and (
            not isinstance(symbols, list)
            or not all(isinstance(symbol, str) and symbol.strip() for symbol in symbols)
        ):
            add_error(
                findings,
                lineage_path,
                f"{field_name}[{index}] has invalid `symbols` for lineage capability `{capability_id}`.",
                "Emit `symbols` only as a list of non-empty strings when symbol-level evidence exists.",
            )


def _validate_lineage_capability_entry(
    findings: list[Finding],
    *,
    root: Path,
    lineage_path: str,
    capability_id: str,
    value: object,
) -> None:
    if not isinstance(value, dict):
        add_error(
            findings,
            lineage_path,
            f"lineage capability `{capability_id}` must be a mapping.",
            "Regenerate the lineage file so each capability entry uses the canonical mapping shape.",
        )
        return

    missing_keys = LINEAGE_REQUIRED_CAPABILITY_KEYS.difference(value)
    if missing_keys:
        add_error(
            findings,
            lineage_path,
            f"lineage capability `{capability_id}` is missing required keys.",
            "Include: " + ", ".join(sorted(LINEAGE_REQUIRED_CAPABILITY_KEYS)) + ".",
        )

    state = value.get("state")
    if not isinstance(state, str) or not state.strip():
        add_error(
            findings,
            lineage_path,
            f"lineage capability `{capability_id}` must include a non-empty `state`.",
            "Regenerate the lineage file so each capability records its current lifecycle state.",
        )
    statement = value.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        add_error(
            findings,
            lineage_path,
            f"lineage capability `{capability_id}` must include a non-empty `statement`.",
            "Regenerate the lineage file so each capability records its canonical statement.",
        )

    _validate_string_list(
        findings,
        root=root,
        lineage_path=lineage_path,
        capability_id=capability_id,
        field_name="satisfies",
        value=value.get("satisfies", []),
    )
    _validate_evidence_nodes(
        findings,
        root=root,
        lineage_path=lineage_path,
        capability_id=capability_id,
        field_name="code",
        value=value.get("code", []),
    )
    _validate_evidence_nodes(
        findings,
        root=root,
        lineage_path=lineage_path,
        capability_id=capability_id,
        field_name="tests",
        value=value.get("tests", []),
    )
    _validate_string_list(
        findings,
        root=root,
        lineage_path=lineage_path,
        capability_id=capability_id,
        field_name="docs",
        value=value.get("docs", []),
        check_paths=True,
    )
    _validate_evidence_nodes(
        findings,
        root=root,
        lineage_path=lineage_path,
        capability_id=capability_id,
        field_name="docs_evidence",
        value=value.get("docs_evidence", []),
    )
    _validate_string_list(
        findings,
        root=root,
        lineage_path=lineage_path,
        capability_id=capability_id,
        field_name="configs",
        value=value.get("configs", []),
        check_paths=True,
    )
    _validate_evidence_nodes(
        findings,
        root=root,
        lineage_path=lineage_path,
        capability_id=capability_id,
        field_name="config_evidence",
        value=value.get("config_evidence", []),
    )
    _validate_string_list(
        findings,
        root=root,
        lineage_path=lineage_path,
        capability_id=capability_id,
        field_name="components",
        value=value.get("components", []),
        check_paths=True,
    )
    _validate_evidence_nodes(
        findings,
        root=root,
        lineage_path=lineage_path,
        capability_id=capability_id,
        field_name="component_evidence",
        value=value.get("component_evidence", []),
    )
    for field_name in (
        "specs",
        "plans",
        "evidence_gaps",
        "allowed_evidence_gaps",
        "unresolved_evidence_gaps",
    ):
        _validate_string_list(
            findings,
            root=root,
            lineage_path=lineage_path,
            capability_id=capability_id,
            field_name=field_name,
            value=value.get(field_name, []),
            check_paths=field_name in {"specs", "plans"},
        )

    lineage_exception_reason = value.get("lineage_exception_reason")
    if lineage_exception_reason is not None and (
        not isinstance(lineage_exception_reason, str) or not lineage_exception_reason.strip()
    ):
        add_error(
            findings,
            lineage_path,
            f"lineage capability `{capability_id}` has invalid `lineage_exception_reason`.",
            "Use null or a non-empty string reason for excepted lineage gaps.",
        )

    completeness_status = value.get("completeness_status")
    if completeness_status not in LINEAGE_COMPLETENESS_STATUSES:
        add_error(
            findings,
            lineage_path,
            f"lineage capability `{capability_id}` has invalid `completeness_status`.",
            "Use one of: " + ", ".join(sorted(LINEAGE_COMPLETENESS_STATUSES)) + ".",
        )


def _validate_lineage_timeline(
    findings: list[Finding],
    *,
    root: Path,
    lineage_path: str,
    value: object,
) -> None:
    if not isinstance(value, list):
        add_error(
            findings,
            lineage_path,
            "lineage.generated.yaml timeline must be a list.",
            "Regenerate the file so the timeline stays a list of completed-change records.",
        )
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            add_error(
                findings,
                lineage_path,
                f"timeline[{index}] must be a mapping.",
                "Use the canonical rich completed-change record shape for timeline entries.",
            )
            continue
        missing_keys = LINEAGE_RICH_TIMELINE_KEYS.difference(item)
        if missing_keys:
            add_error(
                findings,
                lineage_path,
                f"timeline[{index}] is missing required keys.",
                "Include: " + ", ".join(sorted(LINEAGE_RICH_TIMELINE_KEYS)) + ".",
            )
        completed_at = item.get("completed_at")
        if not isinstance(completed_at, str) or not completed_at.strip():
            add_error(
                findings,
                lineage_path,
                f"timeline[{index}] must include a non-empty `completed_at` string.",
                "Emit completed timeline entries from completed plans with stable timestamps.",
            )
        source_plan = item.get("source_plan")
        if not isinstance(source_plan, str) or not source_plan.strip():
            add_error(
                findings,
                lineage_path,
                f"timeline[{index}] must include a non-empty `source_plan` string.",
                "Emit the originating completed plan path for each timeline entry.",
            )
        elif not (root / source_plan).exists():
            add_error(
                findings,
                lineage_path,
                f"timeline[{index}] references a missing source_plan: {source_plan}",
                "Refresh generated lineage so timeline entries point at existing plan files.",
            )
        for field_name in ("change_id", "summary", "outcome"):
            field_value = item.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                add_error(
                    findings,
                    lineage_path,
                    f"timeline[{index}] must include a non-empty `{field_name}` string.",
                    "Emit canonical completed-plan metadata for each timeline entry.",
                )
        capabilities = item.get("capabilities")
        if not isinstance(capabilities, list) or not all(
            isinstance(entry, str) and entry.strip() for entry in capabilities
        ):
            add_error(
                findings,
                lineage_path,
                f"timeline[{index}] must include a string `capabilities` list.",
                "Emit capability-qualified IDs for every completed change record.",
            )
        verification = item.get("verification")
        if not isinstance(verification, list) or not all(
            isinstance(entry, str) and entry.strip() for entry in verification
        ):
            add_error(
                findings,
                lineage_path,
                f"timeline[{index}] must include a string `verification` list.",
                "Emit verification commands as a list of non-empty strings.",
            )


def validate_generated_feature_contract_schema(root: Path, findings: list[Finding]) -> None:
    for contract_path in managed_feature_contracts(root):
        relative_contract_path = relpath(contract_path, root)
        if not has_generated_header(contract_path):
            add_error(
                findings,
                relative_contract_path,
                "Generated feature contract must include the generated-file header.",
                "Regenerate the feature contract with the canonical architecture metadata generator.",
            )

        try:
            payload = load_yaml(contract_path)
        except yaml.YAMLError as exc:
            add_error(
                findings,
                relative_contract_path,
                f"Could not parse generated feature contract: {exc}",
                "Fix YAML syntax or regenerate the file with the canonical generator.",
            )
            continue

        if not isinstance(payload, dict):
            add_error(
                findings,
                relative_contract_path,
                "Generated feature contract must be a top-level mapping.",
                "Regenerate the file so the feature contract uses the canonical mapping shape.",
            )
            continue

        missing_keys = FEATURE_CONTRACT_REQUIRED_KEYS.difference(payload)
        if missing_keys:
            add_error(
                findings,
                relative_contract_path,
                "Generated feature contract is missing required keys.",
                "Include: " + ", ".join(sorted(FEATURE_CONTRACT_REQUIRED_KEYS)) + ".",
            )

        for field_name in FEATURE_CONTRACT_STRING_FIELDS:
            value = payload.get(field_name)
            if not isinstance(value, str) or not value.strip():
                add_error(
                    findings,
                    relative_contract_path,
                    f"Generated feature contract {field_name} must be a non-empty string.",
                    "Regenerate the feature contract so canonical top-level feature fields stay explicit.",
                )

        refs = payload.get("refs")
        if not isinstance(refs, dict):
            add_error(
                findings,
                relative_contract_path,
                "Generated feature contract refs must be a mapping.",
                "Regenerate the feature contract so refs stay grouped by canonical ref family.",
            )
        else:
            missing_ref_keys = FEATURE_CONTRACT_REF_KEYS.difference(refs)
            if missing_ref_keys:
                add_error(
                    findings,
                    relative_contract_path,
                    "Generated feature contract refs are missing required keys.",
                    "Include: " + ", ".join(sorted(FEATURE_CONTRACT_REF_KEYS)) + ".",
                )
            for key in FEATURE_CONTRACT_REF_KEYS.intersection(refs):
                _validate_string_list(
                    findings,
                    root=root,
                    lineage_path=relative_contract_path,
                    capability_id=payload.get("feature_id", contract_path.stem),
                    field_name=f"refs.{key}",
                    value=refs.get(key, []),
                    check_paths=key in {"code", "tests", "specs", "plans", "docs", "configs", "components"},
                )

        for field_name in ("domains", "depends_on"):
            _validate_string_list(
                findings,
                root=root,
                lineage_path=relative_contract_path,
                capability_id=payload.get("feature_id", contract_path.stem),
                field_name=field_name,
                value=payload.get(field_name, []),
            )
        for field_name in ("invariants", "capabilities"):
            value = payload.get(field_name, [])
            if not isinstance(value, list):
                add_error(
                    findings,
                    relative_contract_path,
                    f"Generated feature contract {field_name} must be a list.",
                    "Regenerate the feature contract so structured feature items stay list-shaped.",
                )
                continue
            required_keys = (
                FEATURE_CONTRACT_INVARIANT_REQUIRED_KEYS
                if field_name == "invariants"
                else FEATURE_CONTRACT_CAPABILITY_REQUIRED_KEYS
            )
            id_field = "invariant_id" if field_name == "invariants" else "capability_id"
            for index, item in enumerate(value):
                if not isinstance(item, dict):
                    add_error(
                        findings,
                        relative_contract_path,
                        f"Generated feature contract {field_name}[{index}] must be a mapping.",
                        "Regenerate the feature contract so structured items keep the canonical object shape.",
                    )
                    continue
                missing_item_keys = required_keys.difference(item)
                if missing_item_keys:
                    add_error(
                        findings,
                        relative_contract_path,
                        f"Generated feature contract {field_name}[{index}] is missing required keys.",
                        "Include: " + ", ".join(sorted(required_keys)) + ".",
                    )
                for required_field in required_keys:
                    field_value = item.get(required_field)
                    if not isinstance(field_value, str) or not field_value.strip():
                        add_error(
                            findings,
                            relative_contract_path,
                            (
                                f"Generated feature contract {field_name}[{index}].{required_field} "
                                "must be a non-empty string."
                            ),
                            (
                                "Regenerate the feature contract so "
                                f"{field_name} entries keep canonical structured fields."
                            ),
                        )
                if field_name == "capabilities":
                    satisfies = item.get("satisfies", [])
                    _validate_string_list(
                        findings,
                        root=root,
                        lineage_path=relative_contract_path,
                        capability_id=str(item.get(id_field, payload.get("feature_id", contract_path.stem))),
                        field_name=f"{field_name}[{index}].satisfies",
                        value=satisfies,
                    )

        if any(key in payload for key in FEATURE_CONTRACT_FRESHNESS_KEYS):
            revision = payload.get("revision")
            if revision is not None and not isinstance(revision, int):
                add_error(
                    findings,
                    relative_contract_path,
                    "Generated feature contract revision must be an integer.",
                    "Regenerate the contract so revision is emitted as an integer freshness field.",
                )
            for field_name in ("latest_change_id", "last_updated_at"):
                value = payload.get(field_name)
                if value is not None and (not isinstance(value, str) or not value.strip()):
                    add_error(
                        findings,
                        relative_contract_path,
                        f"Generated feature contract {field_name} must be a non-empty string.",
                        "Regenerate the contract so freshness metadata uses canonical string values.",
                    )

        lineage_path = contract_path.parent / "lineage.generated.yaml"
        if lineage_path.exists():
            try:
                lineage_payload = load_yaml(lineage_path)
            except yaml.YAMLError:
                lineage_payload = None
            if isinstance(lineage_payload, dict):
                timeline = lineage_payload.get("timeline")
                if isinstance(timeline, list) and timeline:
                    missing_freshness = [
                        key for key in FEATURE_CONTRACT_FRESHNESS_KEYS if key not in payload
                    ]
                    if missing_freshness:
                        add_error(
                            findings,
                            relative_contract_path,
                            "Generated feature contract is missing freshness metadata despite completed lineage history.",
                            "Include: " + ", ".join(sorted(FEATURE_CONTRACT_FRESHNESS_KEYS)) + ".",
                        )


def validate_generated_stage_contract_schema(root: Path, findings: list[Finding]) -> None:
    for stage_path in stage_contract_files(root):
        relative_stage_path = relpath(stage_path, root)
        if not has_generated_header(stage_path):
            add_error(
                findings,
                relative_stage_path,
                "Generated stage contract must include the generated-file header.",
                "Regenerate the stage contract with the canonical architecture metadata generator.",
            )

        try:
            payload = load_yaml(stage_path)
        except yaml.YAMLError as exc:
            add_error(
                findings,
                relative_stage_path,
                f"Could not parse generated stage contract: {exc}",
                "Fix YAML syntax or regenerate the file with the canonical generator.",
            )
            continue

        if not isinstance(payload, dict):
            add_error(
                findings,
                relative_stage_path,
                "Generated stage contract must be a top-level mapping.",
                "Regenerate the file so the stage contract uses the canonical flat mapping shape.",
            )
            continue

        if len(payload) == 1:
            only_key, only_value = next(iter(payload.items()))
            if isinstance(only_value, dict) and only_key not in STAGE_CONTRACT_REQUIRED_KEYS:
                add_error(
                    findings,
                    relative_stage_path,
                    "Generated stage contract uses a legacy nested stage_id wrapper.",
                    "Regenerate the file so stage_id and generated refs live at the top level.",
                )

        missing_keys = STAGE_CONTRACT_REQUIRED_KEYS.difference(payload)
        if missing_keys:
            add_error(
                findings,
                relative_stage_path,
                "Generated stage contract is missing required keys.",
                "Include: " + ", ".join(sorted(STAGE_CONTRACT_REQUIRED_KEYS)) + ".",
            )

        stage_id = payload.get("stage_id")
        if not isinstance(stage_id, str) or not stage_id.strip():
            add_error(
                findings,
                relative_stage_path,
                "Generated stage contract must include a non-empty stage_id.",
                "Regenerate the file so the stage contract records its canonical stage_id.",
            )

        for field_name in ("name", "status", "purpose"):
            value = payload.get(field_name)
            if not isinstance(value, str) or not value.strip():
                add_error(
                    findings,
                    relative_stage_path,
                    f"Generated stage contract must include a non-empty {field_name}.",
                    "Regenerate the file so the stage contract keeps canonical top-level fields.",
                )

        if "workflow_position" in payload:
            workflow_position = payload.get("workflow_position")
            if not isinstance(workflow_position, str) or not workflow_position.strip():
                add_error(
                    findings,
                    relative_stage_path,
                    "Generated stage contract workflow_position must be a non-empty string when present.",
                    "Regenerate the file so optional workflow_position stays in canonical string form.",
                )

        for field_name in (
            "feature_refs",
            "capability_refs",
            "code_refs",
            "test_refs",
            "doc_refs",
            "config_refs",
            "component_refs",
        ):
            _validate_string_list(
                findings,
                root=root,
                lineage_path=relative_stage_path,
                capability_id=str(stage_id or stage_path.stem),
                field_name=field_name,
                value=payload.get(field_name, []),
                check_paths=field_name in {"code_refs", "test_refs", "doc_refs", "config_refs", "component_refs"},
            )

        for field_name in STAGE_CONTRACT_STRING_LIST_OPTIONAL_KEYS:
            if field_name in payload:
                _validate_string_list(
                    findings,
                    root=root,
                    lineage_path=relative_stage_path,
                    capability_id=str(stage_id or stage_path.stem),
                    field_name=field_name,
                    value=payload.get(field_name, []),
                )


def validate_managed_feature_history_structure(root: Path, findings: list[Finding]) -> None:
    for folder in feature_roots(root):
        history_path = folder / "history.md"
        if not history_path.exists():
            continue
        relative_history_path = relpath(history_path, root)
        try:
            text = history_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            add_error(
                findings,
                relative_history_path,
                f"Could not read history.md: {exc}",
                "Restore the file and keep the managed history structure intact.",
            )
            continue

        if "<!-- GENERATED HISTORY START -->" not in text:
            add_error(
                findings,
                relative_history_path,
                "history.md is missing the generated history start marker.",
                "Add the canonical generated history boundary markers and regenerate the history block if needed.",
            )
        if "<!-- GENERATED HISTORY END -->" not in text:
            add_error(
                findings,
                relative_history_path,
                "history.md is missing the generated history end marker.",
                "Add the canonical generated history boundary markers and regenerate the history block if needed.",
            )
        if "## Human Notes" not in text:
            add_error(
                findings,
                relative_history_path,
                "history.md is missing the human notes heading.",
                "Keep a human-owned ## Human Notes section below the generated history block.",
            )


def validate_generated_discovery_schema(root: Path, findings: list[Finding]) -> None:
    for path in generated_architecture_files(root):
        relative_path = relpath(path, root)
        if not has_generated_header(path):
            add_error(
                findings,
                relative_path,
                f"{path.name} must include the generated-file header.",
                "Regenerate the file with the canonical architecture metadata generator.",
            )

        try:
            payload = load_yaml(path)
        except yaml.YAMLError as exc:
            add_error(
                findings,
                relative_path,
                f"Could not parse {path.name}: {exc}",
                "Fix YAML syntax or regenerate the file with the canonical generator.",
            )
            continue

        if not isinstance(payload, dict):
            add_error(
                findings,
                relative_path,
                f"{path.name} must be a top-level mapping.",
                "Regenerate the generated discovery file so it uses the canonical mapping shape.",
            )
            continue

        if path.name == "capability_lineage.yaml":
            missing_keys = CAPABILITY_LINEAGE_REQUIRED_KEYS.difference(payload)
            if missing_keys:
                add_error(
                    findings,
                    relative_path,
                    "capability_lineage.yaml is missing required top-level keys.",
                    "Include: " + ", ".join(sorted(CAPABILITY_LINEAGE_REQUIRED_KEYS)) + ".",
                )
                continue
            features = payload.get("features")
            if not isinstance(features, dict):
                add_error(
                    findings,
                    relative_path,
                    "capability_lineage.yaml features must be a mapping.",
                    "Regenerate the file so per-feature lineage summaries stay keyed by feature ID.",
                )
                continue
            for feature_id, feature_payload in sorted(features.items()):
                if not isinstance(feature_payload, dict):
                    add_error(
                        findings,
                        relative_path,
                        f"capability_lineage.yaml features.{feature_id} must be a mapping.",
                        "Regenerate aggregate lineage so each feature summary uses the canonical mapping shape.",
                    )
                    continue
                for field_name in ("lineage_file",):
                    value = feature_payload.get(field_name)
                    if not isinstance(value, str) or not value.strip():
                        add_error(
                            findings,
                            relative_path,
                            f"capability_lineage.yaml features.{feature_id}.{field_name} must be a non-empty string.",
                            "Regenerate aggregate lineage so each feature summary records its lineage file path.",
                        )
                capability_count = feature_payload.get("capability_count")
                if not isinstance(capability_count, int):
                    add_error(
                        findings,
                        relative_path,
                        f"capability_lineage.yaml features.{feature_id}.capability_count must be an integer.",
                        "Regenerate aggregate lineage so feature summary counts stay numeric.",
                    )
                capabilities = feature_payload.get("capabilities")
                if not isinstance(capabilities, list):
                    add_error(
                        findings,
                        relative_path,
                        f"capability_lineage.yaml features.{feature_id}.capabilities must be a list.",
                        "Regenerate aggregate lineage so each feature exposes a capability summary list.",
                    )
        elif path.name == "architecture_dag.yaml":
            missing_keys = ARCHITECTURE_DAG_REQUIRED_KEYS.difference(payload)
            if missing_keys:
                add_error(
                    findings,
                    relative_path,
                    "architecture_dag.yaml is missing required top-level keys.",
                    "Include: " + ", ".join(sorted(ARCHITECTURE_DAG_REQUIRED_KEYS)) + ".",
                )
                continue
            nodes = payload.get("nodes")
            edges = payload.get("edges")
            if not isinstance(nodes, list):
                add_error(
                    findings,
                    relative_path,
                    "architecture_dag.yaml nodes must be a list.",
                    "Regenerate the file so graph nodes stay a list of structured entries.",
                )
            else:
                for index, node in enumerate(nodes):
                    if not isinstance(node, dict):
                        add_error(
                            findings,
                            relative_path,
                            f"architecture_dag.yaml nodes[{index}] must be a mapping.",
                            "Regenerate the graph so each node uses the canonical mapping shape.",
                        )
                        continue
                    for field_name in ("id", "type"):
                        value = node.get(field_name)
                        if not isinstance(value, str) or not value.strip():
                            add_error(
                                findings,
                                relative_path,
                                f"architecture_dag.yaml nodes[{index}].{field_name} must be a non-empty string.",
                                "Regenerate the graph so node identifiers and types are explicit.",
                            )
            if not isinstance(edges, list):
                add_error(
                    findings,
                    relative_path,
                    "architecture_dag.yaml edges must be a list.",
                    "Regenerate the file so graph edges stay a list of structured entries.",
                )
            else:
                for index, edge in enumerate(edges):
                    if not isinstance(edge, dict):
                        add_error(
                            findings,
                            relative_path,
                            f"architecture_dag.yaml edges[{index}] must be a mapping.",
                            "Regenerate the graph so each edge uses the canonical mapping shape.",
                        )
                        continue
                    for field_name in ("from", "to", "type"):
                        value = edge.get(field_name)
                        if not isinstance(value, str) or not value.strip():
                            add_error(
                                findings,
                                relative_path,
                                f"architecture_dag.yaml edges[{index}].{field_name} must be a non-empty string.",
                                "Regenerate the graph so edge endpoints and type are explicit.",
                            )


def validate_generated_headers(root: Path, findings: list[Finding]) -> None:
    for path in feature_source_files(root):
        if has_generated_header(path):
            add_error(
                findings,
                relpath(path, root),
                "Human-owned feature.source.yaml appears to have a generated-file header.",
                "Regenerate into the feature contract path and keep feature.source.yaml human-owned.",
            )


def validate_lineage_generated_schema(root: Path, findings: list[Finding]) -> None:
    for folder in feature_roots(root):
        lineage_path = folder / "lineage.generated.yaml"
        if not lineage_path.exists():
            continue

        relative_lineage_path = relpath(lineage_path, root)
        if not has_generated_header(lineage_path):
            add_error(
                findings,
                relative_lineage_path,
                "lineage.generated.yaml must include the generated-file header.",
                "Regenerate the lineage file with the canonical architecture metadata generator.",
            )

        try:
            payload = load_yaml(lineage_path)
        except yaml.YAMLError as exc:
            add_error(
                findings,
                relative_lineage_path,
                f"Could not parse lineage.generated.yaml: {exc}",
                "Fix YAML syntax or regenerate the file with the canonical generator.",
            )
            continue

        if not isinstance(payload, dict):
            add_error(
                findings,
                relative_lineage_path,
                "lineage.generated.yaml must be a top-level mapping.",
                "Regenerate the file so the lineage artifact uses the canonical mapping shape.",
            )
            continue

        missing_keys = REQUIRED_LINEAGE_TOP_LEVEL_KEYS.difference(payload)
        if missing_keys:
            add_error(
                findings,
                relative_lineage_path,
                "lineage.generated.yaml is missing required top-level keys.",
                "Include: " + ", ".join(sorted(REQUIRED_LINEAGE_TOP_LEVEL_KEYS)) + ".",
            )

        legacy_keys = LEGACY_LINEAGE_TOP_LEVEL_KEYS.intersection(payload)
        if legacy_keys:
            add_error(
                findings,
                relative_lineage_path,
                "lineage.generated.yaml uses legacy summary-style top-level keys.",
                "Remove legacy keys and regenerate the file with the canonical evidence-oriented lineage schema.",
            )

        capabilities = payload.get("capabilities")
        if capabilities is not None and not isinstance(capabilities, dict):
            add_error(
                findings,
                relative_lineage_path,
                "lineage.generated.yaml capabilities must be a mapping keyed by capability ID.",
                "Regenerate the file so feature-local lineage remains capability-keyed rather than list-shaped.",
            )
        elif isinstance(capabilities, dict):
            for capability_id, capability_payload in sorted(capabilities.items()):
                _validate_lineage_capability_entry(
                    findings,
                    root=root,
                    lineage_path=relative_lineage_path,
                    capability_id=capability_id,
                    value=capability_payload,
                )

        _validate_lineage_timeline(
            findings,
            root=root,
            lineage_path=relative_lineage_path,
            value=payload.get("timeline"),
        )


def contains_feature_metadata_markers(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return any(pattern in text for pattern in FEATURE_METADATA_PATTERNS)


def metadata_marker_files(root: Path) -> list[Path]:
    matches: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in METADATA_SCAN_SUFFIXES:
            continue
        relative_parts = path.relative_to(root).parts
        if relative_parts and relative_parts[0] in METADATA_SCAN_SKIP_DIRS:
            continue
        if contains_feature_metadata_markers(path):
            matches.append(path)
    return sorted(matches)


def validate_starter_method_only(root: Path, findings: list[Finding]) -> None:
    for path in feature_source_files(root):
        add_error(
            findings,
            relpath(path, root),
            "feature.source.yaml exists in starter_method_only mode.",
            "Switch to managed_architecture_metadata or remove feature metadata until adoption is chosen.",
        )
    for path in managed_feature_contracts(root):
        add_error(
            findings,
            relpath(path, root),
            "Managed feature contract exists in starter_method_only mode.",
            "Switch adoption mode or remove managed feature contracts.",
        )
    for path in generated_architecture_files(root):
        if is_empty_generated_scaffold(path):
            continue
        add_error(
            findings,
            relpath(path, root),
            "Non-empty generated architecture discovery exists in starter_method_only mode.",
            "Switch adoption mode or remove generated architecture indexes.",
        )
    for path in metadata_marker_files(root):
        add_error(
            findings,
            relpath(path, root),
            "Feature/capability metadata marker exists in starter_method_only mode.",
            "Switch adoption mode before adding feature/capability source metadata.",
        )

    features_root = root / "docs" / "features"
    if features_root.exists():
        for path in sorted(features_root.iterdir()):
            if path.name != "README.md":
                add_warning(
                    findings,
                    relpath(path, root),
                    "Non-README entry exists under docs/features in starter_method_only mode.",
                    "Confirm this is intentional prose, or switch adoption mode before adding feature metadata.",
                )
    stages_root = root / "docs" / "stages"
    if stages_root.exists():
        for path in sorted(stages_root.iterdir()):
            if path.name != "README.md":
                add_warning(
                    findings,
                    relpath(path, root),
                    "Non-README entry exists under docs/stages in starter_method_only mode.",
                    "Confirm this is intentional prose, or switch adoption mode before adding stage metadata.",
                )


def validate_managed_mode(config: AdoptionConfig, root: Path, findings: list[Finding]) -> None:
    for path in flat_feature_files(root):
        add_error(
            findings,
            relpath(path, root),
            "Flat authoritative feature YAML is not allowed in managed_architecture_metadata mode.",
            "Move semantic source into docs/features/<feature_id>/feature.source.yaml and regenerate the contract.",
        )
    for folder in feature_roots(root):
        source = folder / "feature.source.yaml"
        contract = folder / f"{folder.name}.yaml"
        lineage = folder / "lineage.generated.yaml"
        history = folder / "history.md"
        if not source.exists():
            add_error(
                findings,
                relpath(folder, root),
                "Managed feature folder is missing feature.source.yaml.",
                "Create the human-owned feature.source.yaml source file.",
            )
        if config.architecture_generator != "none" and not contract.exists():
            add_error(
                findings,
                relpath(folder, root),
                f"Managed feature folder is missing {folder.name}.yaml.",
                "Run the architecture generator to regenerate the concrete managed feature contract.",
            )
        if config.architecture_generator != "none" and not lineage.exists():
            add_error(
                findings,
                relpath(folder, root),
                "Managed feature folder is missing lineage.generated.yaml.",
                "Run the architecture generator to regenerate the feature-local lineage artifact.",
            )
        if not history.exists():
            add_error(
                findings,
                relpath(folder, root),
                "Managed feature folder is missing history.md.",
                "Add history.md using the managed history pattern with generated markers plus human notes.",
            )
    if generated_architecture_files(root) and not feature_roots(root):
        add_error(
            findings,
            "docs/generated",
            "Generated architecture discovery exists but no managed feature folders were found.",
            "Create managed feature folders or remove stale generated discovery.",
        )
    if config.architecture_generator == "none":
        add_error(
            findings,
            "repo_config/adoption-mode.yaml",
            "managed_architecture_metadata mode requires an architecture_generator.",
            "Set architecture_generator to the sync/check script path.",
        )
    if not metadata_marker_files(root):
        add_warning(
            findings,
            ".",
            "No source metadata markers were found outside docs/config roots.",
            "Confirm source metadata is intentionally deferred, or add canonical feature/capability markers.",
        )


def validate_legacy_mode(config: AdoptionConfig, root: Path, findings: list[Finding]) -> None:
    for path in feature_source_files(root):
        add_error(
            findings,
            relpath(path, root),
            "feature.source.yaml exists in legacy_compatibility mode.",
            "Switch to managed_architecture_metadata or remove managed source files.",
        )
    flat_ids = {path.stem for path in flat_feature_files(root)}
    for contract in managed_feature_contracts(root):
        if contract.stem in flat_ids:
            add_error(
                findings,
                relpath(contract, root),
                "Managed feature-folder contract exists beside a flat authoritative contract.",
                "Choose legacy compatibility or managed mode; do not keep both authoritative shapes.",
            )
    follow_up = config.payload.get("migration_follow_up")
    if not isinstance(follow_up, dict) or not follow_up.get("required"):
        add_warning(
            findings,
            "repo_config/adoption-mode.yaml",
            "legacy_compatibility mode has no required migration_follow_up.",
            "Record the follow-up migration plan or document why legacy mode is long-lived.",
        )
    if generated_architecture_files(root) and config.architecture_generator == "none":
        add_warning(
            findings,
            "docs/generated",
            "Generated architecture discovery exists without a documented legacy generator.",
            "Document the legacy generator or remove stale generated discovery.",
        )


def validate_specs_and_plans(root: Path, findings: list[Finding]) -> None:
    for folder_name in ("specs", "plans"):
        folder = root / "docs" / "superpowers" / folder_name
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "candidate_type: operating_system" in text and "targets:" not in text:
                add_error(
                    findings,
                    relpath(path, root),
                    "Operating-system spec/plan candidate is missing targets.",
                    "Add targets for affected operating-system files/folders.",
                )
            if "candidate_type: operating_system" in text and "related_features: []" not in text:
                add_warning(
                    findings,
                    relpath(path, root),
                    "Operating-system spec/plan does not explicitly clear related_features.",
                    "Use related_features: [] unless product-feature impact is intentionally documented.",
                )


def run_validation(root: Path, adoption_mode_path: Path) -> list[Finding]:
    findings: list[Finding] = []
    config = parse_adoption_config(adoption_mode_path, findings, root)

    validate_required_root_docs(root, findings)
    validate_required_project_folders(root, findings)
    validate_managed_metadata_templates(root, findings)
    validate_method_feature_ids(root, findings)
    validate_feature_dependencies(root, findings)
    validate_capability_ids(root, findings)
    validate_generated_headers(root, findings)
    validate_generated_feature_contract_schema(root, findings)
    validate_generated_stage_contract_schema(root, findings)
    validate_managed_feature_history_structure(root, findings)
    validate_generated_discovery_schema(root, findings)
    validate_lineage_generated_schema(root, findings)
    validate_specs_and_plans(root, findings)

    if config is None:
        return findings

    if config.mode == "starter_method_only":
        validate_starter_method_only(root, findings)
    elif config.mode == "managed_architecture_metadata":
        validate_managed_mode(config, root, findings)
    elif config.mode == "legacy_compatibility":
        validate_legacy_mode(config, root, findings)

    return findings


def print_findings(findings: list[Finding]) -> None:
    if not findings:
        print("Adoption shape validation passed.")
        return

    for finding in findings:
        print(f"{finding.level}: {finding.path}: {finding.message}")
        print(f"  fix: {finding.fix}")


def main() -> int:
    args = build_parser().parse_args()
    root = args.repo_root.resolve()
    adoption_mode_path = (root / args.adoption_mode).resolve()
    findings = run_validation(root, adoption_mode_path)
    print_findings(findings)
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())

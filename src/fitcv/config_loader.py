"""@meta
name: config_loader
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Loader utilities for config file discovery and YAML ingestion.
inputs:
  - Config file paths and loader callbacks
outputs:
  - Parsed config dictionaries and resolved config paths
lifecycle:
  - status: active
"""

from pathlib import Path
from typing import Any

import yaml


class _DuplicateYamlKeyError(ValueError):
    def __init__(self, key: object) -> None:
        self.key = key
        super().__init__(str(key))


class _UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise _DuplicateYamlKeyError(key)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _reject_duplicate_keys_in_sections(
    raw_yaml: str,
    *,
    source: str,
    sections: frozenset[str],
) -> None:
    root = yaml.compose(raw_yaml, Loader=yaml.SafeLoader)
    if not isinstance(root, yaml.MappingNode):
        return
    for section_key, section_value in root.value:
        if section_key.value not in sections or not isinstance(section_value, yaml.MappingNode):
            continue
        seen: set[str] = set()
        for key_node, _ in section_value.value:
            key = str(key_node.value)
            if key in seen:
                raise ValueError(f"{source}: duplicate YAML key: {key}")
            seen.add(key)


def load_yaml_text(
    raw_yaml: str,
    *,
    source: str,
    reject_duplicate_keys: bool = False,
    duplicate_key_sections: frozenset[str] = frozenset(),
) -> Any:
    if duplicate_key_sections:
        _reject_duplicate_keys_in_sections(
            raw_yaml,
            source=source,
            sections=duplicate_key_sections,
        )
    try:
        return yaml.load(
            raw_yaml,
            Loader=_UniqueKeySafeLoader if reject_duplicate_keys else yaml.SafeLoader,
        )
    except _DuplicateYamlKeyError as exc:
        raise ValueError(f"{source}: duplicate YAML key: {exc.key}") from exc


def load_yaml_file(
    path: Path,
    *,
    logger: Any,
    reject_duplicate_keys: bool = False,
    duplicate_key_sections: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    if not path.exists():
        logger.warning("Config file not found (skipping): %s", path)
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = load_yaml_text(
                f.read(),
                source=str(path),
                reject_duplicate_keys=reject_duplicate_keys,
                duplicate_key_sections=duplicate_key_sections,
            )
    except PermissionError:
        logger.warning("Config file not readable (skipping): %s", path)
        return {}
    return data if isinstance(data, dict) else {}


def load_policy_file(
    config_dir: Path,
    rel_paths: tuple[str, ...],
    *,
    load_yaml_file_fn: Any,
    logger: Any,
) -> tuple[dict[str, Any], Path]:
    for rel_path in rel_paths:
        candidate = config_dir / rel_path
        if candidate.exists():
            return load_yaml_file_fn(candidate), candidate
    preferred_path = config_dir / rel_paths[0]
    logger.warning("Config file not found (skipping): %s", preferred_path)
    return {}, preferred_path


def find_config_dir(base_path: Path) -> Path:
    candidate = base_path.parent
    for _ in range(4):
        config_dir = candidate / "config"
        if config_dir.is_dir():
            return config_dir
        candidate = candidate.parent
    return base_path.parent / "config"


def resolve_env_path(path: str | Path | None, *, default_env_candidates: tuple[str, ...]) -> Path:
    if path is not None:
        return Path(path)
    for candidate in default_env_candidates:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return candidate_path
    return Path(default_env_candidates[0])



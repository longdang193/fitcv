from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "module_path",
    [
        "fitcv_cp.app",
        "fitcv_cp.worker_job",
    ],
)
def test_replace_yaml_top_level_mapping_block_preserves_other_sections(module_path: str) -> None:
    module = __import__(module_path, fromlist=["_replace_yaml_top_level_mapping_block"])
    replace_block = getattr(module, "_replace_yaml_top_level_mapping_block")

    raw = (
        "# header\n"
        "domain_alias_map: {}\n"
        "domain_neighbors: {}\n"
    )
    updated = replace_block(
        raw_yaml=raw,
        key="domain_alias_map",
        mappings={"b": "x", "a": "y"},
    )
    assert updated.startswith("# header\n")
    assert "domain_neighbors: {}\n" in updated
    assert "domain_alias_map:\n" in updated
    assert "  a: y\n" in updated
    assert "  b: x\n" in updated


@pytest.mark.parametrize(
    "module_path,key",
    [
        ("fitcv_cp.app", "domain_alias_map"),
        ("fitcv_cp.app", "role_family_alias_map"),
        ("fitcv_cp.worker_job", "domain_alias_map"),
        ("fitcv_cp.worker_job", "role_family_alias_map"),
    ],
)
def test_replace_yaml_top_level_mapping_block_overwrites_existing_multiline(
    module_path: str,
    key: str,
) -> None:
    module = __import__(module_path, fromlist=["_replace_yaml_top_level_mapping_block"])
    replace_block = getattr(module, "_replace_yaml_top_level_mapping_block")

    raw = (
        "# header\n"
        f"{key}:\n"
        "  z: w\n"
        "  a: b\n"
        "\n"
        "some_other_key: 1\n"
    )
    updated = replace_block(
        raw_yaml=raw,
        key=key,
        mappings={"b": "x", "a": "y"},
    )
    assert "# header\n" in updated
    assert "some_other_key: 1\n" in updated
    assert "  z: w\n" not in updated
    assert "  a: b\n" not in updated
    assert f"{key}:\n" in updated
    assert "  a: y\n" in updated
    assert "  b: x\n" in updated


@pytest.mark.parametrize(
    "module_path",
    [
        "fitcv_cp.app",
        "fitcv_cp.worker_job",
    ],
)
def test_replace_yaml_top_level_mapping_block_appends_when_missing(module_path: str) -> None:
    module = __import__(module_path, fromlist=["_replace_yaml_top_level_mapping_block"])
    replace_block = getattr(module, "_replace_yaml_top_level_mapping_block")

    raw = "# header\nsome_other_key: 1\n"
    updated = replace_block(
        raw_yaml=raw,
        key="role_family_alias_map",
        mappings={"alias": "canonical"},
    )
    assert updated.startswith("# header\n")
    assert "some_other_key: 1\n" in updated
    assert "role_family_alias_map:\n" in updated
    assert "  alias: canonical\n" in updated


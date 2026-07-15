"""
@meta
type: test
scope: unit
domain: deployment
covers:
  - deployment configuration behavior
excludes:
  - live deployment provisioning
tags:
  - fast
  - ci-safe
"""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_docker_compose_mounts_runtime_config_files() -> None:
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    for service_name in ("web", "worker"):
        volumes = services[service_name]["volumes"]
        assert "./.env:/app/.env:ro" in volumes
        assert "./.env.yaml:/app/.env.yaml:ro" in volumes
        assert "./config/runtime/control_plane.yaml:/app/config/runtime/control_plane.yaml:ro" in volumes
        assert "${FITCV_LANGGRAPH_REPO_PATH:-../fitcv-langgraph}:/opt/fitcv-langgraph:ro" in volumes
        assert "FITCV_LANGGRAPH_ENV_FILE=/app/.env" not in services[service_name]["environment"]
        assert "./data:/app/data" in volumes
        assert "fitcv_runtime:/app/runtime" in volumes

    assert compose["volumes"] == {"fitcv_runtime": None}


def test_dockerfile_copies_templates_directory() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY templates/ ./templates/" in dockerfile

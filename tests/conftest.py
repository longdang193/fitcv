"""Shared pytest fixtures for fitcv tests."""
from pathlib import Path

import pytest


@pytest.fixture
def sample_jobs_path() -> Path:
    """Absolute path to the sample jobs JSON fixture."""
    return Path(__file__).parent.parent / "data" / "sample_jobs.json"


@pytest.fixture
def config() -> dict[str, object]:
    """Loaded project config from .env.yaml."""
    from fitcv.config import load_config
    return load_config(Path(__file__).parent.parent / ".env.yaml")

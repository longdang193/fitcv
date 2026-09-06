from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

SPEC = importlib.util.spec_from_file_location(
    "opendesign_profile_adapter", SCRIPTS_ROOT / "opendesign_profile_adapter.py"
)
assert SPEC is not None and SPEC.loader is not None
ADAPTER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ADAPTER
SPEC.loader.exec_module(ADAPTER)


def write_profile(root: Path, name: str = "high") -> None:
    agents = root / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{name}.toml").write_text(
        f'name = "{name}"\n'
        'model_provider = "9router"\n'
        f'model = "combo-{name}"\n'
        'description = "Profile description"\n'
        'developer_instructions = "Profile instructions"\n',
        encoding="utf-8",
    )


def test_build_start_run_request_projects_profile_into_open_design_mcp(tmp_path: Path) -> None:
    write_profile(tmp_path)

    request = ADAPTER.build_start_run_request(
        agents_root=tmp_path / "agents",
        profile_name="high",
        project="fitcv-settings-ux-audit",
        task="Inspect settings UX.",
        agent="codex",
        request_id="request-1",
    )

    assert request == {
        "agent": "codex",
        "model": "combo-high",
        "project": "fitcv-settings-ux-audit",
        "prompt": (
            "[Project OS profile: high]\n"
            "Profile instructions\n\n"
            "[OpenDesign task]\n"
            "Inspect settings UX."
        ),
        "requestId": "request-1",
    }


def test_build_start_run_request_rejects_blank_task(tmp_path: Path) -> None:
    write_profile(tmp_path)

    with pytest.raises(ValueError, match="task"):
        ADAPTER.build_start_run_request(
            agents_root=tmp_path / "agents",
            profile_name="high",
            project="fitcv-settings-ux-audit",
            task=" ",
        )

"""
@meta
name: test_render_harness_routing
type: test
domain: harness
distribution_tier: starter_kit
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_harness_routing.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_harness_routing", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rendered_routing_matches_policy() -> None:
    renderer = load_renderer()

    rendered = renderer.render(ROOT)

    assert "| `local_change` | `normal` | `implement` |" in rendered
    assert "DO NOT EDIT" in rendered


def test_check_reports_stale_output(tmp_path: Path) -> None:
    renderer = load_renderer()
    output = tmp_path / "harness-routing.generated.md"
    output.write_text("stale\n", encoding="utf-8")

    assert renderer.sync(ROOT, output, check=True) == 1
    assert renderer.sync(ROOT, output, check=False) == 0
    assert renderer.sync(ROOT, output, check=True) == 0

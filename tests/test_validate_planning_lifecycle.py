"""
@meta
type: test
scope: unit
domain: docs
covers:
  - Planning lifecycle validation for completed-workstream thread status closure
  - Checkpoint-evidence requirements for completed threads
  - Strict-mode failure behavior for warning-level lifecycle coverage findings
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path
from shutil import rmtree

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate_planning_lifecycle.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_validator(repo_root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--repo-root", str(repo_root), *extra],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def make_test_root() -> Path:
    root = REPO_ROOT / ".tmp-tests" / f"validate-planning-lifecycle-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=False)
    return root


def seed_minimum_workstream(root: Path, *, workstream_status: str, thread_status: str) -> None:
    write_text(root / "docs" / "intent" / "master-workstream-roadmap.md", "# Roadmap\n")
    write_text(
        root / "docs" / "intent" / "workstreams" / "sample-workstream.md",
        f"""---
workstream_id: sample-workstream
status: {workstream_status}
---

# Sample Workstream
""",
    )
    write_text(
        root / "docs" / "intent" / "workstreams" / "threads" / "sample-workstream" / "01-sample-thread.md",
        f"""---
thread_id: sample-workstream.sample-thread
status: {thread_status}
---

# Sample Thread
""",
    )


def test_completed_workstream_with_proposed_thread_fails() -> None:
    root = make_test_root()
    try:
        seed_minimum_workstream(root, workstream_status="completed", thread_status="proposed")
        result = run_validator(root)
        assert result.returncode == 1
        assert "non-terminal thread status" in result.stdout
    finally:
        rmtree(root, ignore_errors=True)


def test_completed_thread_without_checkpoint_evidence_fails() -> None:
    root = make_test_root()
    try:
        seed_minimum_workstream(root, workstream_status="completed", thread_status="completed")
        result = run_validator(root)
        assert result.returncode == 1
        assert "missing checkpoint evidence" in result.stdout
    finally:
        rmtree(root, ignore_errors=True)


def test_warning_only_without_strict_passes_but_strict_fails() -> None:
    root = make_test_root()
    try:
        seed_minimum_workstream(root, workstream_status="active", thread_status="proposed")
        result_normal = run_validator(root)
        result_strict = run_validator(root, "--strict")
        assert result_normal.returncode == 0
        assert result_strict.returncode == 1
    finally:
        rmtree(root, ignore_errors=True)

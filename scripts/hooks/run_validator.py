"""
Run the repo-contract validator from a stable repo-root entrypoint.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    root = repo_root()
    cmd = [sys.executable, str(root / "scripts" / "validate_repo_contracts.py"), *argv]
    return subprocess.run(cmd, cwd=root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

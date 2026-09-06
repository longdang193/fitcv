"""Project OS profile projection for OpenDesign MCP start_run requests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from agent_profile_registry import AgentProfile, load_agent_profiles
except ModuleNotFoundError:
    from scripts.agent_profile_registry import AgentProfile, load_agent_profiles


DEFAULT_AGENT = "codex"


def _load_profile(agents_root: Path, profile_name: str) -> AgentProfile:
    try:
        profiles = load_agent_profiles(agents_root)
    except (OSError, ValueError) as exc:
        raise ValueError(str(exc)) from exc
    profile = profiles.get(profile_name)
    if profile is None:
        raise ValueError(f"Unknown agent profile: {profile_name}")
    return profile


def _compose_prompt(profile: AgentProfile, task: str) -> str:
    task = task.strip()
    if not task:
        raise ValueError("OpenDesign task must be non-empty.")
    return (
        f"[Project OS profile: {profile.name}]\n"
        f"{profile.developer_instructions.strip()}\n\n"
        f"[OpenDesign task]\n{task}"
    )


def build_start_run_request(
    *,
    agents_root: Path,
    profile_name: str,
    project: str,
    task: str,
    agent: str = DEFAULT_AGENT,
    request_id: str | None = None,
) -> dict[str, str]:
    project = project.strip()
    agent = agent.strip()
    if not project:
        raise ValueError("OpenDesign project must be non-empty.")
    if not agent:
        raise ValueError("OpenDesign agent must be non-empty.")

    profile = _load_profile(agents_root, profile_name)
    request: dict[str, str] = {
        "agent": agent,
        "model": profile.model,
        "project": project,
        "prompt": _compose_prompt(profile, task),
    }
    if request_id is not None:
        request_id = request_id.strip()
        if not request_id:
            raise ValueError("OpenDesign request ID must be non-empty when provided.")
        request["requestId"] = request_id
    return request


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--agent", default=DEFAULT_AGENT)
    parser.add_argument(
        "--agents-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "agents",
    )
    parser.add_argument("--request-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        request = build_start_run_request(
            agents_root=args.agents_root,
            profile_name=args.profile,
            project=args.project,
            task=args.task,
            agent=args.agent,
            request_id=args.request_id,
        )
    except ValueError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(request, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

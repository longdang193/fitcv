from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_chief_of_staff_has_single_required_read_and_clear_ownership() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    assert "name: skill-chief-of-staff" in skill
    assert "required_reads: []" in skill
    assert "`skill-executing-plans` owns\napproved-plan execution" in skill
    assert "CoS has no direct Git or PR authority" in skill
    assert "`deepagents` uses `dcode-project`" in " ".join(skill.split())
    assert "`tura` uses `project-delegate`" in skill
    assert "top-level lane selection" in skill


def test_chief_of_staff_has_deterministic_binding_runtime_and_status_contract() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    for text in (
        "explicit supplied plan path",
        "plan already bound by the current execution context",
        "exactly one active plan matching the current repository and worktree",
        "otherwise return `BLOCKED`",
        "discovered `herdr` executable and version",
        "discovered `codex` executable and version",
        "DeepAgents implementation lane",
        "bounded worker wait, timeout, exit, and descendant-cleanup evidence",
        "`CODEX_HOME`",
        "required MCP/tool surface",
        "launched process cwd",
        "native Codex lead controller",
        "Template Profile` selects the\nprofile contract",
        "agents/*.toml` owns its profile identity",
        "selected profile, resolved model, and Herdr launch binding",
        "scripts/herdr_main_launcher.py",
        "CoS may be invoked from a native Codex session",
        "verifies target lane readiness, Git/cwd identity,\nruntime/profile binding, and task delivery",
        "does not attest CoS controller\nidentity or own lane authority",
        "Top-level MAIN AGENTS are CoS execution lanes; sub-agents are subordinate lane\nworkers.",
        "CoS assigns top-level\nMAIN AGENTS through Herdr.",
        "MAIN\nAGENT may spawn Native Codex, DeepAgents, or Tura sub-agents when needed",
        "Before local dispatch, run\n`py -B scripts/validate_agent_runtime_drift.py`",
        "`--skip-deploy-check` is CI-only",
        "CoS verifies the full lane contract",
        "launcher owns\nruntime projection, exact pane/cwd checks, Git-fact reporting, and delivery\nmechanics",
        "Do not construct provider, model, or developer-instruction overrides\nin CoS",
        "DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT |",
        "PASS | FAIL | BLOCKED",
    ):
        assert text in skill


def test_chief_of_staff_requires_cold_start_dispatch_evidence() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    for text in (
        "Treat every explicit CoS turn as a cold start",
        "never use prior\nassistant prose, runtime-thread state, or memory as proof",
        "`DISPATCH` - use the repository launcher, then record its returned evidence;",
        "`CONTINUE` - reuse a live lane only after fresh identity and binding checks",
        "Selecting a profile, writing a brief, naming a lane, or stating intent is not\nassignment",
        "successful final delivery evidence\nfrom the repository launcher",
        "Missing or failed delivery evidence is a blocker",
    ):
        assert text in skill


def test_chief_of_staff_preserves_lifecycle_boundaries() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    for text in (
        "one exact branch and isolated worktree",
        "Implementation lanes may implement, commit,\npush, and manage their assigned PR when granted",
        "Independent Codex review lanes\nown assigned review actions",
        "A designated Codex integration action owns an exact\napproved PR merge after review and verification gates pass",
        "Project OS\nreview is separate from GitHub review state",
        "Required distinct-identity approval returns\n`BLOCKED`",
        "retire or stop the\nHerdr top-level lane",
        "Never let an agent remove the worktree\nfrom which it is running",
        "Do not require, create, or treat `identity.md`",
        "Herdr owns transient\nprocess observation only",
        "Branch and PR publication may occur after accepted lane proof",
        "Final merge and lane cleanup require whole-plan verification",
    ):
        assert text in skill
    assert "event-driven" not in skill.lower()


def test_chief_of_staff_defines_explicit_turn_attention_audit() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    audit = skill.index("### Attention Audit")
    work_binding = skill.index("## Work Binding")
    plan_binding = skill.index("## Plan Binding")
    next_action = skill.index("Select one dependency-ready task")
    assert work_binding < audit < plan_binding < next_action
    normalized = " ".join(skill.split())
    for text in (
        "On each explicit CoS turn with outstanding CoS-coordinated work",
        "after Work Binding and before selecting the mode-specific next action",
        "plan-bound execution inspects the current plan/task, Git/worktree, applicable PR/review, and expected Herdr lane evidence",
        "NO_ACTION | INSPECT | BLOCKED",
        "NO_ACTION` - evidence is consistent with the current lifecycle phase.",
        "INSPECT` - CoS judgment or an approved in-scope correction is needed.",
        "BLOCKED` - an existing canonical blocking condition prevents safe progress.",
        "Consume blocking and verification semantics from their canonical owners",
        "Herdr absence alone is not a blocker",
        "current plan or current-turn evidence establishes that a live bound agent is expected",
        "attention_target",
        "Audit outcomes are advisory attention results, not workflow-state transitions.",
        "does not mutate plan, Git, PR state, Herdr, authority, or durable coordination state",
        "This contract has no autonomous wake mechanism, timer, scheduler, helper-agent dispatch, new profile, hook integration, or persistent heartbeat state.",
        "No polling or subscription mechanism is implied by this skill.",
    ):
        assert text in normalized


def test_chief_of_staff_defines_canonical_work_modes_and_advisory_boundaries() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    normalized = " ".join(skill.split())
    for text in (
        "Work identity",
        "evidence authority",
        "reference anchors",
        "source-relative freshness boundary",
        "acceptance authority",
        "Coordination mode: `advisory` or `plan-bound-execution`",
        "Repository Snapshot Advisory Binding",
        "exact commit SHA",
        "repository identity",
        "scoped target",
        "Advisory CoS may inspect, synthesize, challenge, and recommend",
        "Advisory CoS has no mutation authority",
        "explicit current-work owner",
        "canonical work owner",
        "existing repository or workflow authority",
        "source-relative freshness",
        "Remote or immutable inspection needs no worktree",
        "local tools can mutate",
        "CoS must not activate for PR, release, incident, specification, research, or cross-repository work",
        "CoS coordinates work; it does not own work execution or canonical work truth",
    ):
        assert text in normalized
    assert "authority class: inspect | recommend | execute" not in skill
    assert "required_reads:\n  - docs/operating_system/rules/git-tracked-coordination-rule.md" not in skill


def test_chief_of_staff_keeps_plan_execution_mode_specific() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    normalized = " ".join(skill.split())
    for text in (
        "Plan-bound execution mode",
        "Plan Binding applies only to `plan-bound-execution`",
        "Attention Audit applies to both coordination modes",
        "Select one dependency-ready task only in `plan-bound-execution`",
        "`skill-executing-plans` remains the sole approved-plan execution owner",
    ):
        assert text in normalized


def test_chief_of_staff_exposes_attention_and_freshness_output_contract() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    normalized = " ".join(skill.split())
    assert "`attention_result`, optional `attention_target`" in normalized
    assert "Runtime evidence must be fresh for the current turn" in normalized
    assert "Reviewer read-only behavior is instruction-level" in skill
    assert "substantial independent detour, park the current lane" in normalized


def test_chief_of_staff_blocks_delegated_reactivation_and_separates_returns() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    assert "Sub-agents must not spawn peer MAIN AGENTS, activate CoS, or\nreactivate coordination" in skill
    assert "execution returns to `DONE | DONE_WITH_CONCERNS |" in skill
    assert "never converts execution\nstatus into a review verdict" in skill


def test_chief_of_staff_defines_bounded_lane_autonomy() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    normalized = " ".join(skill.split())
    for text in (
        "## Bounded Lane Autonomy (plan-bound execution)",
        "executes autonomously inside its assigned task contract",
        "Delegation inside lane scope does not need a separate CoS approval",
        "inherits a subset of its parent task's scope, authority",
        "never expand them",
        "remains accountable for subordinate writes and evidence",
        "returns control at declared task completion or when it reaches a coordination boundary",
        "CoS acceptance remains required for task completion",
        "Explicit-turn attention governs wake-up, not progress within an active run",
        "without asking the user between tasks",
    ):
        assert text in normalized


def test_parallel_dispatch_defers_cos_top_level_fanout_to_herdr() -> None:
    dispatch = read(".agents/skills/skill-dispatching-parallel-agents/SKILL.md")
    normalized = " ".join(dispatch.split())
    assert "top-level parallel fan-out uses Herdr MAIN AGENT lanes" in normalized
    assert "Platform-native parallel dispatch applies only to ordinary non-CoS execution or subordinate work" in normalized
    assert "CoS never directly dispatches sub-agents" in normalized


def test_git_tracked_coordination_claim_cannot_expand_through_delegation() -> None:
    rule = read("docs/operating_system/rules/git-tracked-coordination-rule.md")
    normalized = " ".join(rule.split())
    assert "active task or wave plus declared ownership, dependencies, authority, and Git workspace is the durable coordination claim" in normalized
    assert "Subordinate delegation may narrow that claim but never expand its ownership, authority, or allowed paths" in normalized


def test_chief_of_staff_uses_herdr_for_top_level_lane_dispatch() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    assert "CoS may dispatch only top-level MAIN AGENT lanes through Herdr." in skill
    assert "Every CoS lane dispatch goes through Herdr" in skill
    assert "`scripts/herdr_main_launcher.py`" in skill
    assert "Monitor only the\ntop-level lane and wrapper" in skill
    assert "never invokes subagents directly" in skill
    assert "The launcher owns\nruntime projection, exact pane/cwd checks, Git-fact reporting, and delivery\nmechanics" in skill
    for forbidden in (
        "`multi_agent_v1`",
        "native Codex subagents",
        "DeepAgents internal `task` workers",
        "Tura internal workers",
        "executor-local reviewers or helpers",
    ):
        assert forbidden in skill
    assert "Independent review and integration remain Codex-only." in skill
    assert "Reuse `implementation-main` only when its\nexecutor is `codex`" in skill


def test_executor_skill_keeps_cos_as_codex_controlled() -> None:
    skill = read(".agents/skills/skill-executing-plans/SKILL.md")
    assert "lists `skill-chief-of-staff` in `Required skills`" in skill
    assert "only a Herdr-\nsupervised top-level Codex main agent or bounded DeepAgents pane process" in skill
    assert "CoS must not call `multi_agent_v1`, native Codex subagents" in skill
    assert "`dcode-project` for `deepagents`" in skill
    assert "project-delegate` for `tura`" in skill


def test_planning_dispatch_selects_cos_for_sustained_implementation_coordination() -> None:
    dispatch = read("docs/operating_system/planning/planning-dispatch.md")
    assert "## Coordination Method Selection" in dispatch
    assert "as an optional\ncoordination specialization of" in dispatch
    assert "Git-tracked plan lists `skill-chief-of-staff` in `Required skills`" in dispatch
    assert "canonical CoS\nopt-in signal" in dispatch
    normalized = " ".join(dispatch.split())
    assert "sustained handoffs, independent top-level lanes" in normalized
    assert "Select `skill-chief-of-staff` in `advisory` mode" in dispatch
    assert "Advisory mode needs no plan or" in dispatch
    assert "does not add an executor, profile, plan field, or durable state artifact" in " ".join(dispatch.split())
    assert "Herdr is\nruntime observation and top-level lane supervision" in dispatch
    assert "only independent Herdr top-level MAIN AGENT\nlanes" in dispatch
    assert "never calls\n`multi_agent_v1`, native Codex subagents" in dispatch
    assert "`tura` retains\nits existing peer executor path" in dispatch


def test_main_agents_can_delegate_without_granting_peer_authority() -> None:
    template = read("AGENTS.md")
    execution = read(".agents/skills/skill-executing-plans/SKILL.md")
    deepagents = read(".agents/skills/skill-deepagents-executing-plans/SKILL.md")
    for text in (
        "MAIN AGENTS own assigned lanes and may spawn Native Codex, DeepAgents, or Tura",
        "Sub-agents remain subordinate to their parent lane",
        "Assigned MAIN AGENTS may spawn Native Codex, DeepAgents, or Tura",
        "must not spawn peer MAIN AGENTS or activate CoS",
        "MAIN AGENTS may use nested delegation when needed within assigned lane scope",
    ):
        assert text in " ".join((template + execution + deepagents).split())


def test_planning_dispatch_defines_observable_level_2_readiness() -> None:
    dispatch = read("docs/operating_system/planning/planning-dispatch.md")
    section = dispatch.split("## Level-2 Readiness Evidence", 1)[1].split("## Delivery Lifecycle", 1)[0]
    normalized = " ".join(section.split())
    for text in (
        "approved Git-tracked plan opts into CoS",
        "two independent write-capable lanes",
        "verified Herdr runtime identity",
        "expected head SHA",
        "stale-head evidence blocks acceptance",
        "retires its Herdr session",
        "resume from plan plus Git",
        "focused contract tests, adapter sync, repository validation, and diff checks",
        "do not create a Level-2 registry",
    ):
        assert text in normalized


def test_planning_dispatch_defines_cos_executor_eligibility_overlay() -> None:
    dispatch = read("docs/operating_system/planning/planning-dispatch.md")
    section = dispatch.split("### CoS Executor Eligibility", 1)[1]
    normalized = " ".join(section.split())
    for text in (
        "Generic executor selection chooses task executor",
        "CoS eligibility limits which selected executors CoS may dispatch through Herdr",
        "`codex`: implementation, review, integration, acceptance, MCP, connected tools",
        "`deepagents`: bounded repo-local implementation lane",
        "`tura`: not a CoS Herdr lane",
        "CoS coordinates only eligible `codex` and `deepagents` lanes",
        "CoS does not translate or reroute it",
        "CoS resumes from plan and Git after reconciliation",
    ):
        assert text in normalized


def test_chief_of_staff_references_cos_executor_eligibility_contract() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    assert "Apply the CoS Executor Eligibility contract from" in skill
    assert "`docs/operating_system/planning/planning-dispatch.md`" in skill


def test_chief_of_staff_keeps_deepagents_implementation_outside_review_integration() -> None:
    skill = read(".agents/skills/skill-chief-of-staff/SKILL.md")
    normalized = " ".join(skill.split())
    assert "Review and integration remain Codex-only" in normalized
    assert "Independent Codex review lanes own assigned review actions" in normalized
    assert "Every top-level lane launch, and every Codex session reuse" in normalized


def test_planning_dispatch_uses_executor_neutral_top_level_lane_terms() -> None:
    dispatch = read("docs/operating_system/planning/planning-dispatch.md")
    assert "For every Herdr top-level CoS lane launch" in dispatch

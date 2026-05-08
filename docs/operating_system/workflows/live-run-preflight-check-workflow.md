---
name: live-run-preflight-check-workflow
description: Validate live-run prerequisites before execution so evidence can be captured
  and results are trustworthy.
allowed-tools: []
required_reads:
- docs/operating_system/prompt_templates/README.md
required_outputs:
- preflight readiness report
- missing prerequisites and unblock actions
related_skills:
- planning-dispatch
- executing-plans
tags:
- workflow
- execution
- change
workflow_id: live-run-preflight-check
type: workflow
stage: execution
owner_layer: change
entry_points:
- scenario set exists and run readiness must be verified
- execution/debugging requires environment or evidence-path readiness checks
prerequisites:
- selected scenario and target run path are identified
- access to environment and observability surfaces is available
next_steps:
- live-run-execution-workflow.md
- live-run-scenario-planning-workflow.md
status: active
validators:
- readiness checks include artifacts, observability, trace IDs, environment
---

# Live Run Preflight Check Workflow

## Goal

Validate live-run prerequisites before execution so evidence can be captured and
results are trustworthy.

## Execution Flow

1. Validate required artifacts exist for selected scenario.
2. Validate observability is enabled for required telemetry surfaces.
3. Validate traceability IDs are present/resolvable.
4. Validate environment and configuration match intended run target.
5. Confirm evidence capture paths for outputs and intermediate artifacts.
6. Produce pass/fail readiness decision with minimal unblock actions.

## Decision Gates

1. Artifact gate:
   - fail preflight if required artifacts are missing.
2. Observability gate:
   - fail preflight if required logs/traces/metrics cannot be captured.
3. Traceability gate:
   - fail preflight if run evidence cannot be linked to scope.
4. Environment gate:
   - fail preflight if environment is invalid for scenario intent.

## Exit Criteria

- Preflight pass with ready evidence paths, or
- Preflight fail with explicit minimal prerequisites to unblock.


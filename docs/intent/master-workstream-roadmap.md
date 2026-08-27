---
layer: intent
artifact_type: roadmap
name: master-workstream-roadmap
status: active
registered_workstreams:
  - workstream-fitcv-local-experience
  - workstream-candidate-profile-lifecycle
  - workstream-job-collection-and-scans
  - workstream-job-evaluation-and-personalization
  - workstream-grounded-cv-generation-and-review
  - workstream-run-continuity-and-recovery
  - workstream-decision-and-history-truth
  - workstream-reliability-and-diagnostics
  - workstream-efficiency-and-cost-control
---

# Master Workstream Roadmap

## Goal

Deliver Personal FitCV for one trusted user on a Windows computer they control.
The roadmap organizes work around the personal job-search journeys and evidence
in `success-outcomes.md`, not around the historical architecture program that
produced them.

## Product Completion Boundary

Personal FitCV is complete when the personal-use journeys and evidence gates in
`success-outcomes.md` pass.

The roadmap distinguishes product completion from ongoing engineering:

- `completion-critical` work directly enables a declared completion journey
- `supporting` work improves reliability, diagnosis, efficiency, or quality but does not block completion unless promoted
- `maintenance` work preserves completed behavior after completion
- `deferred` work remains outside the current completion target

Downstream work may decompose these categories, but may not promote work into a
completion blocker without an explicit intent update.

The registered names below define current roadmap ownership. This update does
not create or rename child workstream files; historical artifacts remain
migration evidence until their disposition is handled deliberately.

## Key Deliverables

- complete the personal journey from FitCV Local setup through grounded CV review and return use
- keep Candidate Profile, Scan, Run, fit, bookmark, interest, personalization, and CV behavior truthful across user-visible history
- preserve clear failure, recovery, credential, and data-control behavior
- keep supporting, maintenance, and deferred work from becoming completion blockers by implication

## Completion-Critical Workstreams

- `workstream-fitcv-local-experience` - setup, local data control, normal operation, and shutdown through FitCV Local
- `workstream-candidate-profile-lifecycle` - create, review, confirm, revise, archive, restore, and select Candidate Profiles
- `workstream-job-collection-and-scans` - collect jobs through supported Scans or supplied inputs, inspect results, reuse successful Scans, and use them in Runs
- `workstream-job-evaluation-and-personalization` - explain fit, record interest, bookmark jobs, and optionally prioritize future jobs without changing suitability
- `workstream-grounded-cv-generation-and-review` - prepare, validate, review, and download grounded CV output without unsupported claims
- `workstream-run-continuity-and-recovery` - start Runs, follow lifecycle state, inspect results, return later, and recover from interruption or failure
- `workstream-decision-and-history-truth` - preserve evidence, explanations, profile snapshots, prior decisions, and user-visible historical truth across product surfaces

## Supporting Workstreams

- `workstream-reliability-and-diagnostics` - support truthful diagnosis and recovery without making advanced monitoring or telemetry a completion prerequisite
- `workstream-efficiency-and-cost-control` - reduce avoidable analysis and CV-generation cost without changing product meaning
- synonym review and improvement - remain optional supporting work, not a top-level completion pillar

## Maintenance

- `operating_system.docs-and-contract-hygiene` - preserve documentation and contract ownership
- `operating_system.repo-governance-and-publication-boundary` - preserve private/public publication boundaries
- `operating_system.starter-shared-surface-sync` - preserve shared starter surfaces without overwriting product truth
- `operating_system.agent-workflow-reliability` - preserve validator, skill, and agent reliability

## Deferred

- public Internet service operation and high-availability deployment
- broader website coverage beyond supported FitCV job scans
- large-scale architecture, developer/server deployment expansion, and public-release hardening
- optional observability, portability, scalability, and other infrastructure improvements that do not address a demonstrated personal-use gap

## Personal Journey Map

The roadmap follows this product sequence:

1. set up and use FitCV Local
2. build and maintain a Candidate Profile
3. collect or add jobs through supported Scans and job inputs
4. start a Run and understand narrowing, fit, and user feedback
5. save jobs and optionally use personalization
6. prepare and review a grounded CV
7. return to prior profiles, Runs, jobs, bookmarks, feedback, and recovery state

Each completion-critical workstream must map to one or more of these journeys
and to representative evidence in `success-outcomes.md`.

## Historical Workstream Disposition

Historical workstreams remain evidence and do not automatically remain
completion-critical:

| Historical workstream | Current disposition |
| --- | --- |
| `workstream-fitcv-semantic-spine` | migrate relevant stage-meaning and acceptance responsibilities into `workstream-decision-and-history-truth`; preserve remaining semantics as maintenance |
| `workstream-operator-control-plane` | split responsibilities across local experience, Candidate Profile, Scan, and Run continuity workstreams |
| `workstream-deterministic-acceptance-and-artifact-truth` | completed foundation; preserve its truth obligations through decision/history maintenance and completion evidence |
| `workstream-bounded-agentic-cv-quality` | migrate product-facing responsibilities into `workstream-grounded-cv-generation-and-review` |
| `workstream-agentic-observability` | migrate needed diagnosis and recovery responsibilities into `workstream-reliability-and-diagnostics`; keep infrastructure enhancements supporting |
| `workstream-agentic-synonym-management` | optional supporting child work; not registered as a completion-critical master workstream |
| `workstream-pipeline-efficiency-and-reuse` | migrate into `workstream-efficiency-and-cost-control` as supporting optimization |

Migration does not require immediate bulk renaming. Do not rewrite historical
child references merely to make names look current; create or rename downstream
artifacts only when an active work item needs them.

## Remaining Completion Alignment

Current work should focus only on gaps demonstrated against the declared
personal-use journeys, including:

- missing or misleading user experience
- broken continuity between product areas
- incomplete Scan, Run, profile, bookmark, personalization, or CV behavior
- incomplete failure or recovery behavior
- incorrect historical state
- unsupported or ungrounded recommendations or CV content
- regressions in normal personal use

Architecture, observability, scalability, or platform work does not become
completion-critical unless a demonstrated product gap requires it.

## Workstream Completion

A completion-critical workstream is complete when the Success Outcomes it owns
have representative acceptance evidence and no unresolved blocker prevents the
declared Personal FitCV journey.

Supporting and maintenance descendants do not have to be exhausted or closed
for the product workstream to be complete.

New work becomes completion-critical only through an explicit update to the
intent layer.

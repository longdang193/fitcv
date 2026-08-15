---
name: skill-backend-verification
description: Use when material backend behavior needs direct boundary, failure, state, dependency, contract, or trace proof whether or not a frontend exists.
required_reads: []
distribution_tier: starter_kit
---

# Backend Verification

## Role

Prove backend behavior directly before consumer or frontend integration. Follow `docs/operating_system/rules/backend-verification-rule.md`; use `docs/operating_system/tooling/frontend-backend-integration-tools.md` only when contract, MCP, browser, or cross-boundary routing applies.

## Method

1. Define changed claims: entry boundary, business result, important failures, final state or side effects, rollback or idempotency, dependencies, contract, traceability, and performance only when claimed.
2. Exercise backend through nearest real boundary: HTTP handler, service API, command, worker input, queue message, scheduled entrypoint, or webhook receiver.
3. Prove success and important failure behavior. Validate trust-boundary inputs and authorization where applicable.
4. Assert durable state and side effects. Include rollback, retry, duplicate delivery, idempotency, or partial-failure behavior when material.
5. Run contract proof when canonical contract governs changed behavior, using repository-supported contract checks.
6. Run real-dependency proof when database, queue, cache, filesystem, external service, or infrastructure semantics are material. Avoid mocks that erase behavior under test.
7. Reconstruct one representative operation using existing logs, correlation or trace IDs, job/message IDs, dependency records, or test instrumentation when traceability is material.
8. Run fresh focused automated checks and record exact command, exit status, failures, skips, and relevant evidence.
9. Hand failures to `skill-systematic-debugging`, implementation loops to `skill-test-driven-development`, consumer integration to `skill-full-stack-integration`, and final claims to `skill-verification-before-completion`.

## Evidence Output

- direct boundary exercised
- success and important failures proven
- final state and side effects asserted
- rollback/idempotency disposition
- contract and real-dependency disposition
- representative-operation trace mechanism and result when applicable
- fresh automated command and result
- remaining blocker or `none`

Frontend, browser, client, mock, and MCP output may support evidence but never replace direct backend proof.

# Reproduction Steps

1. Run focused regression command from Phase 8 plan.
2. Run `docker compose build web worker`.
3. Run `docker compose run --rm web python -c "import cvxpy as cp; assert 'CLARABEL' in cp.installed_solvers()"`.
4. Run architecture, planning, hook, repo-contract, and diff validators from plan.

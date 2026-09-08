# Scan provider catalog live probes

Date: 2026-09-08

Initial probes used public HTTP GETs, plus read-only Gem GraphQL POST list/detail
probes. No credentials or cookies were used. GraphQL request bodies contained
read-only queries and were not retained. No mutation operations were used.
Checksums cover disposable response bodies only and are not catalog approval
evidence.

| target | provider/board | host | status | bytes | keyword matches | response SHA-256 | result |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `https://www.anthropic.com/careers` | Anthropic careers | `www.anthropic.com` | 200 | 249259 | n/a | not retained | reachable; linked `/careers/jobs` |
| `https://openai.com/careers/` | OpenAI careers | `openai.com` | 403 | n/a | n/a | not retained | blocked by public endpoint |
| `https://elevenlabs.io/careers` | ElevenLabs careers | `elevenlabs.io` | 200 | 684780 | n/a | not retained | reachable; ATS not identified from page |
| `https://retool.com/careers` | Retool careers | `retool.com` | 200 | 558630 | n/a | not retained | reachable; links `jobs.gem.com/retool` |
| `https://n8n.io/careers/` | n8n careers | `n8n.io` | 200 | 288886 | n/a | not retained | reachable; embeds Ashby `jobs.ashbyhq.com/n8n` |
| `https://job-boards.greenhouse.io/anthropic` | Greenhouse | `job-boards.greenhouse.io` | 200 | 69436 | 361 | `957b94dfc1f6f58c1597ab543c57bb38063164e236d005799fee87af6b220ba3` | reachable; parser approval still missing |
| `https://jobs.ashbyhq.com/openai` | Ashby | `jobs.ashbyhq.com` | 200 | 322171 | 29 | `072a1f488d5328bcc96d81cf6e28d37a8a0cccb87f0c7c8617d74ccf53eabc5e` | reachable; parser approval still missing |
| `https://jobs.ashbyhq.com/elevenlabs` | Ashby | `jobs.ashbyhq.com` | 200 | 134784 | 29 | `d657c44faaf83a58671a5c7a074bc6b28e962da1002e733a88fa8a8e26bd0894` | reachable; parser approval still missing |
| `https://jobs.ashbyhq.com/n8n` | Ashby | `jobs.ashbyhq.com` | 200 | 62889 | 29 | `0bc6a54a8c86a4f089667dc9f258d288b55bba6f6571daefb7a69cf0add896cc` | reachable; parser approval still missing |
| `https://jobs.gem.com/retool` | Retool board | `jobs.gem.com` | 200 | 4104 | 11 | `5ecd4b09e9d97764cd437e63210fb9f768c4586fcc9d64b8e8d935395b76064d` | reachable; public Gem board |
| `https://jobs.lever.co/anthropic` | Lever | `jobs.lever.co` | 404 | n/a | n/a | not retained | negative control |
| `https://jobs.ashbyhq.com/anthropic` | Ashby | `jobs.ashbyhq.com` | 200 | 7319 | 3 | `6530e65bc27e72c96525454f499ff39472651a85947164f86146e423f3c6f7b7` | reachable response; not approved |
| `https://boards.greenhouse.io/anthropic` | Greenhouse legacy host | `boards.greenhouse.io` | 301 | n/a | n/a | not retained | redirect; no redirect-follow approval |
| `https://jobs.personio.de/anthropic` | Personio | `jobs.personio.de` | DNS failure | n/a | n/a | not retained | negative control |
| `https://anthropic.wd1.myworkdayjobs.com/Careers` | Workday | `anthropic.wd1.myworkdayjobs.com` | 500 | n/a | n/a | not retained | negative control |

## Parser probes

Bounded public ATS API GETs passed provider parsers. Response bodies were hashed
and discarded; retained job counts reflect bounded output.

| catalog ID | provider | API host | status | bytes | jobs | response SHA-256 | parser result |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `company-anthropic` | Greenhouse | `boards-api.greenhouse.io` | 200 | 8493747 | 5 | `10a7069e5229a024c72a7ea25003d2ea450523df32bc60435f3136ae16ea5530` | canonical fields passed |
| `company-openai` | Ashby | `api.ashbyhq.com` | 200 | 12931026 | 5 | `4da8f5e32ef49588dbcbac94b646d6eaafadea7afdbed1bbc15e1999f4a21a73` | canonical fields passed |
| `company-elevenlabs` | Ashby | `api.ashbyhq.com` | 200 | 3568744 | 5 | `0b07bfcc9199253f935277393ae0d26c98000f11f4e059926e71a3839b3c2c08` | canonical fields passed |
| `company-n8n` | Ashby | `api.ashbyhq.com` | 200 | 953905 | 5 | `f2b02a00aa0cda2191b1df28ff9590b8e3207b79c48a91e87729b734923bb736` | canonical fields passed |
| `company-retool` | Gem | `jobs.gem.com/api/public/graphql` | 200 | not retained | 1 | not retained | accepted: public list/detail GraphQL payload produced one job; canonical fields and schema validation passed; catalog revision `2026-09-08-v3` |

## Approval gate

The user-approved probe set supplies stable IDs, canonical ATS URLs, and
provider scope for Anthropic, OpenAI, ElevenLabs, n8n, and Retool. Existing
parsers pass for four profiles; the accepted Retool Gem record above proves
both list and detail parsing. All five records are verified in
`config/scan_catalog.yaml`.

## Safety review

- No credentials or cookies were used. GraphQL request bodies contained
  read-only queries and were not retained. No mutation operations were used.
- No automated test may call these URLs.
- Gem probe used read-only public GraphQL POSTs to `jobs.gem.com`; no mutation
  operations or credentials used.

## Current-worktree checks

| command | result |
| --- | --- |
| `python -m pytest tests/test_job_sources.py -q` | PASS: 29 passed |
| `python -m pytest tests/test_fitcv_cp/test_scan_contracts.py -q` | PASS: 16 passed |
| `python -m pytest tests/test_fitcv_cp/test_app.py -k company_catalog -q` | PASS: 4 passed |
| `npm --prefix frontend test -- --run src/test/scans.test.ts src/test/vite-proxy.test.ts` | PASS: 12 passed |
| `npm --prefix frontend run typecheck` | BLOCKED by unrelated existing diagnostics in `src/test/feature-ux-consistency.test.tsx` and `src/test/job-evaluation.test.ts` |
| `python -m pytest ... -k 'catalog or tracked_company or scan_routes or snapshot or migration' -q` | BLOCKED only by preserved deleted `data/candidate_profile.v2.sample.yaml`; catalog/Scan checks passed |
| `git diff --check` | PASS; existing CRLF conversion warnings only |

# Candidate Profile Prototype Drift Audit

## 1. Authority and incident status

- Presentation SSOT: `docs/fitcv-settings-ui-prototype.html`.
- Approved blob: `989af611bd7767c148022c79ac00c5069d8a3956`.
- Runtime lane: `codex/canonical-candidate-frontend-first-backend-integration`.
- Backend integration gate: closed.
- Prior mock browser approval: invalidated.
- Remediation status: verified; corrected mock approved August 3, 2026.
- Port `8765`: occupied by Anki (`pythonw`, PID `15960` on August 3, 2026) and forbidden for FitCV mock, audit, or test servers.

## 2. Executive finding

Runtime was not built from prototype components. It was manually translated into independent Jinja markup, independent CSS, independent Python fixtures, and permissive string-based tests. Prototype hash equality proved only that approved artifact existed; it did not prove served UI consumed or matched it.

This produced repeated SSOT violations:

1. prototype owned reviewed presentation;
2. field registry also claimed presentation metadata;
3. plan, UI Intent, templates, CSS, fixtures, and tests restated portions of same presentation;
4. implementation could satisfy tests while visibly disagreeing with prototype.

## 3. User-visible evidence

Controlled Derivation originally demonstrated drift; corrected runtime now matches approved contract:

| Contract | Prototype | Served mock | Result |
|---|---|---|---|
| collection body | `.collection-list` | `.collection-list` | aligned |
| entry header | `.derived-entry-head` plus `.field-action-row` | `.derived-entry-head` plus `.field-action-row` | aligned |
| source action | visible `Source` button | visible `Source` button | aligned for every derived entry |
| regenerate action | `.wand-btn` | `.wand-btn` | aligned |
| destructive action | `.btn.danger` | `.btn.danger` | aligned |
| action order | Source, wand, Remove | Source, wand, Remove | aligned |
| evidence IDs | plain small code text | plain small code text | aligned |
| fixture | approved deterministic seed | approved deterministic seed | aligned |

Source evidence:

- Prototype component contract: `docs/fitcv-settings-ui-prototype.html`, functions `derivedEntryMarkup`, `derivedSectionMarkup`, and `evidenceRefSelectorMarkup`.
- Runtime component contract: `src/fitcv_cp/templates/candidate_profile_creation.html`, macros `derived_collection` and `evidence_ref_selector`.
- Runtime styling: `src/fitcv_cp/templates/base.html`, Candidate Profile CSS block.
- Runtime fixture and capabilities: `src/fitcv_cp/candidate_profile_mock.py`, `_derived_document` and `_review_annotations`.

## 4. Root causes

### RC1: Split presentation ownership

Prototype, plan, UI Intent, field registry, Jinja templates, CSS, fixtures, and tests each encoded presentation. No runtime dependency connected served components to approved prototype structure.

### RC2: Prototype was treated as reference image, not executable contract

Implementation copied concepts and labels instead of exact DOM hierarchy, class names, action order, spacing, button variants, and default states. Hash check validated file identity only.

### RC3: Field schema was over-assigned

Plan states `src/fitcv/candidate.py` owns field and presentation metadata. Registry can own field inventory, labels, descriptions, control shapes, and validation metadata. It cannot own page layout, component classes, action placement, responsive styling, or visual hierarchy without becoming a second presentation SSOT.

### RC4: Manual translation crossed incompatible rendering stacks

Prototype renders JavaScript template strings. Runtime renders Jinja. No shared candidate-profile CSS asset, fixture, DOM contract, or generated parity manifest exists. Equivalent components were recreated rather than reused.

### RC5: Capability data was incomplete and asymmetric

Runtime hid Source and wand unless per-path annotations contained `source_block_ids` and `regenerable`. Mock annotations covered only two Skill names. Correction now generates annotations uniformly for every admissible derived entry.

### RC6: Fixtures drifted independently

Prototype and Python mock define separate candidates, evidence IDs, claims, descriptions, confidence values, and selected evidence refs. Visual comparison therefore mixes component drift with data drift and cannot isolate either.

### RC7: Global CSS leaked into feature components

Runtime global `code` styling changes evidence IDs into blue outlined pills. Prototype scopes evidence-reference code styling. Generic element selectors silently altered Candidate Profile presentation.

### RC8: Tests proved presence, not parity

Current tests assert labels, checkbox presence, hidden fields, section order, and section counts. They do not assert exact DOM hierarchy, class names, action presence and order, button variants, fixture equality, computed styles, spacing, responsive wrapping, or screenshot parity.

### RC9: Approval evidence was marked complete too early

Plan Task 4 marked browser parity complete without a page-by-page parity matrix against same fixture. Corrections focused on latest reported pages, especially Confirmation and Candidate Details, while Upload, Candidate Profiles, Baseline, Controlled Derivation, and LLM Configuration remained independently rendered.

## 5. Page-by-page audit

| Surface | Status | Main drift |
|---|---|---|
| Candidate Profiles | verified | prototype hierarchy, tabs, toolbar, table controls, fixture, and responsive states aligned |
| Upload | verified | two-column upload card, dropzone, staged-pipeline explanation, file summary, and action layout aligned |
| Baseline | verified | collection wrappers, entry headers, button variants, footer, and nested evidence aligned |
| Controlled Derivation | verified | shared component classes, Source/wand/Remove order, evidence styling, and fixture aligned |
| Confirmation | verified | shared section renderer, order, expanded states, header, footer, and fixture aligned |
| Candidate Details | verified | shared confirmation/details renderer, page header, sections, fixture, and status presentation aligned |
| LLM Configuration | verified | prototype header, grid, actions, explanatory cards, and six task rows aligned |

## 6. Required ownership model

| Concern | One owner |
|---|---|
| visual structure, class contract, action order, button variants, expanded states, responsive behavior | prototype blob |
| canonical field inventory, labels, descriptions, control shapes, evidence kinds, validation metadata | `src/fitcv/candidate.py` field registry |
| transport payloads, capabilities, errors, revisions, fingerprints, transitions | canonical specification plus executable models/routes/tests |
| deterministic approval content | one shared mock fixture |
| runtime state | server resource |

No other document may restate prototype presentation as an alternative design.

## 7. Remediation

### Gate 0: keep backend closed

Do not start parser, LLM, persistence, or pipeline integration until every frontend surface passes parity and user approves served mock.

### Gate 1: create exact parity matrix

For Candidate Profiles, Upload, Baseline, Controlled Derivation, Confirmation, Candidate Details, and LLM Configuration, record:

- route and viewport;
- exact headings and copy;
- DOM hierarchy and class names;
- action presence, order, labels, and button variants;
- default expanded/collapsed state;
- fixture values and selected refs;
- computed spacing, borders, radii, type sizes, and wrapping.

### Gate 2: reuse approved component styling

Extract Candidate Profile prototype CSS verbatim into one shared static asset loaded by both prototype and runtime. Remove duplicate Candidate Profile CSS from `base.html`. Do not introduce a component framework or web-component layer.

Jinja still needs server rendering, so copy exact prototype DOM contract into shared Jinja macros once. Use same macro for every baseline collection and same macro for every derived collection.

### Gate 3: unify fixture

Create one deterministic Candidate Profile fixture consumed by Python mock and prototype generation. Prototype remains presentation SSOT; fixture becomes content SSOT. Remove independently maintained `BASELINE_TEMPLATE`, `DERIVED_SUGGESTIONS`, and Python equivalents after generated prototype data is verified.

### Gate 4: make capabilities symmetric

Generate review annotations for every derived entry from one rule. Every admissible claim uses same Source/wand/Remove contract when server capability allows it. No hand-written per-skill annotation list.

### Gate 5: replace permissive checks

Add focused parity gates:

- exact DOM-order assertions for one representative repeatable baseline entry and each derived collection;
- exact Source, wand, Remove presence and order;
- exact class and button-variant assertions;
- same fixture IDs, values, and checked evidence refs;
- desktop and narrow screenshot comparison for all seven surfaces;
- computed-style checks for high-risk selectors such as `code`, `.derived-entry`, `.creation-footer`, and action rows.

### Gate 6: require explicit approval

Serve corrected mock on port `8766` or another explicit non-`8765` port. Compare prototype and runtime side by side using same fixture. Mark Task 4 complete only after user approval.

## 8. Verification performed

- Prototype hash verified as `989af611bd7767c148022c79ac00c5069d8a3956` in active lane.
- Focused Candidate Profile slice passed: `13 passed, 1 skipped`.
- Exact staged DOM, action-order, fixture, section-order, and forbidden-checksum regressions passed.
- Changed-template JavaScript passed `node --check`; `git diff --check` passed with CRLF warnings only.
- Candidate Profiles, Upload, Baseline, Controlled Derivation, Confirmation, Candidate Details, and LLM Configuration passed browser comparison at `1440px` and `375px`.
- Source and LLM dialogs returned focus; checkbox evidence editing, long labels, effective 200% width, dark theme, and reduced motion passed without horizontal overflow.
- Browser console reported zero errors or warnings.
- FitCV mock listens on `8766`; prototype comparison server listens on `8767`; Anki retains `8765`.
- A fresh independent verifier retested all seven surfaces after the final shared-CSS and projection fixes and reported `Spec compliance: PASS` and `UI parity quality: APPROVED`.
- Verified fixes include exact baseline section projection, symmetric Source/wand/Remove actions, evidence alignment, `End` control sizing, info/header/dialog control styling, field-specific Source excerpt/locator values, validated-model copy, derived display metadata, confirmation date projection, confirmation/detail canonical equality, and zero console errors.
- No known user-visible parity blocker remains in the reviewed Candidate Profile surfaces.
- Prior broad scoped tests reported `519 passed, 1 skipped, 3 failed`; inspection attributed those failures to unchanged `HEAD` owners outside this UI slice. Current Candidate Profile focused checks remain green.

## 9. Decision

Corrected mock was approved August 3, 2026. Backend Tasks 5-10 may execute sequentially against the frozen frontend contract.

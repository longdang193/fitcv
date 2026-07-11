# UX Style / Typography / Spacing SSOT Audit

Reviewed artifact: `templates_ssot_patched.zip` (16 Jinja/HTML templates).

## Verdict

The templates have a useful central theme layer in `base.html`, but the visual system is **not yet a true SSOT**. Colors are mostly tokenized; typography, spacing, radii, control geometry, status surfaces, and layout utilities are still distributed across page-local CSS and 278 inline style attributes.

The result is visually close, but equivalent UI roles are not guaranteed to remain equivalent across pages, themes, viewport widths, or later edits.

## Audit metrics

- 278 inline `style` attributes across 16 templates.
- 5 separate `<style>` blocks.
- 19 distinct font sizes.
- 23 distinct `gap` values.
- 21 distinct `margin-bottom` values.
- 47 distinct `padding` declarations.
- 10 border-radius forms.
- 4 font-family declarations/stacks.
- 31 inline event handlers remain; these also make reusable components harder to standardize.

## Critical findings

### 1. The declared UI font is not actually sourced

`base.html:95` declares:

```css
font-family: 'Inter', system-ui, sans-serif;
```

There is no `@font-face`, stylesheet import, or bundled Inter font. Machines without Inter silently use a different system font. Text widths, wrapping, control heights, and table density therefore vary by operating system.

**Invariant violated:** the same page/data should preserve layout across supported machines.

**Patch:** choose one explicit policy:

1. Self-host Inter and define it with `@font-face`; or
2. Deliberately use a complete system stack and remove the unsourced `Inter` name.

Also define a single `--font-mono` token. `base.html:447` uses generic `monospace`, while `_cv_review_queue.html:246` has a separate detailed stack.

### 2. The generic button hover rule overrides component-specific states

`base.html:379-380` styles every button and then applies:

```css
button:not(.btn-secondary):hover { background: var(--accent-hover); }
```

This selector is more specific than `.btn-section:hover` and `.tab-btn:hover`. Consequently, section buttons and generic tab buttons can receive the primary-button hover background instead of their component-specific hover state.

**SSOT violated:** a legacy fallback is acting as a second owner of every button's interactive state.

**Patch:** remove the global visual fallback. Keep only neutral element normalization on `button`; put appearance exclusively on `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-section`, and `.tab-btn`.

### 3. Shared component classes are redefined locally

`base.html` owns `.sub-card-footer`, `.error-box`, `.inspection-card`, and `.pane-container`. Later templates change those same classes:

- `settings.html:307-315` redefines `.sub-card-footer` and `.error-box`.
- `run_detail.html:1151-1157` changes `.inspection-card` and `.pane-container` overflow.

A component's geometry therefore depends on which page happens to load it.

**SSOT violated:** the same class name has multiple visual contracts.

**Patch:** retain one base definition and add explicit modifiers:

```css
.sub-card-footer--flush { border-top: 0; padding: 0 var(--space-4) var(--space-4); }
.error-box--inset { margin-inline: var(--space-4); }
.inspection-card--overflow-visible,
.inspection-card--overflow-visible .pane-container { overflow: visible; }
```

### 4. Semantic status colors have two independent systems

Badges and status text use `--badge-success-*`, `--badge-warning-*`, and related tokens. Run-health tiles at `run_detail.html:972-995` instead hard-code unrelated RGB colors. Thus “success”, “warning”, and “error” do not share one semantic source.

**Symmetry violated:** equivalent states use different color contracts.

**Theme invariant violated:** hard-coded translucent colors were tuned for dark mode and behave differently on light surfaces.

**Patch:** derive all status surfaces, borders, text, banners, and health tiles from the same semantic tokens.

### 5. Typography hierarchy has no canonical `h3`/`h4` contract

`base.html` defines only `h1`, `h2`, and `.section-title`. The templates contain 22 `h3` elements and 4 `h4` elements, most with inline margins and browser-default sizes/weights.

Equivalent card headings therefore depend on UA defaults and ad hoc inline spacing. Examples include `run_detail.html`, `synonym_review.html`, and `synonym_promote_preview.html`.

**Symmetry violated:** same-level headings do not reliably look or space the same.

**Patch:** define canonical heading roles such as `.page-title`, `.section-heading`, `.card-heading`, and `.group-heading`; avoid relying on browser-default `h3`/`h4` presentation.

## High-priority consistency findings

### 6. The type scale is fragmented

Current sizes include:

```text
0.68, 0.70, 0.72, 0.74, 0.75, 0.77, 0.78, 0.80, 0.82,
0.84, 0.85, 0.86, 0.875, 0.90, 0.95, 1.00, 1.05, 1.10, 1.50rem
```

Many values represent the same semantic roles with imperceptible differences. For example, helper/meta text appears at `0.74`, `0.75`, `0.78`, `0.8`, `0.82`, and `0.86rem`.

**Patch scale:**

```css
--text-xs: 0.75rem;
--text-sm: 0.8125rem;
--text-md: 0.875rem;
--text-lg: 1rem;
--text-xl: 1.125rem;
--text-2xl: 1.5rem;
```

Map all typography to role tokens rather than selecting per-template values.

### 7. Body and controls lack a canonical line-height

`body` has no explicit `line-height`. Individual elements use five line-height values, while most controls rely on browser defaults.

This changes vertical rhythm and control alignment when the fallback font changes.

**Patch:** define `--leading-tight`, `--leading-normal`, and a fixed control line-height/min-height.

### 8. Primary, secondary, and section buttons do not share geometry

The three button variants use different vertical padding (`0.5rem`, `0.4rem`, `0.45rem`) and no shared min-height. Icon-only buttons compensate with an inline macro from `_icons.html`.

**Symmetry violated:** buttons in the same toolbar can have different heights and baselines.

**Patch:** introduce a `.btn` base with `inline-flex`, `align-items:center`, a shared gap, line-height, min-height, font, radius, and horizontal padding. Variants should change only color/border emphasis. Replace the inline icon macro with `.btn-icon`.

### 9. Spacing is not tokenized

The audit found 23 gaps, 21 bottom margins, and 47 padding forms. Repeated semantic structures are encoded as inline strings, including:

- 10 identical accent-bordered notices.
- 8 identical run-detail section headers.
- 5 repeated mode-button rows.
- repeated form/action clusters and stack layouts.

**Patch scale:**

```css
--space-1: 0.25rem;
--space-2: 0.5rem;
--space-3: 0.75rem;
--space-4: 1rem;
--space-6: 1.5rem;
--space-8: 2rem;
```

Add shared layout primitives such as `.cluster`, `.stack`, `.split`, `.section-header`, `.notice`, and `.form-actions`.

### 10. Radius hierarchy is undocumented and inconsistent

The code uses `4px`, `6px`, `8px`, `10px`, `12px`, `0.5rem`, `0.55rem`, `99px`, and `999px`.

Some variation is valid for hierarchy, but the current values are selected per component rather than through named roles.

**Patch:** define `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-xl`, and `--radius-pill` and document which component tier uses each.

### 11. Dark-mode-biased translucent white surfaces

`run_detail.html:943-995` and `_cv_review_queue.html:204-248` use translucent white backgrounds and borders. These create subtle elevation in dark mode but become nearly invisible or visually different in light mode.

**Patch:** use surface tokens or `color-mix()` from semantic theme tokens. Do not encode “lighter than current surface” as a fixed white overlay.

### 12. Fixed input widths weaken viewport invariance

`base.html:434-435` gives text inputs `360px` and number inputs `96px`. Settings later overrides some controls, while other pages inherit the fixed width. The mobile media rule does not normalize input widths.

**Patch:** use responsive field-size modifiers:

```css
.field { width: min(100%, 22.5rem); }
.field--compact { width: 6rem; max-width: 100%; }
.field--fluid { width: 100%; }
```

### 13. The enriched-jobs toolbar is not narrow-screen invariant

`run_detail.html:1024-1032` uses `flex-wrap: nowrap`, multiple minimum widths, and `overflow-x: visible`. This can push controls beyond the card or viewport.

**Patch:** allow wrapping at a shared breakpoint or make the toolbar intentionally horizontally scrollable. The behavior should be explicit, not accidental overflow.

### 14. Two tab style systems overlap

`base.html` defines both `.tab-bar--attached` and a separate `.tab-bar`, while both reuse `.tab-btn`. The cascade currently works mainly through selector specificity.

**Patch:** use a single `.tabs` component with variants such as `.tabs--attached`; keep all states in one component block.

### 15. JavaScript banners duplicate visual CSS in strings

`runs_list.html` and `run_detail.html` build banner styles through `element.style.cssText`, including independent padding, radius, font size, positioning, and status colors.

**SSOT violated:** notification appearance is owned by JavaScript strings rather than the stylesheet.

**Patch:** define `.toast`, `.toast--success`, `.toast--warning`, and `.toast--error`; JavaScript should assign classes and content only.

## What is already consistent

- Dark/light theme colors are mostly centralized in `base.html`.
- Missing surface and neutral-badge tokens from the earlier revision are now defined.
- Table, input, card, badge, and focus styles have reusable base rules.
- The attached run-detail tabs now use one class-based visibility state and ARIA tab semantics.
- Status text in `runs_list.html` reuses semantic badge foreground tokens.
- Most interactive controls inherit the base font rather than declaring independent fonts.

## Recommended patch order

1. Remove the global button visual fallback and fix the hover cascade.
2. Establish font, type, line-height, spacing, radius, and control-size tokens in `base.html`.
3. Define canonical heading, button, notice, stack, cluster, card-header, and toast components.
4. Replace local redefinitions with modifiers.
5. Replace status RGB values and white overlays with semantic theme tokens.
6. Migrate repeated inline style signatures first; then remove remaining one-offs incrementally.
7. Add visual regression snapshots for dark/light and desktop/mobile states.

## Suggested base-system skeleton

```css
:root {
  --font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;

  --text-xs: 0.75rem;
  --text-sm: 0.8125rem;
  --text-md: 0.875rem;
  --text-lg: 1rem;
  --text-xl: 1.125rem;
  --text-2xl: 1.5rem;
  --leading-tight: 1.2;
  --leading-normal: 1.5;

  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;

  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 10px;
  --radius-xl: 12px;
  --radius-pill: 999px;
  --control-height: 2.25rem;
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-md);
  line-height: var(--leading-normal);
}

button {
  font: inherit;
}

.btn {
  min-height: var(--control-height);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding-inline: var(--space-4);
  border-radius: var(--radius-sm);
  line-height: 1;
}

.btn-icon {
  width: var(--control-height);
  padding-inline: 0;
}

.section-heading {
  margin: 0;
  font-size: var(--text-lg);
  line-height: var(--leading-tight);
  font-weight: 700;
}

.meta,
.helper-text {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.cluster {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
```

## Acceptance invariants after patching

- The same semantic role maps to one type token, one spacing pattern, and one component class.
- Primary/secondary/section buttons have identical height and alignment in every toolbar.
- Success/warning/error/info always derive from the same semantic token family.
- A shared class has one base contract; variation requires an explicit modifier.
- Light/dark mode changes colors only, not perceived elevation or component geometry.
- Desktop/mobile changes layout without horizontal page overflow.
- OS font availability cannot silently alter the intended typography policy.

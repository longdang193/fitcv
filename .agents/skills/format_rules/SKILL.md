---
name: format_rules
description: "Enforce formatting standards for markdown and canvas files including LaTeX formulas and list formatting"
---

# Formatting Rules Skill

## Context
Use this skill when:
- Working with markdown (`.md`) files containing mathematical content.
- Editing canvas (`.canvas`) files with formulas.
- Writing or editing production planning and scheduling documentation.

## Guidelines

### List Formatting
- **All lists MUST use hyphen (`-`) as the bullet marker, NOT bullet points (`•`)**
- Use `-` for all unordered list items.
- Maintain consistent formatting throughout documents.

### Formula Formatting
- **All mathematical formulas MUST use LaTeX syntax**
- Use `$...$` for inline math expressions (e.g., `$C_j = C_{j-1} + p_j$`).
- Use `$$...$$` for display/block math expressions (e.g., `$$C_{\max} = \max(C_1, \ldots, C_j)$$`).
- Never use Unicode subscripts/superscripts (like `Cⱼ`, `pₒₚₜ`) - always use LaTeX subscripts (`$C_j$`, `$p_{opt}$`).

### Common Mathematical Notations
- Subscripts: Use `_{}` syntax (e.g., `$p_j$`, `$C_{j,i}$`, `$M_1$`).
- Superscripts: Use `^{}` syntax (e.g., `$t^d$`, `$x^2$`).
- Greek letters: Use LaTeX commands (e.g., `$\alpha$`, `$\beta$`, `$\gamma$`, `$\Sigma$`, `$\sum$`).
- Operators: Use LaTeX commands:
  - `\max`, `\min` for max/min functions.
  - `\sum` for summation.
  - `\sqrt{}` for square roots.
  - `\frac{}{}` for fractions.
  - `\leq`, `\geq` for inequalities.
  - `\parallel` for parallel notation (e.g., `$F_m \parallel C_{\max}$`).

### Scheduling-Specific Conventions
- Job indices: `$j$`, `$i$` (e.g., `$p_j$`, `$C_{j,i}$`).
- Machine indices: `$m$`, `$M_1$`, `$M_2$` (e.g., `$P_m$`, `$F_m$`).
- Time variables: `$t$` for current time, `$r_j$` for release time, `$d_j$` for due date.
- Performance metrics: `$C_j$` (completion time), `$F_j$` (flow time), `$L_j$` (lateness), `$T_j$` (tardiness), `$C_{\max}$` (makespan).

## Examples

**Valid:** Fundamental Parameters
- **Flow Time** ($F_j$): $F_j = C_j - r_j$
- **Lateness** ($L_j$): $L_j = C_j - d_j$
- **Tardiness** ($T_j$): $T_j = \max(0, L_j)$
- **Makespan** ($C_{\max}$): $C_{\max} = \max(C_1, \ldots, C_j)$

**Invalid:** Fundamental Parameters
• **Flow Time** (Fⱼ): Cⱼ - rⱼ
• **Lateness** (Lⱼ): Cⱼ - dⱼ
• **Tardiness** (Tⱼ): max(0, Lⱼ)
• **Makespan** (Cₘₐₓ): max(C₁...Cⱼ)
*(Reason: Uses bullet points `•` instead of hyphens `-`, and Unicode instead of LaTeX)*

## Canvas Files
- When editing `.canvas` files, ensure all formulas in the `text` field use LaTeX syntax.
- Canvas files store content as JSON strings - formulas should be properly escaped LaTeX within those strings.

## Additional Notes
- Always prefer LaTeX over Unicode mathematical notation.
- When in doubt, use display math (`$$...$$`) for standalone formulas.
- Use inline math (`$...$`) for formulas within sentences or bullet points.

---
name: python-code-standards
description: Use when generating or modifying any Python file to enforce style, types,
  and quality.
allowed-tools: []
hooks:
  pre: []
  post: []
required_reads: []
required_outputs: []
related_skills: []
tags:
- skill
- python-code-standards
---

# Python Code Standards

You are required to follow these strict principles when writing or modifying Python code.

The hard invariants from this workflow are also enforced by the generated
`python-contracts` rule surface. Use this skill for the richer implementation
judgment, typing loop, and code-quality workflow that the rule does not try to
fully encode.

## 1. Type Safety (Mypy)

- **Prefer precise types**: Avoid `Any` unless absolutely necessary.
- **Use narrow types**: Prefer `TypedDict`, `dataclass`, `Protocol`, `Literal`, and generics over `dict[str, Any]`.
- **Suppress narrowly**: If you must suppress an error, use `# type: ignore[error-code]` with a short comment explaining why.
- **Enforcement Loop**: When making Python changes in `src/` or `tests/`:
  1. Run: `uvx mypy src --show-error-codes`
  2. Fix all errors without changing runtime behavior.
  3. Re-run Mypy until the targeted scope is clean.

## 2. Code Quality & Formatting

- **Avoid hard-coded numbers**: Use named constants for magic numbers (e.g., `SALES_TAX_RATE = 0.08` instead of `price * 0.08`).
- **Use meaningful, descriptive names**: `elapsed_days = 12` instead of `d = 12`.
- **Comments**: Code should be clear enough to read without comments. Only comment to explain *why* something unusual is happening, not *what* the code does.
- **Function Structure**: Keep functions under 30-50 lines. Prefer early returns to avoid deep nesting. 1 function = 1 task. Maximum 3 parameters, use `TypedDict` or `dataclass` if more are needed.

## 3. Naming Conventions

- **Language:** 100% English
- **snake_case:** variables, functions (`user_id`, `calculate_total()`)
- **PascalCase:** Classes (`UserController`, `TrainingExecutor`)
- **SCREAMING_SNAKE_CASE:** Constants (`MAX_RETRY`, `DEFAULT_BATCH_SIZE`)
- **Boolean:** prefix with `is`, `has`, `can`, `should` (`is_valid`, `has_data`)

## 4. Error Handling

- **Don't swallow errors:** Always log in `try/except` blocks. Use specific exceptions, never a bare `except:`.
- **Structured Logging:** Use structured logging with context.

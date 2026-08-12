# Created: 2026-07-27
# Last Edited: 2026-08-01 16:55 CT (America/Chicago)
# Path: project_audit/alignment_checklist.md
# Purpose: Concrete, measurable checks for evaluating a file or project against "our standard."

# Alignment Checklist

This is the yardstick. Every file in the audited project gets checked against every
applicable item. The goal is a scored, objective assessment — not opinions.

---

## Category 1: File Structure & Headers

| # | Check | Pass Criteria | Severity |
|---|-------|---------------|----------|
| 1.1 | File header present | File begins with `# Created:`, `# Last Edited:`, `# Path:`, `# Purpose:` | P2 |
| 1.2 | Timestamps current | All `# Last Edited` timestamps are within reason (not months/years stale for recently edited files) | P2 |
| 1.3 | Path matches actual | `# Path` value matches the file's actual relative path from project root | P2 |
| 1.4 | No trailing whitespace | Lines don't have trailing spaces | P3 |
| 1.5 | Line length ≤ 100 | No lines exceed 100 characters (PEP 8) | P2 |

---

## Category 2: Imports

| # | Check | Pass Criteria | Severity |
|---|-------|---------------|----------|
| 2.1 | Grouped correctly | Imports ordered: stdlib → third-party → local, with blank line between groups | P2 |
| 2.2 | Absolute imports | Uses absolute imports (`from aethernews.core.engine import ...`), never relative (`from ..core import ...`) | P2 |
| 2.3 | No unused imports | Every imported name is used somewhere in the file | P2 |
| 2.4 | No wildcard imports | No `from x import *` | P1 |
| 2.5 | Import only what's needed | No import of entire module when a single name suffices | P2 |

---

## Category 3: Error Handling

| # | Check | Pass Criteria | Severity |
|---|-------|---------------|----------|
| 3.1 | Specific exceptions | NO bare `except:` — always catch `except SpecificError:` | P0 |
| 3.2 | No silent failures | Every `except` block logs, notifies, or handles the error — never `pass` | P1 |
| 3.3 | User-facing errors shown | Exceptions that reach the user show a dialog or message, not a traceback | P1 |
| 3.4 | Exceptions are specific | Uses built-in or custom exceptions, not `except Exception:` as a catch-all | P1 |

---

## Category 4: Functions & Structure

| # | Check | Pass Criteria | Severity |
|---|-------|---------------|----------|
| 4.1 | One function, one job | Functions do one thing. No 200-line monsters performing 3 unrelated tasks | P1 |
| 4.2 | Function length | Functions under 50 lines unless justified with a comment explaining why | P2 |
| 4.3 | Meaningful names | Names describe what the function/variable does. No `foo`, `bar`, `temp`, `data2` | P2 |
| 4.4 | No duplicate code | No identical or near-identical blocks in different files | P1 |
| 4.5 | Separation of concerns | UI code doesn't contain business logic. DB code doesn't render UI | P1 |
| 4.6 | No circular imports | Module A doesn't import Module B which imports Module A | P0 |

---

## Category 5: Database

| # | Check | Pass Criteria | Severity |
|---|-------|---------------|----------|
| 5.1 | Parameterized queries | All SQL uses `?` placeholders, never f-string or string concatenation | P0 |
| 5.2 | Named column access | Uses `conn.row_factory = sqlite3.Row` or dict access, never numeric indices | P1 |
| 5.3 | Connection handling | Connections opened with context manager (`with db:`) or properly closed in `finally` | P1 |
| 5.4 | WAL mode enabled | `PRAGMA journal_mode=WAL;` set on connection for concurrent access | P2 |

---

## Category 6: Testing

| # | Check | Pass Criteria | Severity |
|---|-------|---------------|----------|
| 6.1 | Tests exist | `tests/` directory exists with at least one test file | P1 |
| 6.2 | Tests run | `pytest` exits 0 without crashes | P1 |
| 6.3 | Core logic tested | Business logic (engine, models) has unit tests | P1 |
| 6.4 | Regression tests | Bug fixes include a test that verifies the fix | P2 |

---

## Category 7: Project Hygiene

| # | Check | Pass Criteria | Severity |
|---|-------|---------------|----------|
| 7.1 | `.gitignore` present | Root has `.gitignore` covering venv, pycache, .env, build artifacts | P2 |
| 7.2 | Virtual env named correctly | Named `venv/` not `.venv/` | P2 |
| 7.3 | Requirements tracked | `requirements.txt` exists with pinned versions | P2 |
| 7.4 | No secrets committed | No `.env`, API keys, passwords, or `.key` files in git history | P0 |
| 7.5 | No debug artifacts | No `print()` statements left in production code, no commented-out debug blocks | P2 |
| 7.6 | Package name is unique | Top-level package is named after the project (e.g., `aethervault/`), NOT `src/`. Prevents namespace collisions when sibling projects exist on the same machine | P1 |

---

## Category 8: Documentation

| # | Check | Pass Criteria | Severity |
|---|-------|---------------|----------|
| 8.1 | CHANGELOG exists | `docs/sys/CHANGELOG.md` exists and has entries | P2 |
| 8.2 | PLAN/TASKS exist | `docs/sys/PLAN.md` and `docs/sys/TASKS.md` exist | P2 |
| 8.3 | ARCHITECTURE exists | `docs/sys/ARCHITECTURE.md` describes the structure | P2 |
| 8.4 | BUGS tracker exists | `docs/sys/BUGS.md` exists (may be empty) | P2 |
| 8.5 | Maps directory populated | `/maps/` contains `.md`/`.mmd` files reflecting the codebase | P1 |

---

## Category 9: Environment

| # | Check | Pass Criteria | Severity |
|---|-------|---------------|----------|
| 9.1 | Python version | Uses Python 3.10+ | P2 |
| 9.2 | Virtual env active | `venv/` directory exists and is in use | P2 |
| 9.3 | No system-wide deps | All dependencies listed in `requirements.txt`, not just installed globally | P2 |

---

## Scoring

| Score | Criteria |
|-------|----------|
| **A** | 100% pass on all applicable checks |
| **B** | ≥90% pass, only P2/P3 failures |
| **C** | ≥75% pass, some P1 failures |
| **D** | ≥50% pass, P0/P1 failures exist |
| **F** | <50% pass or any unresolved P0 |

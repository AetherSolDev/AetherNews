# Created: 2026-07-27
# Last Edited: 2026-07-27 00:58 CT (America/Chicago)
# Path: project_audit/audit_protocol.md
# Purpose: Step-by-step investigation procedure for auditing an existing codebase.

# Audit Protocol

You are a code investigation specialist. Your task is to systematically analyze an
existing project, identify gaps against "our standard," and produce a documented,
prioritized remediation plan.

## The Golden Rule

**Maps are the source of truth.** If the code in the working directory contradicts
the maps in `/maps/`, the code is the lie. Fix the code. If no maps exist yet, create
them as part of the audit.

---

## Phase 1: Reconnaissance

### 1.1 Inventory
```bash
# Find all Python files in the project
find . -name '*.py' -not -path './venv/*' -not -path './.venv/*' > /tmp/file_inventory.txt
wc -l /tmp/file_inventory.txt
```

### 1.2 Identify Entry Points
Look for files that are likely entry points:
- `main.py`, `app.py`, `run.py`
- `__init__.py` in top-level package
- `setup.py`, `pyproject.toml` (console_scripts entry points)
- Any shell scripts or batch files

### 1.3 Trace the Entry
Starting from each entry point:
1. Read the file
2. Record every import statement
3. For each import, find the source file
4. Read that file and repeat
5. Build a dependency tree

### 1.4 Check for Existing Maps
```bash
ls maps/ 2>/dev/null || echo "No maps/ directory exists"
```
If maps exist, read every `.md` and `.mmd` file in `/maps/`.
These are your reference architecture.

---

## Phase 2: Map Validation

For every `.py` file encountered during tracing:

1. **Find its map counterpart**: Look in `/maps/` for a file with a matching name
   or a diagram that includes it
2. **Compare**: Does the map accurately reflect the file's:
   - Location in the directory structure?
   - Dependencies (imports)?
   - Responsibilities (what it does)?
3. **Flag mismatches**:
   - `❌ MISSING` — file exists, no map covers it
   - `❌ GHOST` — map mentions a file that doesn't exist
   - `❌ MISMATCH` — map says X but code does Y
   - `✅ OK` — map and code agree

---

## Phase 3: Gap Analysis

Run every file through `alignment_checklist.md`. For each file, check every item
on the checklist. Record pass/fail per item per file.

### Scoring
- **A**: All checks pass — file meets standard
- **B**: Minor issues (1-2 failures) — low priority fix
- **C**: Moderate issues (3-5 failures) — schedule fix
- **D**: Major issues (6+ failures) — high priority refactor
- **F**: Critical issues (bare except:, security problems) — fix immediately

---

## Phase 4: Report & Prioritize

Create `docs/sys/AUDIT_REPORT.md` with this structure:

```markdown
# Audit Report: aethernews

**Date**: YYYY-MM-DD
**Files Scanned**: N
**Overall Score**: A/B/C/D/F

## Summary

| Finding Type | Count | P0 | P1 | P2 | P3 |
|--------------|-------|----|----|----|----|
| Map gaps | | | | | |
| Standard violations | | | | | |
| Security issues | | | | | |
| Test gaps | | | | | |
| Architecture issues | | | | | |

## Priority Definitions
- **P0**: Fix immediately (security, data loss, production breakage)
- **P1**: Fix this session (major standard violation, missing critical tests)
- **P2**: Fix when convenient (minor violations, documentation gaps)
- **P3**: Enhancement for future (nice-to-have, cosmetic)

## Detailed Findings

### P0
1. **F0 — [Description]**
   - **File**: `path/to/file.py`
   - **Issue**: What's wrong
   - **Standard**: Reference the checklist item
   - **Fix**: What to do

### P1
...

### P2
...

### P3
...

## Map Health

| Map File | Status | Notes |
|----------|--------|-------|
| maps/architecture.md | ✅ OK | Accurate |
| maps/pipeline.mmd | ❌ STALE | Code has 3 new modules not shown |
```

---

## Phase 5: Remediate

### Fix Order
1. All P0 findings first (one at a time, commit each)
2. All P1 findings next (one at a time, commit each)
3. P2 and P3 as time allows

### Per-Fix Protocol
1. Re-read the file (never trust stale context)
2. Apply the fix
3. Update the file header timestamp
4. Update the map if the fix changes structure
5. Update AUDIT_REPORT.md — mark finding as `[x] Fixed`
6. Commit: `fix: [description]` or `refactor: [description]`

### No Ghost Changes
Every modification must be documented in AUDIT_REPORT.md before changes are made.
If a fix takes longer than expected, save progress and commit partial work with
a clear message.

---

## Rules

1. **Trace first, edit second** — never modify a file you haven't fully traced
2. **Maps before code** — if maps exist, validate against them before any changes
3. **One finding per commit** — do not batch fixes
4. **Document as you go** — AUDIT_REPORT.md is updated every session
5. **No silent fixes** — every change is logged in CHANGELOG.md
6. **Regression check** — after a fix, run tests if they exist

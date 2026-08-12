# Created: 2026-07-31
# Last Edited: 2026-08-01 16:55 CT (America/Chicago)
# Path: aethernews/project_audit/house_cleaning.md
# Purpose: Recurring directory-by-directory tidy-up procedure for an established project.

# House Cleaning

A light, recurring maintenance pass for an **established** project. Differs from
`audit_protocol.md` (which is a deep one-time forensic audit against maps).
House cleaning is a **report-first, approve-then-act** sweep to keep the repo
tidy, current, and aligned with our structure conventions.

## The Golden Rule

**Report first. Act only after approval.** Walk each directory, list what you
find (dead files, stale docs, wrong locations, outdated paths), and let the
user decide before anything is deleted or moved. House cleaning is interactive —
it is done *with* the user, not for them.

---

## Standard Pass Order

Start at the root and work inward, one directory at a time. Do not jump ahead:

```
1. /            → project root
2. admin/
3. aethernews/  → application package
4. docs/        → user-facing docs only
5. docs/sys/    → internal docs (gitignored)
6. scripts/
7. tests/
8. web/         → marketing site (Hostinger)
```

For each directory, report findings grouped as:

| Category | Meaning |
|----------|---------|
| 🗑️ DEAD | No references, regenerable, or superseded — candidate for deletion |
| 📦 MOVE | In the wrong place (e.g., dev docs in user-facing `docs/`) |
| ✏️ STALE | Outdated content/paths that should be updated, not deleted |
| ✅ OK | Fine as-is |

Then stop and wait for the user to approve each item.

---

## Per-Directory Checks

### 1. Project Root
- [ ] Stray files that belong elsewhere (scripts, exports, temp files)
- [ ] `.gitignore` matches reality — no entries for deleted files, all internal paths covered
- [ ] Untracked files that would be swept into a commit by `git add .` (check `git status --short`)
- [ ] Root `README.md` accurate (not the packaged `docs/README.md`)

### 2. admin/ (and other internal dirs)
- [ ] Files still needed, or archived artifacts
- [ ] Sensitive content stays gitignored

### 3. aethernews/ (application package)
- [ ] No dead code, unused imports, or orphaned modules
- [ ] File headers present with correct `Last Edited` timestamps
- [ ] No bare `except:` or f-string SQL
- [ ] Imports grouped: stdlib → third-party → local

### 4. docs/ — **user/client-facing ONLY**
- [ ] Only user docs live here: `USER_GUIDE.md/.html`, `README.md/.html`
- [ ] Dev references (templates, restore notes) live in `docs/sys/` — never here
- [ ] Every `.html` matches its `.md` source (Help menu opens the `.html`)
- [ ] `create_portable.py` copies this folder — anything here ships to end users

### 5. docs/sys/ (internal)
- [ ] Dead generated artifacts removed (inventory reports, stale reference dumps)
- [ ] Living docs current: KNOWLEDGE.md, PLAN.md, CHANGELOG.md, BUGS.md, TASKS.md
- [ ] All internal files gitignored so they never leak to a public repo

### 6. scripts/
- [ ] Every script still used (check references, not just existence)
- [ ] Admin/secret scripts gitignored (e.g., `generate_license.py`)
- [ ] Audit tooling available: `find_dependencies.py` + `function_inventory.py` (dead-code detection).
      Regenerate their reports FRESH per audit — never keep stale snapshots in `docs/sys/`.

### 7. tests/
- [ ] Tests import the current package name (no `src.` leftovers)
- [ ] Tests pass before and after the pass

### 8. web/
- [ ] Links/URLs current (repo name, pricing, contact)
- [ ] Content matches the app (features, trial, price tiers)

---

## Rules

1. **Report, don't delete.** List findings with a recommendation; get a yes.
2. **One directory at a time.** Finish and confirm before moving on.
3. **Never leave `docs/` with dev content.** User docs stay user-facing.
4. **Update references.** If a file moves, fix every doc/comment that points at it.
5. **Keep `.gitignore` honest.** Remove entries for deleted files; add newly internal files.
6. **Log it.** Update `docs/sys/CHANGELOG.md` and `KNOWLEDGE.md` at the end of the pass.
7. **Re-run tests** after any code-adjacent change.

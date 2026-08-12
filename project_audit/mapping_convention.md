# Created: 2026-07-27
# Last Edited: 2026-07-27 00:58 CT (America/Chicago)
# Path: project_audit/mapping_convention.md
# Purpose: Rules for creating and validating project maps during audit.

# Mapping Convention

## Purpose

Maps are the source of truth for project architecture. They exist so any agent
(human or AI) can understand the system without reading every line of code.
During an audit, maps serve as the reference against which code is validated.

---

## Directory Structure

All maps live in `/maps/` at the project root:

```
project-root/
├── maps/
│   ├── architecture.md        — Directory tree, component responsibilities
│   ├── pipeline.mmd           — Data/process flow (mermaid flowchart)
│   ├── database.mmd           — Entity relationships (mermaid ER diagram)
│   ├── imports.mmd            — Module dependency graph (mermaid flowchart)
│   └── DEPRECATED.md          — Archive of outdated maps (never delete, move here)
```

---

## Map Types

### 1. architecture.md (Markdown)
Purpose: High-level directory structure and component responsibilities.

Format:
```markdown
# Architecture Map

## Directory Tree
```
src/
├── core/              # Business logic
│   ├── engine.py      # Main processing pipeline
│   └── settings.py    # Configuration management
├── gui/               # UI layer
│   └── main_window.py # Application window
└── shared/            # Cross-cutting utilities
    └── database.py    # Data access layer
```

## Key Relationships
- `gui/` imports `shared/` but never `core/` directly
- `core/` imports `shared/` for database access
```

### 2. pipeline.mmd (Mermaid flowchart)
Purpose: Process flow, data pipeline, or state machine.

Rules:
- Maximum 12 nodes for audit maps
- Labels describe the action, not the file
- Group related nodes with subgraphs

### 3. database.mmd (Mermaid ER diagram)
Purpose: Table relationships and key columns.

### 4. imports.mmd (Mermaid flowchart)
Purpose: Module dependency visualization. Useful for identifying circular imports
and unexpected coupling.

---

## Map Validation Rules

### Rule 1: Every file must map
For every `.py` file in the project (excluding `venv/`, `tests/`, `scripts/`),
there must be a map entry somewhere. A file with no map entry is a gap.

### Rule 2: Maps must be accurate
If code changes, the map must be updated in the same commit. Stale maps are
worse than no maps.

### Rule 3: Maps are not documentation
Maps describe *structure and relationships*, not *how to use the app*. User
instructions go in `docs/USER_GUIDE.md`.

### Rule 4: Never delete — archive
Instead of deleting an outdated map, move it to `maps/DEPRECATED.md` with a
note about when and why it was superseded.

---

## Audit-Specific Mapping Protocol

When auditing a project with no existing maps:

1. **Start from the entry point** — trace all imports
2. **Build architecture.md first** — directory tree + one-line purpose per file
3. **Build imports.mmd** — dependency graph (identifies circular imports)
4. **Build pipeline.mmd** — if the project has a data/processing pipeline
5. **Build database.mmd** — if the project uses a database

When auditing a project WITH existing maps:

1. **Read all maps** before reading code
2. **Trace imports** and compare against `imports.mmd`
3. **Flag discrepancies** — every mismatch is a finding in AUDIT_REPORT.md
4. **Update maps** after code is fixed (not before)

# Created: 2026-07-27
# Last Edited: 2026-07-31 12:28 CT (America/Chicago)
# Path: project_audit/cleanup_patterns.md
# Purpose: Common anti-patterns found during audits, with fixes.

# Cleanup Patterns

A reference of common codebase issues discovered during audits, organized by
pattern, with the standard fix. Use this as a quick reference during remediation.

---

## Pattern 1: Circular Imports

**Detection**: `ImportError: cannot import name X from partially initialized module Y`

**Root Cause**: Module A imports Module B, which imports Module A (direct or
through a chain).

**Fix**: Extract the shared dependency into a third module that both can import:

```python
# Before:
# module_a.py
from module_b import helper_b

# module_b.py
from module_a import helper_a

# After:
# shared.py (new)
def helper_a(): ...
def helper_b(): ...

# module_a.py
from shared import helper_b

# module_b.py
from shared import helper_a
```

**Alternative**: Use late imports (import inside the function) if the circular
dependency is truly unavoidable, but this is a smell — prefer extraction.

---

## Pattern 2: Duplicate Functions

**Detection**: Same logic appears in 2+ files with different names.

**Root Cause**: Copy-paste during development, or two developers solving the
same problem independently.

**Fix**: Extract to a shared module:

```python
# Before:
# file_a.py
def calculate_total(items):
    return sum(item.price * item.qty for item in items)

# file_b.py
def sum_items(items):
    total = 0
    for item in items:
        total += item.price * item.qty
    return total

# After:
# aethernews/shared/utils.py
def calculate_total(items):
    return sum(item.price * item.qty for item in items)

# Both files import from utils
```

---

## Pattern 3: God Functions (>100 lines)

**Detection**: A function that scrolls more than 2 pages, with multiple
responsibilities.

**Root Cause**: "I'll refactor it later" — which never comes.

**Fix**: Extract each distinct responsibility into its own function:

```python
# Before:
def process_order(order):
    # Validate
    if not order.customer:
        raise ValueError("No customer")
    if not order.items:
        raise ValueError("No items")
    # Calculate
    total = sum(i.price * i.qty for i in order.items)
    tax = total * 0.08
    # Save
    db.save_order(order, total + tax)
    # Notify
    email.send(order.customer.email, f"Total: ${total + tax}")

# After:
def process_order(order):
    _validate_order(order)
    total = _calculate_total(order)
    _persist_order(order, total)
    _notify_customer(order, total)

def _validate_order(order): ...
def _calculate_total(order): ...
def _persist_order(order, total): ...
def _notify_customer(order, total): ...
```

---

## Pattern 4: Mixed Concerns (UI + Logic)

**Detection**: A GUI file contains SQL queries or business calculations.

**Root Cause**: Rapid prototyping — "it's faster to write the query here."

**Fix**: Move data access to `database.py`, business logic to `engine.py`,
leave only presentation in the GUI file:

```python
# Before: gui/main_window.py
def load_tasks(self):
    rows = self.db.execute("SELECT * FROM tasks").fetchall()
    total = sum(r["hours"] for r in rows)
    self.total_label.setText(f"{total} hrs")

# After: gui/main_window.py
def load_tasks(self):
    tasks = self.engine.get_all_tasks()
    self.task_table.populate(tasks)

# core/engine.py
def get_all_tasks(self):
    return self.db.fetch_all("tasks")
```

---

## Pattern 5: Bare Excepts

**Detection**: `except:` or `except Exception:` swallowing all errors.

**Root Cause**: "I don't want it to crash" — but now it silently fails.

**Fix**: Catch specific exceptions. Log the error. Notify the user:

```python
# Before:
try:
    data = db.query(sql)
except:
    pass

# After:
try:
    data = db.query(sql)
except DatabaseError as e:
    logger.error("Query failed", sql=sql, error=str(e))
    show_error_dialog("Could not load data. Please try again.")
    raise
```

---

## Pattern 6: Hardcoded Values

**Detection**: Magic numbers, strings, or configuration values scattered
throughout the code.

**Root Cause**: "I'll make it configurable later."

**Fix**: Extract to constants, settings class, or config file:

```python
# Before:
def calculate_tax(amount):
    return amount * 0.08  # What is 0.08? Why 0.08?

# After:
TAX_RATE = 0.08  # Standard sales tax rate

def calculate_tax(amount):
    return amount * TAX_RATE
```

---

## Pattern 7: Dead Code

**Detection**: Functions, classes, or imports that are never called/used.

**Root Cause**: Deleted the caller but forgot to delete the callee.

**Fix**: Remove dead code. Git history preserves it if needed later.

```python
# Before:
import os  # unused
def old_parser(data): ...  # never called
def new_parser(data): ...  # used

# After:
def new_parser(data): ...
```

---

## Pattern 8: Generic Package Name (`src/`)

**Detection**: Top-level package is named `src/` (e.g., `from src.core import ...`)

**Root Cause**: Scaffolding template defaulted to `src/` without considering
namespace collisions with sibling projects sharing the same machine.

**Fix**: Rename `src/` → `aethernews/` and update all imports:

```python
# Before:
#   from src.core import engine
#   from src.gui import app

# After:
#   from aethervault.core import engine
#   from aethervault.gui import app
```

Also update `pyproject.toml`:
```toml
[tool.setuptools.packages.find]
include = ["aethernews*"]

[project.scripts]
project_name = "aethernews.main:run"
```

Reinstall after rename:
```bash
pip install --user --break-system-packages -e .
```

---

## Pattern 9: Stringly-Typed SQL Queries

**Detection**: SQL queries built with f-strings or `+` concatenation.

**Root Cause**: "It's just a quick query."

**Fix**: Use parameterized queries:

```python
# Before (VULNERABLE to SQL injection):
cursor.execute(f"SELECT * FROM tasks WHERE id = {task_id}")

# After:
cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
```

---

## Quick Reference

| Pattern | Severity | Detection Method | Typical Fix |
|---------|----------|-----------------|-------------|
| Circular imports | P0 | ImportError at runtime | Extract shared dependency |
| Duplicate functions | P1 | Manual code review | Extract to shared module |
| God functions | P1 | Function length > 50 lines | Extract methods |
| Mixed concerns | P1 | GUI files contain SQL/logic | Move to engine/database |
| Bare excepts | P0 | Search for `except:` | Catch specific exceptions |
| Hardcoded values | P2 | Magic numbers in code | Extract to constants |
| Dead code | P2 | IDE inspection / grep | Remove unused code |
| Generic package name | P1 | Package dir is `src/` | Rename to `aethernews/` |
| Stringly-typed SQL | P0 | f-string in SQL query | Use parameterized queries |

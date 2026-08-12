#!/usr/bin/env python3
# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: aethernews.py
# Purpose: CLI entry point — delegates to aethernews.cli:main.

import sys

from aethernews.cli import main

if __name__ == "__main__":
    sys.exit(main())

"""Allow the program to be started with ``python -m gradevault``."""

from __future__ import annotations

import sys

from .cli.app import main

if __name__ == "__main__":
    sys.exit(main())

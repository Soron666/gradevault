"""Infrastructure layer: repositories and the demo dataset."""

from __future__ import annotations

from .repository import (
    GradeVaultRepository,
    InMemoryRepository,
    SqliteRepository,
    describe_repository,
    open_repository,
)
from .seed import seed_demo_data

__all__ = [
    "GradeVaultRepository",
    "InMemoryRepository",
    "SqliteRepository",
    "describe_repository",
    "open_repository",
    "seed_demo_data",
]

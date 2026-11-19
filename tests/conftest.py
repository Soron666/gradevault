"""Shared pytest fixtures for the GradeVault test suite."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from gradevault.application.service import ResultService
from gradevault.infrastructure.repository import InMemoryRepository, SqliteRepository


@pytest.fixture()
def repository() -> InMemoryRepository:
    """A fresh in-memory repository."""
    return InMemoryRepository()


@pytest.fixture()
def service(repository: InMemoryRepository) -> ResultService:
    """A service backed by the in-memory repository."""
    return ResultService(repository)


@pytest.fixture()
def fixed_clock():
    """A deterministic clock so recorded timestamps can be asserted."""
    return lambda: datetime(2026, 11, 19, 10, 30, 0)


@pytest.fixture()
def service_with_clock(repository, fixed_clock) -> ResultService:
    """A service whose timestamps are deterministic."""
    return ResultService(repository, clock=fixed_clock)


@pytest.fixture()
def sqlite_service(tmp_path) -> ResultService:
    """A service backed by a temporary SQLite file."""
    repository = SqliteRepository(tmp_path / "gradevault-test.db")
    try:
        yield ResultService(repository)
    finally:
        repository.close()


@pytest.fixture()
def populated_service(service: ResultService) -> ResultService:
    """A service holding three students, three courses, enrollments and marks.

    The CGPA of the first student is deliberately computed by hand in the
    tests, so the fixture stays small enough to reason about.
    """
    service.add_student("241337037", "Md. Ragib Shahriyer Soron", "CSE", 5)
    service.add_student("241337038", "Nusrat Jahan Oishi", "CSE", 5)
    service.add_student("241337039", "Tanvir Ahmed", "ECE", 3)

    service.add_course("CSE402", "Software Engineering", credit=Decimal("3.00"))
    service.add_course("CSE403", "Database Systems", credit=Decimal("3.00"))
    service.add_course("CSE410", "Artificial Intelligence", credit=Decimal("4.00"))

    for student_id in ("241337037", "241337038", "241337039"):
        service.enroll(student_id, "CSE402")
        service.enroll(student_id, "CSE403")

    service.enroll("241337037", "CSE410")

    service.record_mark("241337037", "CSE402", 86, recorded_by="teacher")
    service.record_mark("241337037", "CSE403", 78, recorded_by="teacher")
    service.record_mark("241337037", "CSE410", 92, recorded_by="teacher")

    service.record_mark("241337038", "CSE402", 64, recorded_by="teacher")
    service.record_mark("241337038", "CSE403", 81, recorded_by="teacher")

    service.record_mark("241337039", "CSE402", 47, recorded_by="teacher")
    return service


@pytest.fixture(params=["memory", "sqlite"])
def any_service(request, tmp_path) -> ResultService:
    """Run a test against both repository implementations."""
    if request.param == "memory":
        yield ResultService(InMemoryRepository())
    else:
        repository = SqliteRepository(tmp_path / f"{request.param}.db")
        try:
            yield ResultService(repository)
        finally:
            repository.close()

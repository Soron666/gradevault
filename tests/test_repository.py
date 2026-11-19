"""Tests for the repositories - both implementations must behave the same."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from gradevault.domain.assessment import MarkRecord
from gradevault.domain.course import Course
from gradevault.domain.enrollment import Enrollment
from gradevault.domain.errors import DuplicateCourseError, DuplicateStudentError
from gradevault.domain.student import Student
from gradevault.infrastructure.repository import (
    GradeVaultRepository,
    InMemoryRepository,
    SqliteRepository,
    open_repository,
)


@pytest.fixture(params=["memory", "sqlite"])
def repo(request, tmp_path):
    """A repository of each kind, so every test below runs twice."""
    if request.param == "memory":
        yield InMemoryRepository()
    else:
        repository = SqliteRepository(tmp_path / "repo.db")
        try:
            yield repository
        finally:
            repository.close()


def test_both_repositories_satisfy_the_protocol(repo):
    assert isinstance(repo, GradeVaultRepository)


# ----------------------------------------------------------------------
# students
# ----------------------------------------------------------------------
def test_a_student_can_be_stored_and_read_back(repo):
    repo.add_student(Student(student_id="241337037", name="Soron", semester=5))
    student = repo.get_student("241337037")
    assert student is not None
    assert student.name == "Soron"
    assert student.semester == 5


def test_a_duplicate_student_is_refused(repo):
    repo.add_student(Student(student_id="241337037", name="Soron"))
    with pytest.raises(DuplicateStudentError):
        repo.add_student(Student(student_id="241337037", name="Other"))


def test_an_unknown_student_reads_as_none(repo):
    assert repo.get_student("404") is None


def test_students_are_returned_in_id_order(repo):
    for student_id in ("C", "A", "B"):
        repo.add_student(Student(student_id=student_id, name="X"))
    assert [s.student_id for s in repo.list_students()] == ["A", "B", "C"]


def test_the_enrolment_date_survives_a_round_trip(repo):
    repo.add_student(
        Student(student_id="1", name="X", enrolled_on=date(2026, 1, 15))
    )
    assert repo.get_student("1").enrolled_on == date(2026, 1, 15)


# ----------------------------------------------------------------------
# courses
# ----------------------------------------------------------------------
def test_a_course_can_be_stored_and_read_back(repo):
    repo.add_course(
        Course(code="CSE402", title="Software Engineering", credit=Decimal("3.00"))
    )
    course = repo.get_course("CSE402")
    assert course.title == "Software Engineering"
    assert course.credit == Decimal("3.00")


def test_a_duplicate_course_is_refused(repo):
    repo.add_course(Course(code="CSE402", title="A"))
    with pytest.raises(DuplicateCourseError):
        repo.add_course(Course(code="CSE402", title="B"))


def test_an_unknown_course_reads_as_none(repo):
    assert repo.get_course("CSE999") is None


def test_fractional_credits_survive_a_round_trip(repo):
    """Decimals are stored as text so 1.50 never becomes 1.5."""
    repo.add_course(Course(code="CSE402", title="A", credit=Decimal("1.50")))
    assert repo.get_course("CSE402").credit == Decimal("1.50")


# ----------------------------------------------------------------------
# enrollments
# ----------------------------------------------------------------------
def test_an_enrollment_can_be_stored_and_read_back(repo):
    repo.add_student(Student(student_id="1", name="X"))
    repo.add_course(Course(code="CSE402", title="A"))
    repo.enroll(Enrollment(student_id="1", course_code="CSE402"))
    assert repo.is_enrolled("1", "CSE402") is True
    assert repo.is_enrolled("1", "CSE403") is False


def test_enrollments_can_be_filtered_by_student(repo):
    repo.add_student(Student(student_id="1", name="X"))
    repo.add_student(Student(student_id="2", name="Y"))
    repo.add_course(Course(code="CSE402", title="A"))
    repo.add_course(Course(code="CSE403", title="B"))
    repo.enroll(Enrollment(student_id="1", course_code="CSE402"))
    repo.enroll(Enrollment(student_id="2", course_code="CSE403"))
    assert len(repo.list_enrollments()) == 2
    assert len(repo.list_enrollments("1")) == 1
    assert repo.list_enrollments("1")[0].course_code == "CSE402"


def test_the_enrolled_courses_of_a_student_are_listed(repo):
    repo.add_student(Student(student_id="1", name="X"))
    repo.add_course(Course(code="CSE403", title="B"))
    repo.add_course(Course(code="CSE402", title="A"))
    repo.enroll(Enrollment(student_id="1", course_code="CSE403"))
    repo.enroll(Enrollment(student_id="1", course_code="CSE402"))
    assert [c.code for c in repo.enrolled_courses("1")] == ["CSE402", "CSE403"]


# ----------------------------------------------------------------------
# marks
# ----------------------------------------------------------------------
def test_a_mark_can_be_stored_and_read_back(repo):
    repo.add_student(Student(student_id="1", name="X"))
    repo.add_course(Course(code="CSE402", title="A"))
    repo.save_mark(MarkRecord(student_id="1", course_code="CSE402", mark=Decimal("86")))
    record = repo.get_mark("1", "CSE402")
    assert record is not None
    assert record.mark == Decimal("86")


def test_a_second_mark_replaces_the_first(repo):
    repo.add_student(Student(student_id="1", name="X"))
    repo.add_course(Course(code="CSE402", title="A"))
    repo.save_mark(MarkRecord(student_id="1", course_code="CSE402", mark=Decimal("50")))
    repo.save_mark(MarkRecord(student_id="1", course_code="CSE402", mark=Decimal("90")))
    assert len(repo.list_marks("1")) == 1
    assert repo.get_mark("1", "CSE402").mark == Decimal("90")


def test_marks_can_be_filtered_by_student(repo):
    repo.add_student(Student(student_id="1", name="X"))
    repo.add_student(Student(student_id="2", name="Y"))
    repo.add_course(Course(code="CSE402", title="A"))
    repo.save_mark(MarkRecord(student_id="1", course_code="CSE402", mark=Decimal("86")))
    repo.save_mark(MarkRecord(student_id="2", course_code="CSE402", mark=Decimal("60")))
    assert len(repo.list_marks("1")) == 1
    assert len(repo.list_marks()) == 2


def test_an_unknown_mark_reads_as_none(repo):
    assert repo.get_mark("1", "CSE402") is None


def test_the_recording_metadata_survives_a_round_trip(repo):
    from datetime import datetime

    repo.add_student(Student(student_id="1", name="X"))
    repo.add_course(Course(code="CSE402", title="A"))
    repo.save_mark(
        MarkRecord(
            student_id="1",
            course_code="CSE402",
            mark=Decimal("86"),
            recorded_at=datetime(2026, 11, 19, 10, 30, 0),
            recorded_by="Prof. Rahman",
        )
    )
    record = repo.get_mark("1", "CSE402")
    assert record.recorded_by == "Prof. Rahman"
    assert record.recorded_at == datetime(2026, 11, 19, 10, 30, 0)


# ----------------------------------------------------------------------
# SQLite specifics
# ----------------------------------------------------------------------
def test_sqlite_data_survives_a_restart(tmp_path):
    """A teacher's work must not be lost when the program is closed."""
    path = tmp_path / "persistent.db"
    first = SqliteRepository(path)
    first.add_student(Student(student_id="241337037", name="Soron"))
    first.add_course(Course(code="CSE402", title="Software Engineering"))
    first.close()

    second = SqliteRepository(path)
    try:
        assert second.get_student("241337037").name == "Soron"
        assert second.get_course("CSE402").title == "Software Engineering"
    finally:
        second.close()


def test_the_schema_is_created_if_it_is_missing(tmp_path):
    """Opening a fresh file is enough - no manual setup step."""
    path = tmp_path / "fresh.db"
    repository = SqliteRepository(path)
    try:
        assert repository.list_students() == []
    finally:
        repository.close()


def test_open_repository_picks_the_right_implementation(tmp_path):
    assert isinstance(open_repository(":memory:"), InMemoryRepository)
    assert isinstance(open_repository(tmp_path / "x.db"), SqliteRepository)

"""Tests for the application service - requirements 1, 2, 3 and 6."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from gradevault.domain.errors import (
    AlreadyEnrolledError,
    CourseNotFoundError,
    DuplicateCourseError,
    DuplicateStudentError,
    InvalidMarkError,
    NotEnrolledError,
    StudentNotFoundError,
)


# ======================================================================
# requirement 1 - add a student with a unique ID
# ======================================================================
def test_a_student_can_be_added(service):
    student = service.add_student("241337037", "Md. Ragib Shahriyer Soron")
    assert student.student_id == "241337037"
    assert student.name == "Md. Ragib Shahriyer Soron"
    assert service.get_student("241337037") is student


def test_student_ids_are_unique(service):
    """The brief is explicit: student IDs must be unique."""
    service.add_student("241337037", "Md. Ragib Shahriyer Soron")
    with pytest.raises(DuplicateStudentError):
        service.add_student("241337037", "Someone Else")


def test_a_duplicate_id_is_rejected_even_when_the_case_differs(service):
    """IDs are compared case-insensitively, so 'a1' and 'A1' collide."""
    service.add_student("A1", "First")
    with pytest.raises(DuplicateStudentError):
        service.add_student("a1", "Second")


def test_the_duplicate_message_names_the_id(service):
    service.add_student("241337037", "Md. Ragib Shahriyer Soron")
    with pytest.raises(DuplicateStudentError, match="241337037"):
        service.add_student("241337037", "Someone Else")


def test_students_are_listed_in_id_order(service):
    service.add_student("3", "Third")
    service.add_student("1", "First")
    service.add_student("2", "Second")
    assert [s.student_id for s in service.list_students()] == ["1", "2", "3"]


def test_an_unknown_student_raises_student_not_found(service):
    with pytest.raises(StudentNotFoundError, match="404"):
        service.get_student("404")


def test_a_student_records_the_department_and_semester(service):
    student = service.add_student(
        "241337037", "Soron", department="CSE", semester=5
    )
    assert student.department == "CSE"
    assert student.semester == 5


# ======================================================================
# requirement 2 - add a course
# ======================================================================
def test_a_course_can_be_added(service):
    course = service.add_course("CSE402", "Software Engineering", credit=Decimal("3.00"))
    assert course.code == "CSE402"
    assert course.title == "Software Engineering"
    assert course.credit == Decimal("3.00")


def test_course_codes_are_unique(service):
    service.add_course("CSE402", "Software Engineering")
    with pytest.raises(DuplicateCourseError):
        service.add_course("CSE402", "Another course with the same code")


def test_a_course_needs_a_credit_value(service):
    course = service.add_course("CSE402", "Software Engineering")
    assert course.credit == Decimal("3.00")  # the default


def test_courses_are_listed_in_code_order(service):
    service.add_course("MATH201", "Discrete Mathematics")
    service.add_course("CSE402", "Software Engineering")
    assert [c.code for c in service.list_courses()] == ["CSE402", "MATH201"]


def test_an_unknown_course_raises_course_not_found(service):
    with pytest.raises(CourseNotFoundError):
        service.get_course("CSE999")


# ======================================================================
# enrollment
# ======================================================================
def test_a_student_can_be_enrolled_in_a_course(service):
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    enrollment = service.enroll("241337037", "CSE402")
    assert enrollment.student_id == "241337037"
    assert enrollment.course_code == "CSE402"


def test_enrolling_an_unknown_student_fails(service):
    service.add_course("CSE402", "Software Engineering")
    with pytest.raises(StudentNotFoundError):
        service.enroll("404", "CSE402")


def test_enrolling_in_an_unknown_course_fails(service):
    service.add_student("241337037", "Soron")
    with pytest.raises(CourseNotFoundError):
        service.enroll("241337037", "CSE999")


def test_a_student_cannot_be_enrolled_twice(service):
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    with pytest.raises(AlreadyEnrolledError):
        service.enroll("241337037", "CSE402")


def test_the_enrolled_courses_of_a_student_are_listed(service):
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.add_course("CSE403", "Database Systems")
    service.enroll("241337037", "CSE403")
    service.enroll("241337037", "CSE402")
    assert [c.code for c in service.enrolled_courses("241337037")] == [
        "CSE402",
        "CSE403",
    ]


# ======================================================================
# requirement 3 - enter marks, rejecting anything outside 0-100
# ======================================================================
def test_a_mark_can_be_recorded(service):
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    record = service.record_mark("241337037", "CSE402", 86)
    assert record.mark == Decimal("86")
    assert service.get_mark("241337037", "CSE402").mark == Decimal("86")


@pytest.mark.parametrize("mark", [-1, -0.01, 100.01, 150, 1000])
def test_a_mark_outside_the_range_is_rejected(service, mark):
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    with pytest.raises(InvalidMarkError):
        service.record_mark("241337037", "CSE402", mark)


def test_a_rejected_mark_is_not_stored(service):
    """A rejected mark must not leave a half-written record behind."""
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    with pytest.raises(InvalidMarkError):
        service.record_mark("241337037", "CSE402", 120)
    assert service.get_mark("241337037", "CSE402") is None


@pytest.mark.parametrize("mark", [0, 50, 100])
def test_the_range_ends_are_accepted(service, mark):
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    assert service.record_mark("241337037", "CSE402", mark).mark == Decimal(mark)


def test_a_mark_can_be_given_as_a_string(service):
    """The CLI passes marks as strings; they are converted, not rejected."""
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    assert service.record_mark("241337037", "CSE402", "78.5").mark == Decimal("78.5")


def test_a_mark_for_a_student_who_is_not_enrolled_is_rejected(service):
    """A mark can only be recorded against an enrollment."""
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    with pytest.raises(NotEnrolledError, match="not enrolled"):
        service.record_mark("241337037", "CSE402", 86)


def test_a_mark_for_an_unknown_student_is_rejected(service):
    service.add_course("CSE402", "Software Engineering")
    with pytest.raises(StudentNotFoundError):
        service.record_mark("404", "CSE402", 86)


def test_a_mark_for_an_unknown_course_is_rejected(service):
    service.add_student("241337037", "Soron")
    with pytest.raises(CourseNotFoundError):
        service.record_mark("241337037", "CSE999", 86)


def test_re_entering_a_mark_replaces_the_old_one(service):
    """A course appears once on a result sheet, never twice."""
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    service.record_mark("241337037", "CSE402", 50)
    service.record_mark("241337037", "CSE402", 90)
    assert service.get_mark("241337037", "CSE402").mark == Decimal("90")
    assert len(service.list_marks("241337037")) == 1


def test_the_recording_metadata_is_kept(service_with_clock):
    """Who entered the mark and when are part of the audit trail."""
    service = service_with_clock
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    record = service.record_mark("241337037", "CSE402", 86, recorded_by="Prof. Rahman")
    assert record.recorded_by == "Prof. Rahman"
    assert record.recorded_at == datetime(2026, 11, 19, 10, 30, 0)


def test_marks_can_be_listed_for_one_student(service):
    service.add_student("241337037", "Soron")
    service.add_student("241337038", "Other")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    service.enroll("241337038", "CSE402")
    service.record_mark("241337037", "CSE402", 86)
    service.record_mark("241337038", "CSE402", 60)
    mine = service.list_marks("241337037")
    assert len(mine) == 1
    assert mine[0].mark == Decimal("86")


# ======================================================================
# requirement 6 - the result sheet
# ======================================================================
def test_the_result_sheet_lists_every_enrolled_course(service):
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering", credit=Decimal("3.00"))
    service.add_course("CSE403", "Database Systems", credit=Decimal("3.00"))
    service.enroll("241337037", "CSE402")
    service.enroll("241337037", "CSE403")
    service.record_mark("241337037", "CSE402", 86)

    sheet = service.result_sheet("241337037")
    codes = [outcome.course.code for outcome in sheet.outcomes]
    assert codes == ["CSE402", "CSE403"]


def test_the_result_sheet_shows_mark_grade_and_point(service):
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering", credit=Decimal("3.00"))
    service.enroll("241337037", "CSE402")
    service.record_mark("241337037", "CSE402", 86)

    outcome = service.result_sheet("241337037").outcomes[0]
    assert outcome.mark == Decimal("86")
    assert outcome.grade == "A+"
    assert outcome.point == Decimal("4.00")


def test_a_course_with_no_mark_yet_shows_as_not_graded(service):
    """Pending work is visible on the sheet instead of being hidden."""
    service.add_student("241337037", "Soron")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("241337037", "CSE402")
    outcome = service.result_sheet("241337037").outcomes[0]
    assert outcome.mark is None
    assert outcome.grade == "-"
    assert outcome.point is None
    assert outcome.is_graded is False


def test_a_result_sheet_for_an_unknown_student_is_rejected(service):
    with pytest.raises(StudentNotFoundError):
        service.result_sheet("404")


def test_result_sheets_can_be_built_for_everyone(service):
    service.add_student("241337037", "Soron")
    service.add_student("241337038", "Other")
    assert len(service.result_sheets()) == 2


# ======================================================================
# course statistics (an extra beyond the brief)
# ======================================================================
def test_course_statistics_summarise_the_marks(service):
    service.add_student("1", "First")
    service.add_student("2", "Second")
    service.add_course("CSE402", "Software Engineering")
    service.enroll("1", "CSE402")
    service.enroll("2", "CSE402")
    service.record_mark("1", "CSE402", 80)
    service.record_mark("2", "CSE402", 30)

    stats = service.course_statistics("CSE402")
    assert stats.students_graded == 2
    assert stats.average == Decimal("55.00")
    assert stats.highest == Decimal("80")
    assert stats.lowest == Decimal("30")
    assert stats.pass_count == 1
    assert stats.fail_count == 1
    assert stats.pass_rate == Decimal("50.00")


def test_course_statistics_for_a_course_with_no_marks(service):
    service.add_course("CSE402", "Software Engineering")
    stats = service.course_statistics("CSE402")
    assert stats.students_graded == 0
    assert stats.average is None
    assert stats.pass_rate is None

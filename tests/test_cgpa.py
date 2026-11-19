"""Tests for the credit-weighted CGPA - requirement 5."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gradevault.domain.grading import GradeScale
from gradevault.domain.result import Transcript


@pytest.fixture()
def grader(service):
    """A helper that registers a student, courses, enrollments and marks.

    Usage::

        grader("241337037", [("CSE402", "3.00", 86), ("CSE403", "4.00", 70)])
    """

    def _grader(student_id, courses, credit="3.00"):
        service.add_student(student_id, "Test Student")
        for index, (code, course_credit, mark) in enumerate(courses):
            service.add_course(code, f"Course {index}", credit=Decimal(course_credit))
            service.enroll(student_id, code)
            if mark is not None:
                service.record_mark(student_id, code, mark)
        return service.result_sheet(student_id)

    return _grader


def test_a_single_course_gives_its_own_grade_point(grader):
    """With one course the CGPA is simply that course's grade point."""
    sheet = grader("1", [("CSE402", "3.00", 86)])
    assert sheet.cgpa == Decimal("4.00")


def test_the_cgpa_is_weighted_by_credit(grader):
    """The heart of requirement 5.

    4 credits at A+ (4.00) and 1 credit at D (2.00) give
    (4.00*4 + 2.00*1) / 5 = 3.60 - *not* the unweighted average of 3.00.
    """
    sheet = grader("1", [("CSE402", "4.00", 80), ("CSE403", "1.00", 44)])
    assert sheet.cgpa == Decimal("3.60")
    assert sheet.cgpa != Decimal("3.00")


def test_an_unweighted_average_would_be_different(grader):
    """A test that fails if the weighting is removed."""
    sheet = grader("1", [("CSE402", "4.00", 80), ("CSE403", "1.00", 44)])
    unweighted = (Decimal("4.00") + Decimal("2.00")) / 2
    assert sheet.cgpa != unweighted.quantize(Decimal("0.01"))


def test_equal_weighted_courses_average_out(grader):
    """(4.00 + 3.00) / 2 = 3.50 when both courses carry the same credit."""
    sheet = grader("1", [("CSE402", "3.00", 80), ("CSE403", "3.00", 64)])
    assert sheet.cgpa == Decimal("3.50")


def test_a_failing_course_still_counts_in_the_denominator(grader):
    """A fail carries a zero grade point, but its credit is still attempted."""
    sheet = grader("1", [("CSE402", "3.00", 80), ("CSE403", "3.00", 20)])
    assert sheet.cgpa == Decimal("2.00")


def test_a_student_with_no_marks_has_no_cgpa(grader):
    """There is nothing to average, so the CGPA is undefined, not zero."""
    sheet = grader("1", [("CSE402", "3.00", None)])
    assert sheet.cgpa is None
    assert sheet.total_credits == Decimal("0")


def test_a_course_with_no_mark_is_excluded_from_the_cgpa(grader):
    """A pending course must not drag the CGPA down."""
    sheet = grader("1", [("CSE402", "3.00", 86), ("CSE403", "3.00", None)])
    assert sheet.cgpa == Decimal("4.00")
    assert sheet.attempted_credits == Decimal("6.00")
    assert sheet.total_credits == Decimal("3.00")


def test_the_cgpa_is_rounded_to_two_places(grader):
    """(4.00*1 + 3.75*1) / 2 = 3.875, which is shown as 3.88."""
    sheet = grader("1", [("CSE402", "1.00", 80), ("CSE403", "1.00", 75)])
    assert sheet.cgpa == Decimal("3.88")


def test_the_cgpa_is_exact_and_not_a_float_artefact(service):
    """Decimal arithmetic keeps 3.875 exact instead of 3.8749999999999996."""
    service.add_student("1", "Test")
    service.add_course("CSE402", "A", credit=Decimal("1.00"))
    service.add_course("CSE403", "B", credit=Decimal("1.00"))
    service.enroll("1", "CSE402")
    service.enroll("1", "CSE403")
    service.record_mark("1", "CSE402", 80)
    service.record_mark("1", "CSE403", 75)
    sheet = service.result_sheet("1")
    assert sheet.cgpa == Decimal("3.88")
    assert str(sheet.cgpa) == "3.88"
    assert "3.87499" not in str(sheet.cgpa)


def test_the_credit_totals_are_reported(grader):
    """The sheet shows how many credits were earned and how many were attempted."""
    sheet = grader("1", [("CSE402", "3.00", 86), ("CSE403", "4.00", 70)])
    assert sheet.total_credits == Decimal("7.00")
    assert sheet.attempted_credits == Decimal("7.00")


def test_the_grade_distribution_is_summarised(grader):
    sheet = grader("1", [("CSE402", "3.00", 86), ("CSE403", "3.00", 64)])
    assert sheet.letter_summary == "A+:1  B:1"


def test_a_failed_course_is_listed(grader):
    sheet = grader("1", [("CSE402", "3.00", 86), ("CSE403", "3.00", 20)])
    assert sheet.failed_courses == ("CSE403",)
    assert sheet.passed is False


def test_a_passing_student_is_marked_as_passed(grader):
    sheet = grader("1", [("CSE402", "3.00", 86)])
    assert sheet.passed is True
    assert sheet.failed_courses == ()


def test_a_custom_scale_changes_the_cgpa(service):
    """The CGPA is derived from the injected scale, not from a hard-coded table."""
    scale = GradeScale.from_rows([(50, 100, "P", "1.00"), (0, 49, "N", "0.00")])
    service.scale = scale
    service.add_student("1", "Test")
    service.add_course("CSE402", "A", credit=Decimal("1.00"))
    service.enroll("1", "CSE402")
    service.record_mark("1", "CSE402", 80)
    assert service.result_sheet("1").cgpa == Decimal("1.00")


def test_the_transcript_can_be_built_directly():
    """``Transcript.build`` is usable without the service."""
    from gradevault.domain.course import Course
    from gradevault.domain.grading import DEFAULT_SCALE
    from gradevault.domain.student import Student

    student = Student(student_id="1", name="Test")
    courses = [Course(code="CSE402", title="A", credit=Decimal("3.00"))]
    sheet = Transcript.build(student, courses, {"CSE402": Decimal("86")}, DEFAULT_SCALE)
    assert sheet.cgpa == Decimal("4.00")
    assert sheet.outcomes[0].grade == "A+"


def test_a_transcript_with_no_courses_is_empty_but_valid(service):
    service.add_student("1", "Test")
    sheet = service.result_sheet("1")
    assert sheet.outcomes == ()
    assert sheet.cgpa is None

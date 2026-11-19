"""The application service - the use cases of GradeVault.

:class:`ResultService` is the single entry point the CLI (and any other front
end) talks to.  It owns the *rules about who may do what*: a mark can only be
recorded for a student who is registered and enrolled in the course, and a
student must exist before a transcript can be produced.

The service deliberately does no formatting.  It returns domain objects; the
rendering of a result sheet lives in :mod:`gradevault.application.export` and in
the CLI package.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date, datetime
from decimal import Decimal

from ..domain.assessment import MarkRecord
from ..domain.course import Course
from ..domain.enrollment import Enrollment
from ..domain.errors import (
    AlreadyEnrolledError,
    CourseNotFoundError,
    NotEnrolledError,
    StudentNotFoundError,
)
from ..domain.grading import DEFAULT_SCALE, GradeScale, normalise_mark
from ..domain.result import CourseOutcome, Transcript
from ..domain.student import Student, normalise_student_id
from ..infrastructure.repository import GradeVaultRepository

__all__ = ["ResultService", "CourseStatistics"]


class CourseStatistics:
    """Aggregate information about one course's marks.

    Attributes:
        course: The course the statistics describe.
        students_graded: How many students have a mark in the course.
        average: The arithmetic mean mark, or ``None`` when nobody is graded.
        highest: The best mark recorded, or ``None``.
        lowest: The worst mark recorded, or ``None``.
        pass_count: How many students scored a non-zero grade point.
        fail_count: How many students failed the course.
    """

    __slots__ = (
        "course",
        "students_graded",
        "average",
        "highest",
        "lowest",
        "pass_count",
        "fail_count",
    )

    def __init__(
        self,
        course: Course,
        students_graded: int,
        average: Decimal | None,
        highest: Decimal | None,
        lowest: Decimal | None,
        pass_count: int,
        fail_count: int,
    ) -> None:
        self.course = course
        self.students_graded = students_graded
        self.average = average
        self.highest = highest
        self.lowest = lowest
        self.pass_count = pass_count
        self.fail_count = fail_count

    @property
    def pass_rate(self) -> Decimal | None:
        """Percentage of graded students who passed, or ``None`` if ungraded."""
        if self.students_graded == 0:
            return None
        passed = Decimal(self.pass_count) * Decimal(100) / Decimal(self.students_graded)
        return passed.quantize(Decimal("0.01"))

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"CourseStatistics({self.course.code}, graded={self.students_graded}, "
            f"average={self.average})"
        )


class ResultService:
    """Use cases for recording marks and producing results.

    Args:
        repository: Where the data is stored.
        scale: The grading scale to apply.  Defaults to the CSE402 table.
        clock: Callable returning the current time; injected in tests so that
            timestamps are deterministic.
    """

    def __init__(
        self,
        repository: GradeVaultRepository,
        scale: GradeScale = DEFAULT_SCALE,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.repository = repository
        self.scale = scale
        self._clock = clock

    # ------------------------------------------------------------------
    # students
    # ------------------------------------------------------------------
    def add_student(
        self,
        student_id: str,
        name: str,
        department: str = "Undeclared",
        semester: int = 1,
        enrolled_on: date | None = None,
    ) -> Student:
        """Register a new student.

        Raises:
            DuplicateStudentError: The ID is already taken.
            ValueError: The ID or the name is not usable.
        """
        student = Student(
            student_id=normalise_student_id(student_id),
            name=name,
            department=department,
            semester=semester,
            enrolled_on=enrolled_on or date.today(),
        )
        self.repository.add_student(student)
        return student

    def get_student(self, student_id: str) -> Student:
        """Return a student, raising :class:`StudentNotFoundError` if absent."""
        student = self.repository.get_student(student_id)
        if student is None:
            raise StudentNotFoundError(f"no student with ID {student_id!r}")
        return student

    def list_students(self) -> list[Student]:
        """Return every registered student, ordered by ID."""
        return self.repository.list_students()

    # ------------------------------------------------------------------
    # courses
    # ------------------------------------------------------------------
    def add_course(self, code: str, title: str, credit: object = Decimal("3.00")) -> Course:
        """Register a new course.

        Raises:
            DuplicateCourseError: The code is already taken.
            InvalidCreditError: The credit value is not a positive number.
        """
        course = Course(code=code, title=title, credit=credit)
        self.repository.add_course(course)
        return course

    def get_course(self, code: str) -> Course:
        """Return a course, raising :class:`CourseNotFoundError` if absent."""
        course = self.repository.get_course(code)
        if course is None:
            raise CourseNotFoundError(f"no course with code {code!r}")
        return course

    def list_courses(self) -> list[Course]:
        """Return every registered course, ordered by code."""
        return self.repository.list_courses()

    # ------------------------------------------------------------------
    # enrollment
    # ------------------------------------------------------------------
    def enroll(self, student_id: str, course_code: str) -> Enrollment:
        """Enrol a student in a course.

        Raises:
            StudentNotFoundError: No such student.
            CourseNotFoundError: No such course.
            AlreadyEnrolledError: The pair is already enrolled.
        """
        student = self.get_student(student_id)
        course = self.get_course(course_code)
        if self.repository.is_enrolled(student.student_id, course.code):
            raise AlreadyEnrolledError(
                f"{student.student_id} is already enrolled in {course.code}"
            )
        enrollment = Enrollment(student_id=student.student_id, course_code=course.code)
        self.repository.enroll(enrollment)
        return enrollment

    def list_enrollments(self, student_id: str | None = None) -> list[Enrollment]:
        """Return enrollments, optionally filtered to one student."""
        return self.repository.list_enrollments(student_id)

    def enrolled_courses(self, student_id: str) -> list[Course]:
        """Return the courses a student is enrolled in, ordered by code."""
        self.get_student(student_id)
        return self.repository.enrolled_courses(normalise_student_id(student_id))

    # ------------------------------------------------------------------
    # marks
    # ------------------------------------------------------------------
    def record_mark(
        self,
        student_id: str,
        course_code: str,
        mark: object,
        recorded_by: str = "teacher",
    ) -> MarkRecord:
        """Record (or replace) the mark of a student in a course.

        Raises:
            StudentNotFoundError: No such student.
            CourseNotFoundError: No such course.
            NotEnrolledError: The student is not enrolled in the course.
            InvalidMarkError: The mark is outside 0-100 or is not a number.
        """
        student = self.get_student(student_id)
        course = self.get_course(course_code)
        if not self.repository.is_enrolled(student.student_id, course.code):
            raise NotEnrolledError(
                f"{student.student_id} is not enrolled in {course.code}"
            )

        value = normalise_mark(mark)
        record = MarkRecord(
            student_id=student.student_id,
            course_code=course.code,
            mark=value,
            recorded_at=self._clock(),
            recorded_by=recorded_by,
        )
        self.repository.save_mark(record)
        return record

    def get_mark(self, student_id: str, course_code: str) -> MarkRecord | None:
        """Return the recorded mark for a student/course pair, or ``None``."""
        return self.repository.get_mark(
            normalise_student_id(student_id), course_code.strip().upper()
        )

    def list_marks(self, student_id: str | None = None) -> list[MarkRecord]:
        """Return every recorded mark, optionally filtered to one student."""
        return self.repository.list_marks(student_id)

    # ------------------------------------------------------------------
    # results
    # ------------------------------------------------------------------
    def result_sheet(self, student_id: str) -> Transcript:
        """Build the result sheet (transcript) of a student.

        Raises:
            StudentNotFoundError: No such student.
        """
        student = self.get_student(student_id)
        courses = self.repository.enrolled_courses(student.student_id)
        marks = {
            record.course_code: record.mark
            for record in self.repository.list_marks(student.student_id)
        }
        return Transcript.build(student, courses, marks, self.scale)

    def result_sheets(self) -> list[Transcript]:
        """Build a result sheet for every student, ordered by ID."""
        return [self.result_sheet(student.student_id) for student in self.list_students()]

    def course_statistics(self, course_code: str) -> CourseStatistics:
        """Summarise the marks recorded in one course.

        Raises:
            CourseNotFoundError: No such course.
        """
        course = self.get_course(course_code)
        records = [
            record
            for record in self.repository.list_marks()
            if record.course_code == course.code
        ]
        if not records:
            return CourseStatistics(course, 0, None, None, None, 0, 0)

        values = [record.mark for record in records]
        total = sum(values, Decimal("0"))
        average = (total / Decimal(len(values))).quantize(Decimal("0.01"))
        passed = 0
        for value in values:
            if self.scale.point_for(value) > 0:
                passed += 1
        return CourseStatistics(
            course=course,
            students_graded=len(values),
            average=average,
            highest=max(values),
            lowest=min(values),
            pass_count=passed,
            fail_count=len(values) - passed,
        )

    def all_course_statistics(self) -> list[CourseStatistics]:
        """Summarise every course that has at least one recorded mark."""
        graded_codes = {record.course_code for record in self.repository.list_marks()}
        return [
            self.course_statistics(code)
            for code in sorted(graded_codes)
        ]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def scale_table(self) -> Sequence[tuple[str, str, str]]:
        """Return the grading scale as printable ``(range, letter, point)`` rows."""
        return self.scale.as_table()

    def outcomes_for(self, student_id: str) -> Sequence[CourseOutcome]:
        """Return the per-course outcomes of a student's result sheet."""
        return self.result_sheet(student_id).outcomes

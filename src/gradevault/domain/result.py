"""Result aggregation: course outcomes, CGPA and the transcript.

The CGPA definition used here is the standard credit-weighted one:

.. math::

    \\mathrm{CGPA} = \\frac{\\sum_i (\\text{point}_i \\times \\text{credit}_i)}
                           {\\sum_i \\text{credit}_i}

Only courses that have a recorded mark take part in the sum - a course the
student is enrolled in but has not been graded yet is listed on the transcript
as *not graded* and contributes nothing to the denominator.  Without that rule
a student with one pending course would see their CGPA silently drop.

All arithmetic uses :class:`~decimal.Decimal`, so a CGPA such as
``(4.00*3 + 3.75*3) / 6 = 3.875`` is exact rather than ``3.8749999999999996``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .course import Course
from .grading import GradeScale
from .student import Student

__all__ = ["CourseOutcome", "Transcript", "CREDIT_WEIGHTED_CGPA"]

#: Name of the CGPA formula, used in the documentation and the CLI output.
CREDIT_WEIGHTED_CGPA = "credit-weighted"

_TWO_PLACES = Decimal("0.01")


def _round2(value: Decimal) -> Decimal:
    """Round a Decimal to two places, half-up (the way a marksheet shows it)."""
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class CourseOutcome:
    """The result of one course for one student.

    Attributes:
        course: The course this outcome refers to.
        mark: The mark on 0-100, or ``None`` when the course is not graded yet.
        grade: The letter grade (``"A+"`` ...), or ``"-"`` when not graded.
        point: The grade point, or ``None`` when not graded.
    """

    course: Course
    mark: Decimal | None
    grade: str
    point: Decimal | None

    @property
    def credit(self) -> Decimal:
        """Credit weight of the course."""
        return self.course.credit

    @property
    def is_graded(self) -> bool:
        """``True`` when a mark has been recorded for this course."""
        return self.mark is not None and self.point is not None

    @property
    def weighted_points(self) -> Decimal:
        """Grade points multiplied by credit - the numerator contribution."""
        if not self.is_graded:
            return Decimal("0")
        return self.point * self.credit  # type: ignore[union-attr]

    @property
    def mark_display(self) -> str:
        """The mark as shown on a result sheet."""
        if self.mark is None:
            return "-"
        return f"{self.mark.normalize():f}"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.course.code}: {self.mark_display} {self.grade}"


@dataclass(frozen=True, slots=True)
class Transcript:
    """A student's full result sheet.

    Attributes:
        student: The student the transcript belongs to.
        outcomes: One :class:`CourseOutcome` per course the student is enrolled in.
        cgpa: The credit-weighted CGPA over graded courses, or ``None`` when no
            course has been graded yet.
        total_credits: Sum of the credits of every graded course.
        attempted_credits: Sum of the credits of every enrolled course.
    """

    student: Student
    outcomes: tuple[CourseOutcome, ...]
    cgpa: Decimal | None
    total_credits: Decimal
    attempted_credits: Decimal
    formula: str = CREDIT_WEIGHTED_CGPA

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    @classmethod
    def build(
        cls,
        student: Student,
        courses: Sequence[Course],
        marks: dict[str, Decimal],
        scale: GradeScale,
    ) -> Transcript:
        """Assemble a transcript.

        Args:
            student: The student concerned.
            courses: Every course the student is enrolled in.
            marks: Mapping of ``course_code -> mark`` for the courses that have
                been graded.  Courses absent from the mapping are shown as not
                graded.
            scale: The grading scale used to derive letters and points.
        """
        outcomes: list[CourseOutcome] = []
        for course in courses:
            mark = marks.get(course.code)
            if mark is None:
                outcomes.append(
                    CourseOutcome(course=course, mark=None, grade="-", point=None)
                )
                continue
            letter, point = scale.classify(mark)
            outcomes.append(
                CourseOutcome(course=course, mark=mark, grade=letter, point=point)
            )

        graded = [outcome for outcome in outcomes if outcome.is_graded]
        attempted = sum((outcome.credit for outcome in outcomes), Decimal("0"))
        earned = sum((outcome.weighted_points for outcome in graded), Decimal("0"))
        graded_credits = sum((outcome.credit for outcome in graded), Decimal("0"))

        cgpa = _round2(earned / graded_credits) if graded_credits > 0 else None

        return cls(
            student=student,
            outcomes=tuple(outcomes),
            cgpa=cgpa,
            total_credits=graded_credits,
            attempted_credits=attempted,
        )

    # ------------------------------------------------------------------
    # derived information
    # ------------------------------------------------------------------
    @property
    def graded_outcomes(self) -> tuple[CourseOutcome, ...]:
        """The outcomes that carry a mark."""
        return tuple(outcome for outcome in self.outcomes if outcome.is_graded)

    @property
    def pending_outcomes(self) -> tuple[CourseOutcome, ...]:
        """The outcomes that have no mark yet."""
        return tuple(outcome for outcome in self.outcomes if not outcome.is_graded)

    @property
    def passed(self) -> bool:
        """``True`` when every graded course has a non-zero grade point."""
        return all(outcome.point is not None and outcome.point > 0 for outcome in self.graded_outcomes)

    @property
    def failed_courses(self) -> tuple[str, ...]:
        """Codes of the graded courses that earned a zero grade point."""
        return tuple(
            outcome.course.code
            for outcome in self.graded_outcomes
            if outcome.point is not None and outcome.point == 0
        )

    @property
    def letter_summary(self) -> str:
        """A compact ``A+:3  B:2  F:1`` style summary of the grade distribution."""
        counts: dict[str, int] = {}
        for outcome in self.graded_outcomes:
            counts[outcome.grade] = counts.get(outcome.grade, 0) + 1
        return "  ".join(f"{letter}:{count}" for letter, count in sorted(counts.items()))

    def outcome_for(self, course_code: str) -> CourseOutcome | None:
        """Return the outcome for *course_code*, or ``None`` if not enrolled."""
        wanted = course_code.strip().upper()
        for outcome in self.outcomes:
            if outcome.course.code == wanted:
                return outcome
        return None

    def __iter__(self) -> Iterable[CourseOutcome]:  # pragma: no cover - cosmetic
        return iter(self.outcomes)

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        cgpa_text = "n/a" if self.cgpa is None else f"{self.cgpa:.2f}"
        return f"{self.student.student_id}: CGPA {cgpa_text}"

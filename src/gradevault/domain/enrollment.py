"""Enrollment: the link between a student and a course.

A mark may only be recorded for a student/course pair that has an enrollment.
Modelling the link explicitly (instead of inferring it from marks) means a
student can be registered in a course before any teaching happens, and it lets
the result sheet list courses with no mark yet as *not graded* rather than
silently omitting them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .course import normalise_course_code
from .student import normalise_student_id

__all__ = ["Enrollment"]


@dataclass(frozen=True, slots=True)
class Enrollment:
    """A student's registration in a course.

    Attributes:
        student_id: ID of the enrolled student.
        course_code: Code of the course.
        enrolled_on: Date the enrollment was made.
    """

    student_id: str
    course_code: str
    enrolled_on: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        object.__setattr__(self, "student_id", normalise_student_id(self.student_id))
        object.__setattr__(self, "course_code", normalise_course_code(self.course_code))
        if not self.student_id:
            raise ValueError("enrollment needs a student ID")
        if not self.course_code:
            raise ValueError("enrollment needs a course code")
        if not isinstance(self.enrolled_on, date):
            raise ValueError("enrolled_on must be a date")

    @property
    def key(self) -> tuple[str, str]:
        """Return the natural key of the enrollment: ``(student_id, course_code)``."""
        return (self.student_id, self.course_code)

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.student_id} -> {self.course_code}"

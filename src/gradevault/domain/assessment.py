"""Assessment records - the marks themselves.

A :class:`MarkRecord` is immutable and keeps a small audit trail: who entered
the mark (``recorded_by``) and when (``recorded_at``).  Re-entering a mark for
the same student/course *replaces* the previous record rather than appending a
second one, so a transcript never shows a course twice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .course import normalise_course_code
from .grading import normalise_mark
from .student import normalise_student_id

__all__ = ["MarkRecord"]


@dataclass(frozen=True, slots=True)
class MarkRecord:
    """A single mark for one student in one course.

    Attributes:
        student_id: ID of the student the mark belongs to.
        course_code: Code of the course the mark belongs to.
        mark: The mark on a 0-100 scale.
        recorded_at: When the mark was entered.
        recorded_by: Who entered the mark.
    """

    student_id: str
    course_code: str
    mark: object = field(default=None)
    recorded_at: datetime = field(default_factory=datetime.now)
    recorded_by: str = "system"

    def __post_init__(self) -> None:
        object.__setattr__(self, "student_id", normalise_student_id(self.student_id))
        object.__setattr__(self, "course_code", normalise_course_code(self.course_code))
        object.__setattr__(self, "mark", normalise_mark(self.mark))
        object.__setattr__(self, "recorded_by", str(self.recorded_by).strip() or "system")
        if not isinstance(self.recorded_at, datetime):
            raise ValueError("recorded_at must be a datetime")

    @property
    def key(self) -> tuple[str, str]:
        """Return the natural key of the record: ``(student_id, course_code)``."""
        return (self.student_id, self.course_code)

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.student_id} {self.course_code} = {self.mark}"

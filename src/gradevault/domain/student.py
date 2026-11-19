"""The :class:`Student` entity.

A student is identified by an ID that must be unique across the system; that
uniqueness is enforced by the repository, while this class is responsible for
the *shape* of a student - a non-empty, normalised ID and a non-empty name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

__all__ = ["Student", "normalise_student_id"]

#: Student IDs are alphanumeric with dashes/underscores, e.g. "241337037".
_STUDENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")


def normalise_student_id(student_id: str) -> str:
    """Trim and upper-case a student ID so ``" 241337037 "`` and ``"241337037"``
    are the same student."""
    if not isinstance(student_id, str):
        raise TypeError("student_id must be a string")
    return student_id.strip().upper()


@dataclass(frozen=True, slots=True)
class Student:
    """A registered student.

    Attributes:
        student_id: Unique identifier, e.g. ``"241337037"``.
        name: Full name of the student.
        department: Department the student belongs to.
        semester: Current semester number.
        enrolled_on: Date the student was registered.
    """

    student_id: str
    name: str
    department: str = "Undeclared"
    semester: int = 1
    enrolled_on: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        object.__setattr__(self, "student_id", normalise_student_id(self.student_id))
        object.__setattr__(self, "name", " ".join(self.name.split()))

        if not self.student_id:
            raise ValueError("student ID must not be empty")
        if not _STUDENT_ID_PATTERN.match(self.student_id):
            raise ValueError(
                "student ID must be 1-32 characters of letters, digits, '-' or '_'"
            )
        if not self.name:
            raise ValueError("student name must not be empty")
        if self.department is not None and not self.department.strip():
            object.__setattr__(self, "department", "Undeclared")
        if not isinstance(self.semester, int) or isinstance(self.semester, bool):
            raise ValueError("semester must be an integer")
        if self.semester < 1:
            raise ValueError("semester must be 1 or greater")

    @property
    def initials(self) -> str:
        """Return the student's initials, e.g. ``"MRS"``."""
        parts = [part for part in self.name.split() if part]
        if not parts:
            return ""
        return "".join(part[0].upper() for part in parts)

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.student_id} - {self.name}"

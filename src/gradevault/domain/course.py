"""The :class:`Course` entity.

A course carries the three attributes the brief asks for - a code, a title and
a credit value - and the credit value is what weights a student's CGPA, so it
is stored as a :class:`~decimal.Decimal` and must be strictly positive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .errors import InvalidCreditError

__all__ = ["Course", "normalise_course_code"]

#: Course codes look like "CSE402" or "ENG-101".
_COURSE_CODE_PATTERN = re.compile(r"^[A-Za-z]{2,6}[-_]?\d{2,4}[A-Za-z]?$")

#: The largest credit value we accept for a single course.
MAX_CREDIT = Decimal("12")


def normalise_course_code(course_code: str) -> str:
    """Trim and upper-case a course code so lookups are case-insensitive."""
    if not isinstance(course_code, str):
        raise TypeError("course_code must be a string")
    return course_code.strip().upper().replace(" ", "")


@dataclass(frozen=True, slots=True)
class Course:
    """A course a student can be enrolled in.

    Attributes:
        code: Unique course code, e.g. ``"CSE402"``.
        title: Human readable title of the course.
        credit: Credit value, strictly positive and at most 12.
    """

    code: str
    title: str
    credit: Decimal = Decimal("3.00")

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", normalise_course_code(self.code))
        object.__setattr__(self, "title", " ".join(self.title.split()))

        if not self.code:
            raise ValueError("course code must not be empty")
        if not _COURSE_CODE_PATTERN.match(self.code):
            raise ValueError(
                "course code must look like 'CSE402' (2-6 letters, then 2-4 digits)"
            )
        if not self.title:
            raise ValueError("course title must not be empty")

        credit = self.credit
        if isinstance(credit, bool) or not isinstance(credit, (int, float, Decimal, str)):
            raise InvalidCreditError(f"credit must be a number, got {credit!r}")
        try:
            credit = Decimal(str(credit))
        except (InvalidOperation, ValueError):
            raise InvalidCreditError(f"credit must be a number, got {credit!r}") from None
        if not credit.is_finite() or credit <= 0:
            raise InvalidCreditError(f"credit must be greater than zero, got {credit}")
        if credit > MAX_CREDIT:
            raise InvalidCreditError(f"credit must not exceed {MAX_CREDIT}, got {credit}")
        object.__setattr__(self, "credit", credit)

    @property
    def credit_display(self) -> str:
        """Return the credit formatted the way it appears on a result sheet."""
        text = f"{self.credit:.2f}"
        return text.rstrip("0").rstrip(".")

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.code} - {self.title} ({self.credit_display} cr)"

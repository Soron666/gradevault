"""GradeVault - a Student Result Manager for CSE402.

GradeVault lets a teacher register students and courses, record marks, and
produce a credit-weighted CGPA and a printable result sheet.

Layers:

* ``gradevault.domain`` - entities, the grading scale and the CGPA rule.
* ``gradevault.application`` - the use cases and the result-sheet rendering.
* ``gradevault.infrastructure`` - the repositories (in-memory and SQLite).
* ``gradevault.cli`` - the command line front end.
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Md. Ragib Shahriyer Soron"

from .domain.course import Course
from .domain.grading import DEFAULT_SCALE, GradeScale
from .domain.result import CourseOutcome, Transcript
from .domain.student import Student

__all__ = [
    "Course",
    "CourseOutcome",
    "DEFAULT_SCALE",
    "GradeScale",
    "Student",
    "Transcript",
    "__version__",
]

"""Domain layer of GradeVault.

This package holds the *business rules* and nothing else: no database, no
files, no printing.  Everything here is pure Python and can be unit tested in
isolation, which is where most of the test suite lives.
"""

from __future__ import annotations

from .assessment import MarkRecord
from .course import Course, normalise_course_code
from .enrollment import Enrollment
from .errors import (
    AlreadyEnrolledError,
    CourseNotFoundError,
    DuplicateCourseError,
    DuplicateStudentError,
    EntityNotFoundError,
    GradeVaultError,
    InvalidCreditError,
    InvalidMarkError,
    NotEnrolledError,
    StorageError,
    StudentNotFoundError,
    ValidationError,
)
from .grading import DEFAULT_SCALE, GradeBand, GradeScale, normalise_mark
from .result import CREDIT_WEIGHTED_CGPA, CourseOutcome, Transcript
from .student import Student, normalise_student_id

__all__ = [
    "AlreadyEnrolledError",
    "CREDIT_WEIGHTED_CGPA",
    "Course",
    "CourseNotFoundError",
    "CourseOutcome",
    "DEFAULT_SCALE",
    "DuplicateCourseError",
    "DuplicateStudentError",
    "Enrollment",
    "EntityNotFoundError",
    "GradeBand",
    "GradeScale",
    "GradeVaultError",
    "InvalidCreditError",
    "InvalidMarkError",
    "MarkRecord",
    "NotEnrolledError",
    "StorageError",
    "Student",
    "StudentNotFoundError",
    "Transcript",
    "ValidationError",
    "normalise_course_code",
    "normalise_mark",
    "normalise_student_id",
]

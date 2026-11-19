"""Exception hierarchy for the GradeVault domain.

Every error raised by the domain layer derives from :class:`GradeVaultError`, so
the application layer (and the CLI) can catch a single base class and report a
friendly message instead of a stack trace.

The hierarchy is deliberately split into *validation* problems (the caller gave
us bad input) and *lookup* problems (the caller referenced something that does
not exist).  Both are recoverable, user-facing conditions, unlike a programming
error such as ``TypeError``.
"""

from __future__ import annotations

__all__ = [
    "GradeVaultError",
    "ValidationError",
    "DuplicateStudentError",
    "DuplicateCourseError",
    "InvalidMarkError",
    "InvalidCreditError",
    "EntityNotFoundError",
    "StudentNotFoundError",
    "CourseNotFoundError",
    "NotEnrolledError",
    "AlreadyEnrolledError",
    "StorageError",
]


class GradeVaultError(Exception):
    """Base class for every error the application raises on purpose."""


class ValidationError(GradeVaultError):
    """The caller supplied input that breaks a domain invariant."""


class DuplicateStudentError(ValidationError):
    """A student with this ID already exists (student IDs must be unique)."""


class DuplicateCourseError(ValidationError):
    """A course with this code already exists (course codes must be unique)."""


class InvalidMarkError(ValidationError):
    """A mark was outside the allowed 0-100 range, or was not a number."""


class InvalidCreditError(ValidationError):
    """A course credit value was not a positive number."""


class EntityNotFoundError(GradeVaultError):
    """A referenced entity does not exist in the repository."""


class StudentNotFoundError(EntityNotFoundError):
    """No student is registered under the requested ID."""


class CourseNotFoundError(EntityNotFoundError):
    """No course is registered under the requested code."""


class NotEnrolledError(GradeVaultError):
    """A mark was submitted for a student/course pair with no enrollment."""


class AlreadyEnrolledError(GradeVaultError):
    """The student/course pair has already been enrolled."""


class StorageError(GradeVaultError):
    """The persistence layer could not complete the requested operation."""

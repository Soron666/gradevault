"""A small demonstration dataset.

Used by the ``gradevault demo`` command so that a fresh clone can show a real
result sheet within seconds of being cloned.  The data is fictional.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..domain.errors import (
    AlreadyEnrolledError,
    DuplicateCourseError,
    DuplicateStudentError,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..application.service import ResultService

__all__ = [
    "seed_demo_data",
    "DEMO_STUDENTS",
    "DEMO_COURSES",
    "DEMO_ENROLLMENTS",
    "DEMO_MARKS",
]

DEMO_STUDENTS = (
    ("241337037", "Md. Ragib Shahriyer Soron", "Computer Science & Engineering", 5),
    ("241337038", "Nusrat Jahan Oishi", "Computer Science & Engineering", 5),
    ("241337039", "Tanvir Ahmed Chowdhury", "Computer Science & Engineering", 5),
    ("241337040", "Farhana Akter Mim", "Computer Science & Engineering", 3),
)

DEMO_COURSES = (
    ("CSE402", "Software Engineering", "3.00"),
    ("CSE403", "Database Systems", "3.00"),
    ("CSE410", "Artificial Intelligence", "4.00"),
    ("MATH201", "Discrete Mathematics", "3.00"),
)

#: ``(student_id, course_code)`` pairs.
DEMO_ENROLLMENTS = (
    ("241337037", "CSE402"),
    ("241337037", "CSE403"),
    ("241337037", "CSE410"),
    ("241337037", "MATH201"),
    ("241337038", "CSE402"),
    ("241337038", "CSE403"),
    ("241337038", "MATH201"),
    ("241337039", "CSE402"),
    ("241337039", "CSE410"),
    ("241337040", "CSE402"),
    ("241337040", "MATH201"),
)

#: ``(student_id, course_code, mark)`` triples.
DEMO_MARKS = (
    ("241337037", "CSE402", "86"),
    ("241337037", "CSE403", "78"),
    ("241337037", "CSE410", "92"),
    ("241337037", "MATH201", "71"),
    ("241337038", "CSE402", "64"),
    ("241337038", "CSE403", "81"),
    ("241337038", "MATH201", "58"),
    ("241337039", "CSE402", "47"),
    ("241337039", "CSE410", "73"),
    ("241337040", "CSE402", "88"),
    ("241337040", "MATH201", "39"),
)


def seed_demo_data(service: ResultService) -> dict[str, int]:
    """Populate *service* with the demonstration dataset.

    Anything that already exists is left alone, so the command is safe to run
    twice against the same database.

    Returns:
        A count of what was created.
    """
    counts = {"students": 0, "courses": 0, "enrollments": 0, "marks": 0}

    for student_id, name, department, semester in DEMO_STUDENTS:
        try:
            service.add_student(
                student_id, name, department=department, semester=semester
            )
            counts["students"] += 1
        except DuplicateStudentError:
            pass  # already present - seeding is idempotent

    for code, title, credit in DEMO_COURSES:
        try:
            service.add_course(code, title, credit=credit)
            counts["courses"] += 1
        except DuplicateCourseError:
            pass  # already present - seeding is idempotent

    for student_id, course_code in DEMO_ENROLLMENTS:
        try:
            service.enroll(student_id, course_code)
            counts["enrollments"] += 1
        except AlreadyEnrolledError:
            pass  # already present - seeding is idempotent

    for student_id, course_code, mark in DEMO_MARKS:
        try:
            service.record_mark(student_id, course_code, mark, recorded_by="demo")
            counts["marks"] += 1
        except (DuplicateStudentError, DuplicateCourseError, AlreadyEnrolledError):
            pass  # already present - seeding is idempotent

    return counts

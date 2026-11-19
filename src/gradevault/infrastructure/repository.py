"""Persistence for GradeVault.

Two implementations sit behind the same :class:`GradeVaultRepository` protocol:

* :class:`InMemoryRepository` - a dictionary-backed store used by the tests and
  by the CLI's ``--memory`` mode.  Fast, isolated, no files touched.
* :class:`SqliteRepository` - the real store.  A single SQLite file holds
  students, courses, enrollments and marks, so a teacher's work survives a
  restart.

Both refuse to create a duplicate student ID or course code, which is how the
"student IDs must be unique" requirement is enforced.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import closing, contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..domain.course import Course
from ..domain.enrollment import Enrollment
from ..domain.errors import (
    DuplicateCourseError,
    DuplicateStudentError,
    StorageError,
)
from ..domain.student import Student

__all__ = ["GradeVaultRepository", "InMemoryRepository", "SqliteRepository"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id   TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    department   TEXT NOT NULL,
    semester     INTEGER NOT NULL,
    enrolled_on  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    code         TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    credit       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    student_id   TEXT NOT NULL,
    course_code  TEXT NOT NULL,
    enrolled_on  TEXT NOT NULL,
    PRIMARY KEY (student_id, course_code),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_code) REFERENCES courses(code)
);

CREATE TABLE IF NOT EXISTS marks (
    student_id   TEXT NOT NULL,
    course_code  TEXT NOT NULL,
    mark         TEXT NOT NULL,
    recorded_at  TEXT NOT NULL,
    recorded_by  TEXT NOT NULL,
    PRIMARY KEY (student_id, course_code),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_code) REFERENCES courses(code)
);
"""


@runtime_checkable
class GradeVaultRepository(Protocol):
    """The storage contract the application layer depends on."""

    def add_student(self, student: Student) -> None:
        """Store *student*.  Raise ``DuplicateStudentError`` if the ID exists."""

    def get_student(self, student_id: str) -> Student | None:
        """Return the student with this ID, or ``None``."""

    def list_students(self) -> list[Student]:
        """Return every student, ordered by ID."""

    def add_course(self, course: Course) -> None:
        """Store *course*.  Raise ``DuplicateCourseError`` if the code exists."""

    def get_course(self, code: str) -> Course | None:
        """Return the course with this code, or ``None``."""

    def list_courses(self) -> list[Course]:
        """Return every course, ordered by code."""

    def enroll(self, enrollment: Enrollment) -> None:
        """Store *enrollment*."""

    def is_enrolled(self, student_id: str, course_code: str) -> bool:
        """Return ``True`` when the student/course pair is enrolled."""

    def list_enrollments(self, student_id: str | None = None) -> list[Enrollment]:
        """Return enrollments, optionally filtered to one student."""

    def save_mark(self, record) -> None:
        """Insert or replace the mark for a student/course pair."""

    def get_mark(self, student_id: str, course_code: str) -> object | None:
        """Return the mark record for a student/course pair, or ``None``."""

    def list_marks(self, student_id: str | None = None) -> list[object]:
        """Return mark records, optionally filtered to one student."""

    def enrolled_courses(self, student_id: str) -> list[Course]:
        """Return the courses a student is enrolled in, ordered by code."""


class InMemoryRepository:
    """A dictionary-backed :class:`GradeVaultRepository`."""

    def __init__(self) -> None:
        self._students: dict[str, Student] = {}
        self._courses: dict[str, Course] = {}
        self._enrollments: dict[tuple[str, str], Enrollment] = {}
        self._marks: dict[tuple[str, str], object] = {}

    # -- students ------------------------------------------------------
    def add_student(self, student: Student) -> None:
        if student.student_id in self._students:
            raise DuplicateStudentError(
                f"a student with ID {student.student_id} already exists"
            )
        self._students[student.student_id] = student

    def get_student(self, student_id: str) -> Student | None:
        return self._students.get(student_id.strip().upper())

    def list_students(self) -> list[Student]:
        return [self._students[key] for key in sorted(self._students)]

    # -- courses -------------------------------------------------------
    def add_course(self, course: Course) -> None:
        if course.code in self._courses:
            raise DuplicateCourseError(
                f"a course with code {course.code} already exists"
            )
        self._courses[course.code] = course

    def get_course(self, code: str) -> Course | None:
        return self._courses.get(code.strip().upper())

    def list_courses(self) -> list[Course]:
        return [self._courses[key] for key in sorted(self._courses)]

    # -- enrollments ---------------------------------------------------
    def enroll(self, enrollment: Enrollment) -> None:
        self._enrollments[enrollment.key] = enrollment

    def is_enrolled(self, student_id: str, course_code: str) -> bool:
        key = (student_id.strip().upper(), course_code.strip().upper())
        return key in self._enrollments

    def list_enrollments(self, student_id: str | None = None) -> list[Enrollment]:
        records = list(self._enrollments.values())
        if student_id is not None:
            wanted = student_id.strip().upper()
            records = [item for item in records if item.student_id == wanted]
        return sorted(records, key=lambda item: (item.student_id, item.course_code))

    # -- marks ---------------------------------------------------------
    def save_mark(self, record) -> None:
        self._marks[record.key] = record

    def get_mark(self, student_id: str, course_code: str) -> object | None:
        key = (student_id.strip().upper(), course_code.strip().upper())
        return self._marks.get(key)

    def list_marks(self, student_id: str | None = None) -> list[object]:
        records = list(self._marks.values())
        if student_id is not None:
            wanted = student_id.strip().upper()
            records = [item for item in records if item.student_id == wanted]
        return sorted(records, key=lambda item: (item.student_id, item.course_code))

    # -- helpers -------------------------------------------------------
    def enrolled_courses(self, student_id: str) -> list[Course]:
        """Return the courses a student is enrolled in, ordered by code."""
        codes = {
            enrollment.course_code
            for enrollment in self.list_enrollments(student_id)
        }
        return [course for course in self.list_courses() if course.code in codes]

    def clear(self) -> None:
        """Drop everything.  Used by the tests between cases."""
        self._students.clear()
        self._courses.clear()
        self._enrollments.clear()
        self._marks.clear()


class SqliteRepository:
    """A SQLite-backed :class:`GradeVaultRepository`.

    Args:
        database: Path to the SQLite file.  ``":memory:"`` opens a private
            in-memory database, which is handy for tests.
    """

    def __init__(self, database: str | Path = ":memory:") -> None:
        self.database = str(database)
        if self.database != ":memory:":
            Path(self.database).expanduser().parent.mkdir(parents=True, exist_ok=True)
        try:
            self._connection = sqlite3.connect(self.database)
        except sqlite3.Error as exc:  # pragma: no cover - depends on the file system
            raise StorageError(f"cannot open database {self.database!r}: {exc}") from exc
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        with closing(self._connection.cursor()) as cursor:
            cursor.executescript(_SCHEMA)
        self._connection.commit()

    # -- plumbing ------------------------------------------------------
    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        try:
            with closing(self._connection.cursor()) as cursor:
                yield cursor
            self._connection.commit()
        except sqlite3.Error as exc:
            self._connection.rollback()
            raise StorageError(f"database error: {exc}") from exc

    # -- students ------------------------------------------------------
    def add_student(self, student: Student) -> None:
        if self.get_student(student.student_id) is not None:
            raise DuplicateStudentError(
                f"a student with ID {student.student_id} already exists"
            )
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO students (student_id, name, department, semester, enrolled_on)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    student.student_id,
                    student.name,
                    student.department,
                    student.semester,
                    student.enrolled_on.isoformat(),
                ),
            )

    def get_student(self, student_id: str) -> Student | None:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM students WHERE student_id = ?", (student_id.strip().upper(),)
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return Student(
            student_id=row["student_id"],
            name=row["name"],
            department=row["department"],
            semester=row["semester"],
            enrolled_on=date.fromisoformat(row["enrolled_on"]),
        )

    def list_students(self) -> list[Student]:
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM students ORDER BY student_id")
            rows = cursor.fetchall()
        return [
            Student(
                student_id=row["student_id"],
                name=row["name"],
                department=row["department"],
                semester=row["semester"],
                enrolled_on=date.fromisoformat(row["enrolled_on"]),
            )
            for row in rows
        ]

    # -- courses -------------------------------------------------------
    def add_course(self, course: Course) -> None:
        if self.get_course(course.code) is not None:
            raise DuplicateCourseError(
                f"a course with code {course.code} already exists"
            )
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO courses (code, title, credit) VALUES (?, ?, ?)",
                (course.code, course.title, str(course.credit)),
            )

    def get_course(self, code: str) -> Course | None:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM courses WHERE code = ?", (code.strip().upper(),)
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return Course(code=row["code"], title=row["title"], credit=Decimal(row["credit"]))

    def list_courses(self) -> list[Course]:
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM courses ORDER BY code")
            rows = cursor.fetchall()
        return [
            Course(code=row["code"], title=row["title"], credit=Decimal(row["credit"]))
            for row in rows
        ]

    # -- enrollments ---------------------------------------------------
    def enroll(self, enrollment: Enrollment) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO enrollments (student_id, course_code, enrolled_on)"
                " VALUES (?, ?, ?)",
                (
                    enrollment.student_id,
                    enrollment.course_code,
                    enrollment.enrolled_on.isoformat(),
                ),
            )

    def is_enrolled(self, student_id: str, course_code: str) -> bool:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM enrollments WHERE student_id = ? AND course_code = ?",
                (student_id.strip().upper(), course_code.strip().upper()),
            )
            return cursor.fetchone() is not None

    def list_enrollments(self, student_id: str | None = None) -> list[Enrollment]:
        query = "SELECT * FROM enrollments"
        params: tuple[str, ...] = ()
        if student_id is not None:
            query += " WHERE student_id = ?"
            params = (student_id.strip().upper(),)
        query += " ORDER BY student_id, course_code"
        with self._cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [
            Enrollment(
                student_id=row["student_id"],
                course_code=row["course_code"],
                enrolled_on=date.fromisoformat(row["enrolled_on"]),
            )
            for row in rows
        ]

    # -- marks ---------------------------------------------------------
    def save_mark(self, record) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO marks"
                " (student_id, course_code, mark, recorded_at, recorded_by)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    record.student_id,
                    record.course_code,
                    str(record.mark),
                    record.recorded_at.isoformat(),
                    record.recorded_by,
                ),
            )

    def get_mark(self, student_id: str, course_code: str) -> object | None:
        from ..domain.assessment import MarkRecord

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM marks WHERE student_id = ? AND course_code = ?",
                (student_id.strip().upper(), course_code.strip().upper()),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return MarkRecord(
            student_id=row["student_id"],
            course_code=row["course_code"],
            mark=Decimal(row["mark"]),
            recorded_at=datetime.fromisoformat(row["recorded_at"]),
            recorded_by=row["recorded_by"],
        )

    def list_marks(self, student_id: str | None = None) -> list[object]:
        from ..domain.assessment import MarkRecord

        query = "SELECT * FROM marks"
        params: tuple[str, ...] = ()
        if student_id is not None:
            query += " WHERE student_id = ?"
            params = (student_id.strip().upper(),)
        query += " ORDER BY student_id, course_code"
        with self._cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [
            MarkRecord(
                student_id=row["student_id"],
                course_code=row["course_code"],
                mark=Decimal(row["mark"]),
                recorded_at=datetime.fromisoformat(row["recorded_at"]),
                recorded_by=row["recorded_by"],
            )
            for row in rows
        ]

    # -- helpers -------------------------------------------------------
    def enrolled_courses(self, student_id: str) -> list[Course]:
        """Return the courses a student is enrolled in, ordered by code."""
        codes = {
            enrollment.course_code for enrollment in self.list_enrollments(student_id)
        }
        return [course for course in self.list_courses() if course.code in codes]

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with contextlib.suppress(sqlite3.Error):  # pragma: no cover - defensive
            self._connection.close()

    def __enter__(self) -> SqliteRepository:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def open_repository(database: str | Path = ":memory:") -> GradeVaultRepository:
    """Return the repository appropriate for *database*.

    ``":memory:"`` (the default) gives an :class:`InMemoryRepository`; anything
    else gives a :class:`SqliteRepository` backed by that file.
    """
    if str(database) == ":memory:":
        return InMemoryRepository()
    return SqliteRepository(database)


def describe_repository(repository: GradeVaultRepository) -> Sequence[str]:
    """Return a few human-readable facts about a repository (used by the CLI)."""
    return (
        type(repository).__name__,
        f"students={len(repository.list_students())}",
        f"courses={len(repository.list_courses())}",
    )

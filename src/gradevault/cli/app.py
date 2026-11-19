"""The GradeVault command line interface.

Run ``python -m gradevault --help`` for the full list of commands.  The CLI is
a thin shell around :class:`~gradevault.application.service.ResultService`: it
parses arguments, calls one use case, and prints the result.  Every expected
failure (duplicate ID, mark out of range, unknown student) is reported as a
readable message with a non-zero exit code rather than a traceback.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from ..application.export import result_sheet_csv, result_sheet_text
from ..application.service import ResultService
from ..domain.errors import GradeVaultError
from ..infrastructure.repository import (
    GradeVaultRepository,
    InMemoryRepository,
    SqliteRepository,
)
from ..rendering import render_table

__all__ = ["main", "build_parser"]

PROGRAM = "gradevault"
DEFAULT_DATABASE = "gradevault.db"


# ----------------------------------------------------------------------
# argument parsing
# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the whole program."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="GradeVault - record student marks and produce result sheets.",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DATABASE,
        metavar="PATH",
        help=f"SQLite database file to use (default: {DEFAULT_DATABASE})",
    )
    parser.add_argument(
        "--memory",
        action="store_true",
        help="use a throw-away in-memory database instead of a file",
    )

    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    # student ---------------------------------------------------------
    student = commands.add_parser("student", help="manage students")
    student_commands = student.add_subparsers(dest="subcommand", metavar="SUBCOMMAND")

    student_add = student_commands.add_parser("add", help="register a new student")
    student_add.add_argument("--id", required=True, help="unique student ID")
    student_add.add_argument("--name", required=True, help="full name")
    student_add.add_argument("--department", default="Undeclared", help="department")
    student_add.add_argument("--semester", type=int, default=1, help="semester number")

    student_commands.add_parser("list", help="list every student")

    student_show = student_commands.add_parser("show", help="show one student's record")
    student_show.add_argument("--id", required=True, help="student ID")

    # course ----------------------------------------------------------
    course = commands.add_parser("course", help="manage courses")
    course_commands = course.add_subparsers(dest="subcommand", metavar="SUBCOMMAND")

    course_add = course_commands.add_parser("add", help="register a new course")
    course_add.add_argument("--code", required=True, help="course code, e.g. CSE402")
    course_add.add_argument("--title", required=True, help="course title")
    course_add.add_argument("--credit", default="3.00", help="credit value (default 3.00)")

    course_commands.add_parser("list", help="list every course")

    # enroll ----------------------------------------------------------
    enroll = commands.add_parser("enroll", help="enrol a student in a course")
    enroll.add_argument("--student", required=True, help="student ID")
    enroll.add_argument("--course", required=True, help="course code")

    # mark ------------------------------------------------------------
    mark = commands.add_parser("mark", help="record marks")
    mark_commands = mark.add_subparsers(dest="subcommand", metavar="SUBCOMMAND")
    mark_enter = mark_commands.add_parser("enter", help="enter a mark")
    mark_enter.add_argument("--student", required=True, help="student ID")
    mark_enter.add_argument("--course", required=True, help="course code")
    mark_enter.add_argument("--mark", required=True, help="mark between 0 and 100")
    mark_enter.add_argument("--by", default="teacher", help="who is entering the mark")

    # result ----------------------------------------------------------
    result = commands.add_parser("result", help="show a student's result sheet")
    result.add_argument("--student", required=True, help="student ID")
    result.add_argument("--csv", action="store_true", help="print CSV instead of a table")
    result.add_argument("--out", metavar="FILE", help="write the sheet to a file")

    # stats -----------------------------------------------------------
    stats = commands.add_parser("stats", help="course statistics")
    stats.add_argument("--course", help="limit to one course code")

    commands.add_parser("scale", help="print the grading scale")
    commands.add_parser("demo", help="load a small demo dataset")

    return parser


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _open_repository(args: argparse.Namespace) -> GradeVaultRepository:
    """Return the repository selected by the global options."""
    if args.memory:
        return InMemoryRepository()
    return SqliteRepository(args.db)


def _print_students(service: ResultService, stream: TextIO) -> int:
    students = service.list_students()
    if not students:
        print("No students registered yet.", file=stream)
        return 0
    rows = [
        (
            student.student_id,
            student.name,
            student.department,
            student.semester,
            student.enrolled_on.isoformat(),
        )
        for student in students
    ]
    print(
        render_table(
            ("ID", "Name", "Department", "Sem", "Registered"),
            rows,
            aligns=["left", "left", "left", "right", "left"],
        ),
        file=stream,
    )
    return 0


def _print_courses(service: ResultService, stream: TextIO) -> int:
    courses = service.list_courses()
    if not courses:
        print("No courses registered yet.", file=stream)
        return 0
    rows = [
        (course.code, course.title, course.credit_display) for course in courses
    ]
    print(
        render_table(("Code", "Title", "Credit"), rows, aligns=["left", "left", "right"]),
        file=stream,
    )
    return 0


def _print_stats(service: ResultService, course_code: str | None, stream: TextIO) -> int:
    statistics = (
        [service.course_statistics(course_code)]
        if course_code
        else service.all_course_statistics()
    )
    if not statistics:
        print("No marks recorded yet.", file=stream)
        return 0
    rows = []
    for item in statistics:
        average = "-" if item.average is None else f"{item.average:.2f}"
        rows.append(
            (
                item.course.code,
                item.students_graded,
                average,
                "-" if item.highest is None else f"{item.highest}",
                "-" if item.lowest is None else f"{item.lowest}",
                item.pass_count,
                item.fail_count,
            )
        )
    print(
        render_table(
            ("Course", "Graded", "Average", "Highest", "Lowest", "Pass", "Fail"),
            rows,
            aligns=["left", "right", "right", "right", "right", "right", "right"],
        ),
        file=stream,
    )
    return 0


def _load_demo(service: ResultService, stream: TextIO) -> int:
    """Populate the database with a small demonstration dataset."""
    from ..infrastructure.seed import seed_demo_data

    created = seed_demo_data(service)
    print(
        f"Loaded demo data: {created['students']} students, "
        f"{created['courses']} courses, {created['enrollments']} enrollments, "
        f"{created['marks']} marks.",
        file=stream,
    )
    print("Try:  gradevault result --student 241337037", file=stream)
    return 0


# ----------------------------------------------------------------------
# command dispatch
# ----------------------------------------------------------------------
def _run(args: argparse.Namespace, service: ResultService, stream: TextIO) -> int:
    """Execute the parsed command.  Returns the process exit code."""
    command = args.command

    if command is None:
        build_parser().print_help(stream)
        return 2

    if command == "student":
        sub = args.subcommand
        if sub == "add":
            student = service.add_student(
                args.id,
                args.name,
                department=args.department,
                semester=args.semester,
            )
            print(f"Registered student {student.student_id} ({student.name}).", file=stream)
            return 0
        if sub == "list":
            return _print_students(service, stream)
        if sub == "show":
            student = service.get_student(args.id)
            courses = service.enrolled_courses(student.student_id)
            print(f"{student.student_id}  {student.name}", file=stream)
            print(f"Department : {student.department}", file=stream)
            print(f"Semester   : {student.semester}", file=stream)
            print(f"Enrolled in: {', '.join(c.code for c in courses) or '-'}", file=stream)
            return 0
        build_parser().print_help(stream)
        return 2

    if command == "course":
        sub = args.subcommand
        if sub == "add":
            course = service.add_course(args.code, args.title, credit=args.credit)
            print(
                f"Registered course {course.code} - {course.title} "
                f"({course.credit_display} credits).",
                file=stream,
            )
            return 0
        if sub == "list":
            return _print_courses(service, stream)
        build_parser().print_help(stream)
        return 2

    if command == "enroll":
        enrollment = service.enroll(args.student, args.course)
        print(
            f"Enrolled {enrollment.student_id} in {enrollment.course_code}.",
            file=stream,
        )
        return 0

    if command == "mark":
        sub = args.subcommand
        if sub == "enter":
            record = service.record_mark(
                args.student, args.course, args.mark, recorded_by=args.by
            )
            letter, point = service.scale.classify(record.mark)
            print(
                f"Recorded {record.mark} for {record.student_id} in "
                f"{record.course_code} -> grade {letter} (point {point:.2f}).",
                file=stream,
            )
            return 0
        build_parser().print_help(stream)
        return 2

    if command == "result":
        transcript = service.result_sheet(args.student)
        text = result_sheet_csv(transcript) if args.csv else result_sheet_text(transcript)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"Result sheet written to {args.out}.", file=stream)
        else:
            print(text, file=stream)
        return 0

    if command == "stats":
        return _print_stats(service, args.course, stream)

    if command == "scale":
        rows = service.scale_table()
        print(
            render_table(
                ("Marks", "Grade", "Point"),
                rows,
                aligns=["left", "center", "right"],
            ),
            file=stream,
        )
        return 0

    if command == "demo":
        return _load_demo(service, stream)

    build_parser().print_help(stream)
    return 2


def main(
    argv: Sequence[str] | None = None,
    stream: TextIO | None = None,
    error_stream: TextIO | None = None,
) -> int:
    """Run the CLI.

    Args:
        argv: Arguments to parse.  Defaults to ``sys.argv[1:]``.
        stream: Where normal output goes.  Defaults to ``sys.stdout``.
        error_stream: Where error messages go.  Defaults to ``sys.stderr``.

    Returns:
        ``0`` on success, ``1`` when the command failed for an expected
        reason, ``2`` for a usage error.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stream if stream is not None else sys.stdout
    err = error_stream if error_stream is not None else sys.stderr

    try:
        repository = _open_repository(args)
    except GradeVaultError as exc:
        print(f"error: {exc}", file=err)
        return 1

    service = ResultService(repository)
    try:
        return _run(args, service, out)
    except GradeVaultError as exc:
        print(f"error: {exc}", file=err)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=err)
        return 1
    finally:
        close = getattr(repository, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

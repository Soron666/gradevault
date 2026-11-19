"""Rendering a result sheet into text and CSV.

The brief asks the program to "show a student's result sheet, listing each
course, the mark, the grade, the grade point and the CGPA".  This module turns
a :class:`~gradevault.domain.result.Transcript` into that listing - as a
box-drawn table for the screen, and as CSV for the records department.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence

from ..domain.result import Transcript
from ..rendering import render_key_values, render_table

__all__ = [
    "result_sheet_text",
    "result_sheet_csv",
    "transcript_summary",
    "RESULT_SHEET_HEADERS",
]

#: The columns of the result sheet, in order.
RESULT_SHEET_HEADERS = ("Course", "Title", "Credit", "Mark", "Grade", "Point")


def _rows(transcript: Transcript) -> list[tuple[str, str, str, str, str, str]]:
    rows = []
    for outcome in transcript.outcomes:
        point = "-" if outcome.point is None else f"{outcome.point:.2f}"
        rows.append(
            (
                outcome.course.code,
                outcome.course.title,
                outcome.course.credit_display,
                outcome.mark_display,
                outcome.grade,
                point,
            )
        )
    return rows


def transcript_summary(transcript: Transcript) -> list[tuple[str, object]]:
    """Return the header block of a result sheet as label/value pairs."""
    student = transcript.student
    cgpa = "n/a" if transcript.cgpa is None else f"{transcript.cgpa:.2f}"
    return [
        ("Student ID", student.student_id),
        ("Name", student.name),
        ("Department", student.department),
        ("Semester", student.semester),
        ("Registered on", student.enrolled_on.isoformat()),
        ("CGPA", cgpa),
        ("Credits earned", f"{transcript.total_credits:.2f}"),
        ("Credits attempted", f"{transcript.attempted_credits:.2f}"),
        ("Graded courses", len(transcript.graded_outcomes)),
        ("Pending courses", len(transcript.pending_outcomes)),
        ("Grade distribution", transcript.letter_summary or "-"),
        ("Result", "PASS" if transcript.passed and transcript.graded_outcomes else "FAIL"),
    ]


def result_sheet_text(transcript: Transcript, width: int = 78) -> str:
    """Render the full result sheet of *transcript* as a printable string."""
    title = "STUDENT RESULT SHEET"
    rule = "=" * min(width, 78)
    table = render_table(
        RESULT_SHEET_HEADERS,
        _rows(transcript),
        aligns=["left", "left", "right", "right", "center", "right"],
    )
    summary = render_key_values(transcript_summary(transcript))
    parts = [
        rule,
        title.center(min(width, 78)),
        rule,
        summary,
        "",
        table,
        "",
        f"CGPA (credit-weighted) : {'n/a' if transcript.cgpa is None else f'{transcript.cgpa:.2f}'}",
        rule,
    ]
    return "\n".join(parts)


def result_sheet_csv(transcript: Transcript) -> str:
    """Render the result sheet of *transcript* as CSV text."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "student_id",
            "student_name",
            "department",
            "semester",
            "course_code",
            "course_title",
            "credit",
            "mark",
            "grade",
            "grade_point",
            "cgpa",
        ]
    )
    cgpa = "" if transcript.cgpa is None else f"{transcript.cgpa:.2f}"
    for outcome in transcript.outcomes:
        writer.writerow(
            [
                transcript.student.student_id,
                transcript.student.name,
                transcript.student.department,
                transcript.student.semester,
                outcome.course.code,
                outcome.course.title,
                f"{outcome.course.credit:.2f}",
                "" if outcome.mark is None else f"{outcome.mark}",
                outcome.grade,
                "" if outcome.point is None else f"{outcome.point:.2f}",
                cgpa,
            ]
        )
    return buffer.getvalue()


def cohort_summary(transcript: Transcript) -> Sequence[str]:
    """Return short, printable lines describing a result sheet."""
    cgpa = "n/a" if transcript.cgpa is None else f"{transcript.cgpa:.2f}"
    return (
        f"{transcript.student.student_id}  {transcript.student.name}",
        f"  CGPA {cgpa}   credits {transcript.total_credits:.2f}/{transcript.attempted_credits:.2f}",
        f"  grades: {transcript.letter_summary or '-'}",
    )

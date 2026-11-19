"""Tests for the result-sheet rendering - requirement 6."""

from __future__ import annotations

import csv
import io
from decimal import Decimal

import pytest

from gradevault.application.export import (
    RESULT_SHEET_HEADERS,
    result_sheet_csv,
    result_sheet_text,
    transcript_summary,
)
from gradevault.rendering import render_key_values, render_table


@pytest.fixture()
def sheet(service):
    """A result sheet with two graded courses and one pending course."""
    service.add_student("241337037", "Md. Ragib Shahriyer Soron", "CSE", 5)
    service.add_course("CSE402", "Software Engineering", credit=Decimal("3.00"))
    service.add_course("CSE403", "Database Systems", credit=Decimal("3.00"))
    service.add_course("CSE410", "Artificial Intelligence", credit=Decimal("4.00"))
    service.enroll("241337037", "CSE402")
    service.enroll("241337037", "CSE403")
    service.enroll("241337037", "CSE410")
    service.record_mark("241337037", "CSE402", 86)
    service.record_mark("241337037", "CSE403", 78)
    return service.result_sheet("241337037")


def test_the_text_sheet_contains_the_student_identity(sheet):
    text = result_sheet_text(sheet)
    assert "241337037" in text
    assert "Md. Ragib Shahriyer Soron" in text
    assert "STUDENT RESULT SHEET" in text


def test_the_text_sheet_lists_every_course_with_its_mark(sheet):
    text = result_sheet_text(sheet)
    assert "CSE402" in text
    assert "CSE403" in text
    assert "CSE410" in text
    assert "86" in text
    assert "78" in text


def test_the_text_sheet_shows_the_grade_and_the_grade_point(sheet):
    text = result_sheet_text(sheet)
    assert "A+" in text
    assert "3.75" in text  # the point of an A
    assert "4.00" in text  # the point of an A+


def test_the_text_sheet_shows_the_cgpa(sheet):
    """(4.00*3 + 3.75*3) / 6 = 3.88 after rounding to two places."""
    text = result_sheet_text(sheet)
    assert "3.88" in text
    assert "CGPA" in text


def test_the_text_sheet_marks_a_pending_course(sheet):
    text = result_sheet_text(sheet)
    assert "CSE410" in text
    assert "Pending courses" in text


def test_the_summary_reports_the_credit_totals(sheet):
    summary = dict(transcript_summary(sheet))
    assert summary["Student ID"] == "241337037"
    assert summary["CGPA"] == "3.88"
    assert summary["Credits earned"] == "6.00"
    assert summary["Credits attempted"] == "10.00"
    assert summary["Graded courses"] == 2
    assert summary["Pending courses"] == 1


def test_the_csv_sheet_has_a_row_per_course(sheet):
    rows = list(csv.reader(io.StringIO(result_sheet_csv(sheet))))
    assert len(rows) == 4  # one header + three courses
    assert rows[0][:3] == ["student_id", "student_name", "department"]
    assert rows[0][-1] == "cgpa"


def test_the_csv_sheet_carries_the_marks_and_grades(sheet):
    rows = list(csv.reader(io.StringIO(result_sheet_csv(sheet))))
    body = rows[1:]
    cse402 = next(row for row in body if row[4] == "CSE402")
    assert cse402[7] == "86"
    assert cse402[8] == "A+"
    assert cse402[9] == "4.00"
    assert cse402[10] == "3.88"


def test_the_csv_sheet_leaves_a_pending_course_blank(sheet):
    rows = list(csv.reader(io.StringIO(result_sheet_csv(sheet))))
    pending = next(row for row in rows[1:] if row[4] == "CSE410")
    assert pending[7] == ""
    assert pending[8] == "-"


def test_the_headers_are_the_columns_the_brief_asks_for():
    """Course, mark, grade and grade point must all be there."""
    assert "Course" in RESULT_SHEET_HEADERS
    assert "Mark" in RESULT_SHEET_HEADERS
    assert "Grade" in RESULT_SHEET_HEADERS
    assert "Point" in RESULT_SHEET_HEADERS


def test_the_table_renderer_draws_a_box():
    text = render_table(("A", "B"), [("1", "2")])
    assert text.startswith("+")
    assert "|" in text
    assert text.count("\n") == 4


def test_the_table_renderer_right_aligns_numbers():
    text = render_table(("N",), [("1",), ("100",)], aligns=["right"])
    assert "  1 |" in text
    assert "100 |" in text


def test_the_table_renderer_handles_an_empty_body():
    text = render_table(("A",), [])
    assert "A" in text


def test_the_key_value_renderer_aligns_the_values():
    text = render_key_values([("Name", "Soron"), ("ID", "241337037")])
    assert text.splitlines()[0].strip().startswith("Name")
    assert "Soron" in text

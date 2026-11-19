"""Tests for the Course entity."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gradevault.domain.course import Course, normalise_course_code
from gradevault.domain.errors import InvalidCreditError


def test_a_course_keeps_its_code_title_and_credit():
    course = Course(code="CSE402", title="Software Engineering", credit=Decimal("3.00"))
    assert course.code == "CSE402"
    assert course.title == "Software Engineering"
    assert course.credit == Decimal("3.00")


def test_the_course_code_is_normalised():
    """' cse402 ' and 'CSE402' are the same course."""
    assert Course(code=" cse402 ", title="x").code == "CSE402"
    assert normalise_course_code(" cse-402 ") == "CSE-402"


@pytest.mark.parametrize("code", ["CSE402", "ENG101", "MATH-201", "CS 402"])
def test_valid_course_codes_are_accepted(code):
    assert Course(code=code, title="A course").code


@pytest.mark.parametrize("code", ["", "   ", "C", "CSE", "402", "CSE_", "CS E", "CSE4O"])
def test_malformed_course_codes_are_rejected(code):
    with pytest.raises(ValueError, match="course code must"):
        Course(code=code, title="A course")


def test_an_empty_title_is_rejected():
    with pytest.raises(ValueError, match="title must not be empty"):
        Course(code="CSE402", title="   ")


@pytest.mark.parametrize("credit", [0, Decimal("0"), -1, Decimal("-2.5"), "abc", None])
def test_a_credit_value_must_be_positive(credit):
    with pytest.raises(InvalidCreditError):
        Course(code="CSE402", title="A course", credit=credit)


def test_a_credit_above_twelve_is_rejected():
    with pytest.raises(InvalidCreditError, match="must not exceed"):
        Course(code="CSE402", title="A course", credit=Decimal("13"))


def test_a_credit_given_as_a_string_is_accepted():
    course = Course(code="CSE402", title="A course", credit="3.00")
    assert course.credit == Decimal("3.00")


def test_the_credit_display_drops_a_trailing_zero():
    """3.00 is shown as 3 and 3.50 is shown as 3.5 on a result sheet."""
    assert Course(code="CSE402", title="x", credit=Decimal("3.00")).credit_display == "3"
    assert Course(code="CSE403", title="x", credit=Decimal("3.50")).credit_display == "3.5"
    assert Course(code="CSE404", title="x", credit=Decimal("4.00")).credit_display == "4"


def test_the_course_str_reads_well():
    course = Course(code="CSE402", title="Software Engineering", credit=Decimal("3.00"))
    assert str(course) == "CSE402 - Software Engineering (3 cr)"

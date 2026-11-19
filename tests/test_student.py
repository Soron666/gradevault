"""Tests for the Student entity."""

from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from gradevault.domain.student import Student, normalise_student_id


def test_a_student_keeps_its_id_and_name():
    student = Student(student_id="241337037", name="Md. Ragib Shahriyer Soron")
    assert student.student_id == "241337037"
    assert student.name == "Md. Ragib Shahriyer Soron"


def test_the_student_id_is_normalised_to_upper_case():
    """IDs are compared case-insensitively, so ' 241337037 ' is the same student."""
    student = Student(student_id="  241337037 ", name="Someone")
    assert student.student_id == "241337037"


def test_normalise_student_id_trims_and_uppercases():
    assert normalise_student_id(" cse-402 ") == "CSE-402"


def test_whitespace_inside_a_name_is_collapsed():
    student = Student(student_id="1", name="  Md.   Ragib   Shahriyer  Soron ")
    assert student.name == "Md. Ragib Shahriyer Soron"


def test_an_empty_id_is_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        Student(student_id="   ", name="Someone")


def test_an_empty_name_is_rejected():
    with pytest.raises(ValueError, match="name must not be empty"):
        Student(student_id="241337037", name="   ")


def test_an_id_with_illegal_characters_is_rejected():
    with pytest.raises(ValueError, match="student ID must be"):
        Student(student_id="24/13/37", name="Someone")


def test_a_semester_below_one_is_rejected():
    with pytest.raises(ValueError, match="semester must be 1 or greater"):
        Student(student_id="1", name="Someone", semester=0)


def test_a_non_integer_semester_is_rejected():
    with pytest.raises(ValueError, match="semester must be an integer"):
        Student(student_id="1", name="Someone", semester="five")


def test_the_department_falls_back_to_undeclared():
    student = Student(student_id="1", name="Someone", department="  ")
    assert student.department == "Undeclared"


def test_initials_are_derived_from_the_name():
    student = Student(student_id="1", name="Md. Ragib Shahriyer Soron")
    assert student.initials == "MRSS"


def test_the_default_enrolment_date_is_today():
    student = Student(student_id="1", name="Someone")
    assert student.enrolled_on == date.today()


def test_the_student_is_immutable():
    """Students are values; changing one silently would corrupt a transcript."""
    student = Student(student_id="1", name="Someone")
    with pytest.raises(dataclasses.FrozenInstanceError):
        student.name = "Someone Else"  # type: ignore[misc]

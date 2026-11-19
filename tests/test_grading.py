"""Tests for the grading scale - requirement 4 (letter grade and grade point)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gradevault.domain.errors import InvalidMarkError
from gradevault.domain.grading import DEFAULT_SCALE, GradeScale, normalise_mark

#: Every row of the table in the brief: (mark, letter, point).
SCALE_TABLE = [
    (100, "A+", "4.00"),
    (95, "A+", "4.00"),
    (80, "A+", "4.00"),
    (79, "A", "3.75"),
    (75, "A", "3.75"),
    (74, "A-", "3.50"),
    (70, "A-", "3.50"),
    (69, "B+", "3.25"),
    (65, "B+", "3.25"),
    (64, "B", "3.00"),
    (60, "B", "3.00"),
    (59, "B-", "2.75"),
    (55, "B-", "2.75"),
    (54, "C+", "2.50"),
    (50, "C+", "2.50"),
    (49, "C", "2.25"),
    (45, "C", "2.25"),
    (44, "D", "2.00"),
    (40, "D", "2.00"),
    (39, "F", "0.00"),
    (20, "F", "0.00"),
    (0, "F", "0.00"),
]


@pytest.mark.parametrize(("mark", "letter", "point"), SCALE_TABLE)
def test_mark_maps_to_the_expected_grade_and_point(mark, letter, point):
    """Every mark in the brief's table produces the right letter and point."""
    assert DEFAULT_SCALE.letter_for(mark) == letter
    assert DEFAULT_SCALE.point_for(mark) == Decimal(point)


@pytest.mark.parametrize(("mark", "letter", "point"), SCALE_TABLE)
def test_classify_returns_letter_and_point_together(mark, letter, point):
    """``classify`` is the two-in-one lookup used by the result sheet."""
    assert DEFAULT_SCALE.classify(mark) == (letter, Decimal(point))


@pytest.mark.parametrize(
    ("lower", "upper"),
    [(80, 100), (75, 79), (70, 74), (65, 69), (60, 64), (55, 59), (50, 54), (45, 49), (40, 44), (0, 39)],
)
def test_every_mark_in_a_band_gets_that_band(lower, upper):
    """Both ends of every band are inclusive, as the brief requires."""
    for mark in (lower, upper):
        assert DEFAULT_SCALE.band_for(mark).lower == lower
        assert DEFAULT_SCALE.band_for(mark).upper == upper


def test_the_scale_has_exactly_ten_bands():
    """The brief's table has ten rows."""
    assert len(DEFAULT_SCALE.bands) == 10


def test_bands_are_ordered_from_highest_to_lowest():
    """Bands are stored high-to-low so the lookup can stop at the first hit."""
    lowers = [band.lower for band in DEFAULT_SCALE.bands]
    assert lowers == sorted(lowers, reverse=True)


def test_a_scale_with_a_gap_is_rejected():
    """A scale that leaves a hole in the 0-100 range is a bug, not a feature."""
    with pytest.raises(ValueError, match="gap"):
        GradeScale.from_rows([(80, 100, "A+", "4.00"), (0, 60, "F", "0.00")])


def test_a_scale_with_overlapping_bands_is_rejected():
    """Two bands covering the same mark would make the grade ambiguous."""
    with pytest.raises(ValueError, match="overlap"):
        GradeScale.from_rows([(80, 100, "A+", "4.00"), (70, 90, "A", "3.75")])


def test_an_empty_scale_is_rejected():
    """A scale with no bands could never grade anything."""
    with pytest.raises(ValueError, match="at least one band"):
        GradeScale(bands=())


def test_a_custom_scale_can_replace_the_default():
    """The scale is data, so a department can plug in its own table."""
    custom = GradeScale.from_rows([(50, 100, "P", "1.00"), (0, 49, "N", "0.00")])
    assert custom.letter_for(80) == "P"
    assert custom.letter_for(20) == "N"
    assert custom.point_for(80) == Decimal("1.00")


def test_as_table_returns_printable_rows():
    """``as_table`` feeds the ``scale`` CLI command."""
    rows = DEFAULT_SCALE.as_table()
    assert rows[0] == ("80-100", "A+", "4.00")
    assert rows[-1] == ("0-39", "F", "0.00")


def test_band_str_is_readable():
    """The band knows how to describe itself."""
    band = DEFAULT_SCALE.band_for(85)
    assert "A+" in str(band)
    assert "80-100" in str(band)


# ----------------------------------------------------------------------
# mark validation - requirement 3
# ----------------------------------------------------------------------
@pytest.mark.parametrize("mark", [-1, -0.5, 100.5, 101, 1000, -100])
def test_marks_outside_zero_to_hundred_are_rejected(mark):
    """A mark below 0 or above 100 must never reach the grade table."""
    with pytest.raises(InvalidMarkError):
        DEFAULT_SCALE.letter_for(mark)


@pytest.mark.parametrize("mark", ["abc", "", None, [], {}, True, False, "8o"])
def test_non_numeric_marks_are_rejected(mark):
    """Garbage input is rejected rather than silently treated as zero."""
    with pytest.raises(InvalidMarkError):
        normalise_mark(mark)


@pytest.mark.parametrize("mark", [0, 0.0, "0", "0.0", Decimal("0"), 50, 100, "99.5", Decimal("77.25")])
def test_valid_marks_are_normalised_to_decimal(mark):
    """Every accepted form comes back as an exact Decimal."""
    value = normalise_mark(mark)
    assert isinstance(value, Decimal)
    assert Decimal("0") <= value <= Decimal("100")


def test_decimal_marks_keep_their_fraction():
    """A fractional mark is not rounded away."""
    assert normalise_mark("87.25") == Decimal("87.25")
    assert DEFAULT_SCALE.letter_for("87.25") == "A+"


def test_the_error_message_mentions_the_allowed_range():
    """The message tells the teacher what to do next."""
    with pytest.raises(InvalidMarkError, match="between 0 and 100"):
        normalise_mark(150)

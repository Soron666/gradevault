"""The grading scale: marks in, letter grades and grade points out.

The scale is *data*, not code.  :data:`DEFAULT_SCALE` is the table mandated by
CSE402, but :class:`GradeScale` can be built with any other table (for example a
department that uses a +/- scale with different points) simply by passing a
different sequence of :class:`GradeBand` objects.  Every consumer of this module
takes a :class:`GradeScale` as an argument instead of hard-coding the table.

Two design decisions worth calling out:

* **Grade points are :class:`~decimal.Decimal`, not ``float``.**  A CGPA of
  3.75 x 3 credits / 3 credits must not come out as ``3.7499999999999996``.
  Decimals keep weighted averages exact and reproducible.
* **Marks are normalised to :class:`~decimal.Decimal` on the way in.**  A mark
  of ``75`` and a mark of ``75.0`` are the same mark, and the grade boundary
  tests rely on that.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .errors import InvalidMarkError

__all__ = ["GradeBand", "GradeScale", "DEFAULT_SCALE", "normalise_mark"]

#: Marks are expressed on a 0-100 scale.
MAX_MARK = Decimal("100")
MIN_MARK = Decimal("0")


def normalise_mark(mark: object) -> Decimal:
    """Coerce *mark* into a validated :class:`Decimal` in the range 0-100.

    Accepts ``int``, ``float``, ``Decimal`` and numeric strings such as
    ``"78.5"``.  Rejects anything else, and anything outside 0-100, with
    :class:`~gradevault.domain.errors.InvalidMarkError`.

    >>> normalise_mark(75)
    Decimal('75')
    >>> normalise_mark(101)
    Traceback (most recent call last):
        ...
    gradevault.domain.errors.InvalidMarkError: mark must be between 0 and 100, got 101
    """
    if isinstance(mark, bool):  # bool is an int subclass - reject it explicitly
        raise InvalidMarkError(f"mark must be a number between 0 and 100, got {mark!r}")

    if isinstance(mark, Decimal):
        value = mark
    elif isinstance(mark, (int, float)):
        try:
            value = Decimal(str(mark))
        except InvalidOperation:  # pragma: no cover - str() of a float is safe
            raise InvalidMarkError(f"mark must be a number between 0 and 100, got {mark!r}") from None
    elif isinstance(mark, str):
        try:
            value = Decimal(mark.strip())
        except (InvalidOperation, ValueError):
            raise InvalidMarkError(f"mark must be a number between 0 and 100, got {mark!r}") from None
    else:
        raise InvalidMarkError(f"mark must be a number between 0 and 100, got {mark!r}")

    if not value.is_finite():
        raise InvalidMarkError(f"mark must be a finite number between 0 and 100, got {mark!r}")
    if value < MIN_MARK or value > MAX_MARK:
        raise InvalidMarkError(f"mark must be between 0 and 100, got {mark}")
    return value


@dataclass(frozen=True, slots=True)
class GradeBand:
    """One row of the grading table.

    Attributes:
        letter: The letter grade handed to the student (``"A+"``).
        point: The grade point carried by the band (``4.00``).
        lower: Lowest mark in the band, inclusive.
        upper: Highest mark in the band, inclusive.
    """

    letter: str
    point: Decimal
    lower: int
    upper: int

    def contains(self, mark: Decimal) -> bool:
        """Return ``True`` when *mark* falls inside this band."""
        return Decimal(self.lower) <= mark <= Decimal(self.upper)

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError(f"band {self.letter} has lower bound above upper bound")
        if self.point < 0:
            raise ValueError(f"band {self.letter} has a negative grade point")

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.letter} ({self.point}) for {self.lower}-{self.upper}"


@dataclass(frozen=True, slots=True)
class GradeScale:
    """An ordered collection of :class:`GradeBand` rows.

    The scale is immutable and validated at construction time: the bands must
    tile the 0-100 range without gaps and without overlaps, so a mark can never
    fall between two rows.
    """

    bands: tuple[GradeBand, ...]

    def __post_init__(self) -> None:
        if not self.bands:
            raise ValueError("a grade scale needs at least one band")

        ordered = tuple(sorted(self.bands, key=lambda band: band.lower, reverse=True))
        # `ceiling` is the highest mark that is still allowed to be unassigned.
        ceiling = MAX_MARK
        for band in ordered:
            upper = Decimal(band.upper)
            lower = Decimal(band.lower)
            if upper > MAX_MARK or lower < MIN_MARK:
                raise ValueError(
                    f"band {band.letter} ({band.lower}-{band.upper}) leaves the 0-100 range"
                )
            if upper > ceiling:
                raise ValueError(
                    f"band {band.letter} overlaps the band above it at mark {band.upper}"
                )
            if upper < ceiling:
                raise ValueError(
                    f"gap in grade scale between mark {band.upper + 1} and mark {ceiling}"
                )
            ceiling = lower - 1
        if ceiling >= MIN_MARK:
            raise ValueError(
                f"grade scale does not cover marks 0 to {ceiling}"
            )

        object.__setattr__(self, "bands", ordered)

    # ------------------------------------------------------------------
    # lookups
    # ------------------------------------------------------------------
    def band_for(self, mark: object) -> GradeBand:
        """Return the :class:`GradeBand` that *mark* falls into."""
        value = normalise_mark(mark)
        for band in self.bands:
            if band.contains(value):
                return band
        raise InvalidMarkError(f"no grade band matches mark {value}")  # pragma: no cover

    def letter_for(self, mark: object) -> str:
        """Return the letter grade for *mark* (``"A+"``, ``"B-"`` ...)."""
        return self.band_for(mark).letter

    def point_for(self, mark: object) -> Decimal:
        """Return the grade point for *mark* (``4.00``, ``3.75`` ...)."""
        return self.band_for(mark).point

    def classify(self, mark: object) -> tuple[str, Decimal]:
        """Return ``(letter, point)`` for *mark* in one lookup."""
        band = self.band_for(mark)
        return band.letter, band.point

    def as_table(self) -> tuple[tuple[str, str, str], ...]:
        """Return the scale as printable rows: ``(range, letter, point)``."""
        rows = []
        for band in self.bands:
            span = f"{band.lower}-{band.upper}" if band.lower != band.upper else str(band.lower)
            rows.append((span, band.letter, f"{band.point:.2f}"))
        return tuple(rows)

    @classmethod
    def from_rows(cls, rows: Iterable[tuple[int, int, str, str]]) -> GradeScale:
        """Build a scale from ``(lower, upper, letter, point)`` tuples."""
        bands = tuple(
            GradeBand(letter=letter, point=Decimal(point), lower=lower, upper=upper)
            for lower, upper, letter, point in rows
        )
        return cls(bands=bands)


def _default_bands() -> Sequence[GradeBand]:
    """The grading table mandated by the CSE402 brief."""
    return (
        GradeBand(letter="A+", point=Decimal("4.00"), lower=80, upper=100),
        GradeBand(letter="A", point=Decimal("3.75"), lower=75, upper=79),
        GradeBand(letter="A-", point=Decimal("3.50"), lower=70, upper=74),
        GradeBand(letter="B+", point=Decimal("3.25"), lower=65, upper=69),
        GradeBand(letter="B", point=Decimal("3.00"), lower=60, upper=64),
        GradeBand(letter="B-", point=Decimal("2.75"), lower=55, upper=59),
        GradeBand(letter="C+", point=Decimal("2.50"), lower=50, upper=54),
        GradeBand(letter="C", point=Decimal("2.25"), lower=45, upper=49),
        GradeBand(letter="D", point=Decimal("2.00"), lower=40, upper=44),
        GradeBand(letter="F", point=Decimal("0.00"), lower=0, upper=39),
    )


#: The default scale used by the application unless another one is injected.
DEFAULT_SCALE = GradeScale(bands=tuple(_default_bands()))

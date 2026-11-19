"""A tiny, dependency-free table renderer.

Used by the result sheet (which is a table) and by the CLI listings.  It is
kept in its own module so that the application layer can render a result sheet
without importing anything from the CLI package.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

__all__ = ["render_table", "render_key_values"]

_BOX = {
    "corner": "+",
    "hline": "-",
    "vline": "|",
    "tee_left": "+",
    "tee_right": "+",
}


def _widths(
    headers: Sequence[str], rows: Sequence[Sequence[object]]
) -> list[int]:
    widths = [len(str(header)) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            if index < len(widths):
                widths[index] = max(widths[index], len(str(cell)))
    return widths


def render_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[object]],
    aligns: Sequence[str] | None = None,
) -> str:
    """Render *rows* under *headers* as a box-drawn table.

    Args:
        headers: Column titles.
        rows: The data rows.
        aligns: Optional per-column alignment, ``"left"`` (default) or ``"right"``.

    Returns:
        The rendered table, as a multi-line string.
    """
    materialised = [[("" if cell is None else str(cell)) for cell in row] for row in rows]
    widths = _widths(headers, materialised)
    if aligns is None:
        aligns = ["left"] * len(widths)

    def line(left: str, mid: str, right: str) -> str:
        return left + mid.join(_BOX["hline"] * (width + 2) for width in widths) + right

    def body(cells: Sequence[str]) -> str:
        parts = []
        for index, cell in enumerate(cells):
            width = widths[index]
            if index < len(aligns) and aligns[index] == "right":
                parts.append(f" {cell.rjust(width)} ")
            else:
                parts.append(f" {cell.ljust(width)} ")
        return _BOX["vline"] + _BOX["vline"].join(parts) + _BOX["vline"]

    out = [line(_BOX["corner"], _BOX["hline"], _BOX["corner"])]
    out.append(body(list(headers)))
    out.append(line(_BOX["tee_left"], _BOX["hline"], _BOX["tee_right"]))
    for row in materialised:
        out.append(body(row))
    out.append(line(_BOX["corner"], _BOX["hline"], _BOX["corner"]))
    return "\n".join(out)


def render_key_values(pairs: Sequence[tuple[str, object]], indent: str = "  ") -> str:
    """Render ``label: value`` pairs with the values aligned in one column."""
    if not pairs:
        return ""
    width = max(len(str(label)) for label, _ in pairs)
    return "\n".join(
        f"{indent}{str(label).ljust(width)} : {value}" for label, value in pairs
    )

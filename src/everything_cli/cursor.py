"""Cursor — forward-only iterator over Everything search results."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .row import Row


class Cursor:
    """Forward-only iterator over Everything search results.

    Wraps the lazy IPC result stream in DB-API 2.0-style fetch methods.
    Metadata (``total``, ``count``) is available immediately before iteration.

    This is a **one-pass** cursor — once results are consumed via iteration
    or fetch methods, they cannot be re-read.  Use :meth:`fetchall` to
    materialise all results into a list for random access.
    """

    __slots__ = ("_iter", "_total", "_count", "_exhausted")

    def __init__(
        self,
        result_iter: Iterator[dict[str, Any]],
        total: int,
        count: int,
    ) -> None:
        self._iter = result_iter
        self._total = total
        self._count = count
        self._exhausted = False

    # -- Metadata (available before iteration) -----------------------------

    @property
    def total(self) -> int:
        """Total number of matches in the Everything database."""
        return self._total

    @property
    def count(self) -> int:
        """Number of results in this cursor (respects limit/offset)."""
        return self._count

    # -- Iterator protocol -------------------------------------------------

    def __iter__(self) -> Iterator[Row]:
        if self._exhausted:
            return
        for raw in self._iter:
            yield Row(raw)
        self._exhausted = True

    def __len__(self) -> int:
        return self._count

    # -- DB-API 2.0 fetch methods ------------------------------------------

    def fetchone(self) -> Row | None:
        """Return the next result as a :class:`Row`, or ``None`` if exhausted."""
        if self._exhausted:
            return None
        raw = next(self._iter, None)
        if raw is None:
            self._exhausted = True
            return None
        return Row(raw)

    def fetchmany(self, size: int) -> list[Row]:
        """Return up to *size* results as a list of :class:`Row`.

        Returns an empty list when the cursor is exhausted.
        """
        if self._exhausted:
            return []
        rows: list[Row] = []
        for _ in range(size):
            raw = next(self._iter, None)
            if raw is None:
                self._exhausted = True
                break
            rows.append(Row(raw))
        return rows

    def fetchall(self) -> list[Row]:
        """Materialise all remaining results into a list of :class:`Row`."""
        if self._exhausted:
            return []
        rows = [Row(raw) for raw in self._iter]
        self._exhausted = True
        return rows

    def __repr__(self) -> str:
        state = "exhausted" if self._exhausted else "open"
        return f"Cursor(count={self._count}, total={self._total}, {state})"

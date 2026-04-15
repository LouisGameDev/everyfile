"""Tests for Cursor — forward-only iterator with DB-API 2.0 fetch methods."""

from __future__ import annotations

from typing import Any

from everything_cli.cursor import Cursor
from everything_cli.row import Row


# -- Helpers ---------------------------------------------------------------

def _make_raw_rows(n: int) -> list[dict[str, Any]]:
    """Create N raw result dicts for testing."""
    return [
        {"name": f"file{i}.txt", "path": "C:\\Data", "full_path": f"C:\\Data\\file{i}.txt"}
        for i in range(n)
    ]


def _make_cursor(n: int, total: int | None = None) -> Cursor:
    """Create a Cursor wrapping N raw rows."""
    rows = _make_raw_rows(n)
    return Cursor(iter(rows), total=total if total is not None else n, count=n)


# -- Metadata --------------------------------------------------------------

class TestCursorMetadata:
    def test_total(self) -> None:
        cur = _make_cursor(5, total=100)
        assert cur.total == 100

    def test_count(self) -> None:
        cur = _make_cursor(5, total=100)
        assert cur.count == 5

    def test_len(self) -> None:
        cur = _make_cursor(5)
        assert len(cur) == 5

    def test_repr_open(self) -> None:
        cur = _make_cursor(3, total=10)
        r = repr(cur)
        assert "count=3" in r
        assert "total=10" in r
        assert "open" in r

    def test_repr_exhausted(self) -> None:
        cur = _make_cursor(0)
        list(cur)  # exhaust
        r = repr(cur)
        assert "exhausted" in r


# -- Iteration -------------------------------------------------------------

class TestCursorIteration:
    def test_iter_yields_rows(self) -> None:
        cur = _make_cursor(3)
        rows = list(cur)
        assert len(rows) == 3
        assert all(isinstance(r, Row) for r in rows)

    def test_iter_row_data(self) -> None:
        cur = _make_cursor(2)
        rows = list(cur)
        assert rows[0].name == "file0.txt"
        assert rows[1].name == "file1.txt"
        assert rows[0].full_path == "C:\\Data\\file0.txt"

    def test_iter_exhausted_returns_empty(self) -> None:
        cur = _make_cursor(2)
        list(cur)  # consume all
        assert list(cur) == []

    def test_empty_cursor(self) -> None:
        cur = _make_cursor(0)
        assert list(cur) == []


# -- fetchone --------------------------------------------------------------

class TestFetchone:
    def test_returns_row(self) -> None:
        cur = _make_cursor(3)
        row = cur.fetchone()
        assert row is not None
        assert isinstance(row, Row)
        assert row.name == "file0.txt"

    def test_sequential_calls(self) -> None:
        cur = _make_cursor(3)
        r0 = cur.fetchone()
        r1 = cur.fetchone()
        r2 = cur.fetchone()
        assert r0 is not None and r0.name == "file0.txt"
        assert r1 is not None and r1.name == "file1.txt"
        assert r2 is not None and r2.name == "file2.txt"

    def test_returns_none_when_exhausted(self) -> None:
        cur = _make_cursor(1)
        cur.fetchone()
        assert cur.fetchone() is None

    def test_returns_none_on_empty(self) -> None:
        cur = _make_cursor(0)
        assert cur.fetchone() is None

    def test_none_after_already_exhausted(self) -> None:
        cur = _make_cursor(1)
        cur.fetchone()
        cur.fetchone()  # marks exhausted
        assert cur.fetchone() is None  # still None


# -- fetchmany -------------------------------------------------------------

class TestFetchmany:
    def test_basic(self) -> None:
        cur = _make_cursor(5)
        batch = cur.fetchmany(3)
        assert len(batch) == 3
        assert batch[0].name == "file0.txt"
        assert batch[2].name == "file2.txt"

    def test_remaining_less_than_size(self) -> None:
        cur = _make_cursor(5)
        cur.fetchmany(3)
        batch = cur.fetchmany(5)
        assert len(batch) == 2  # only 2 remaining

    def test_returns_empty_when_exhausted(self) -> None:
        cur = _make_cursor(2)
        cur.fetchmany(2)
        assert cur.fetchmany(5) == []

    def test_returns_empty_on_empty_cursor(self) -> None:
        cur = _make_cursor(0)
        assert cur.fetchmany(10) == []

    def test_all_rows_are_row_instances(self) -> None:
        cur = _make_cursor(3)
        batch = cur.fetchmany(3)
        assert all(isinstance(r, Row) for r in batch)


# -- fetchall --------------------------------------------------------------

class TestFetchall:
    def test_returns_all(self) -> None:
        cur = _make_cursor(5)
        rows = cur.fetchall()
        assert len(rows) == 5
        assert rows[0].name == "file0.txt"
        assert rows[4].name == "file4.txt"

    def test_returns_remaining_after_partial_read(self) -> None:
        cur = _make_cursor(5)
        cur.fetchone()
        remaining = cur.fetchall()
        assert len(remaining) == 4
        assert remaining[0].name == "file1.txt"

    def test_returns_empty_when_exhausted(self) -> None:
        cur = _make_cursor(3)
        cur.fetchall()
        assert cur.fetchall() == []

    def test_returns_empty_on_empty_cursor(self) -> None:
        cur = _make_cursor(0)
        assert cur.fetchall() == []

    def test_all_rows_are_row_instances(self) -> None:
        cur = _make_cursor(3)
        rows = cur.fetchall()
        assert all(isinstance(r, Row) for r in rows)


# -- Mixed usage -----------------------------------------------------------

class TestCursorMixed:
    def test_fetchone_then_iter(self) -> None:
        cur = _make_cursor(4)
        first = cur.fetchone()
        rest = list(cur)
        assert first is not None and first.name == "file0.txt"
        assert len(rest) == 3
        assert rest[0].name == "file1.txt"

    def test_fetchmany_then_fetchall(self) -> None:
        cur = _make_cursor(5)
        batch = cur.fetchmany(2)
        rest = cur.fetchall()
        assert len(batch) == 2
        assert len(rest) == 3
        assert batch[0].name == "file0.txt"
        assert rest[0].name == "file2.txt"

    def test_fetchone_then_fetchmany_then_fetchall(self) -> None:
        cur = _make_cursor(10)
        r0 = cur.fetchone()
        batch = cur.fetchmany(4)
        rest = cur.fetchall()
        assert r0 is not None and r0.name == "file0.txt"
        assert len(batch) == 4
        assert len(rest) == 5

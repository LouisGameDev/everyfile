"""Tests for Row — typed accessor over raw result dicts."""

from __future__ import annotations

import pytest

from everything_cli.row import Row


# -- Fixtures --------------------------------------------------------------

FULL_ROW_DATA: dict[str, object] = {
    "name": "readme.md",
    "path": "C:\\Projects",
    "full_path": "C:\\Projects\\readme.md",
    "ext": ".md",
    "size": 1024,
    "date_modified": "2026-04-01T12:00:00Z",
    "date_created": "2026-03-15T09:30:00Z",
    "date_accessed": "2026-04-15T08:00:00Z",
    "date_run": "2026-04-10T14:00:00Z",
    "date_recently_changed": "2026-04-01T12:00:00Z",
    "attributes": "A",
    "run_count": 5,
    "is_file": True,
    "is_folder": False,
    "hl_name": "<b>readme</b>.md",
    "hl_path": "C:\\<b>Projects</b>",
    "hl_full_path": "C:\\<b>Projects</b>\\<b>readme</b>.md",
}

MINIMAL_ROW_DATA: dict[str, object] = {
    "name": "src",
    "path": "C:\\Projects",
    "full_path": "C:\\Projects\\src",
}


# -- Typed property accessors (default fields) ----------------------------

class TestRowDefaultProperties:
    def test_name(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        assert row.name == "src"

    def test_path(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        assert row.path == "C:\\Projects"

    def test_full_path(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        assert row.full_path == "C:\\Projects\\src"


# -- Optional property accessors -------------------------------------------

class TestRowOptionalProperties:
    def test_present_fields(self) -> None:
        row = Row(FULL_ROW_DATA)
        assert row.ext == ".md"
        assert row.size == 1024
        assert row.date_modified == "2026-04-01T12:00:00Z"
        assert row.date_created == "2026-03-15T09:30:00Z"
        assert row.date_accessed == "2026-04-15T08:00:00Z"
        assert row.date_run == "2026-04-10T14:00:00Z"
        assert row.date_recently_changed == "2026-04-01T12:00:00Z"
        assert row.attributes == "A"
        assert row.run_count == 5
        assert row.is_file is True
        assert row.is_folder is False
        assert row.hl_name == "<b>readme</b>.md"
        assert row.hl_path == "C:\\<b>Projects</b>"
        assert row.hl_full_path is not None

    def test_missing_fields_return_none(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        assert row.ext is None
        assert row.size is None
        assert row.date_modified is None
        assert row.date_created is None
        assert row.date_accessed is None
        assert row.date_run is None
        assert row.date_recently_changed is None
        assert row.attributes is None
        assert row.run_count is None
        assert row.is_file is None
        assert row.is_folder is None
        assert row.hl_name is None
        assert row.hl_path is None
        assert row.hl_full_path is None


# -- Dict-style access -----------------------------------------------------

class TestRowDictAccess:
    def test_getitem(self) -> None:
        row = Row(FULL_ROW_DATA)
        assert row["name"] == "readme.md"
        assert row["size"] == 1024

    def test_getitem_missing_raises(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        with pytest.raises(KeyError):
            _ = row["size"]

    def test_get_with_default(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        assert row.get("size", -1) == -1

    def test_get_without_default(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        assert row.get("size") is None

    def test_contains(self) -> None:
        row = Row(FULL_ROW_DATA)
        assert "name" in row
        assert "nonexistent" not in row

    def test_keys(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        assert set(row.keys()) == {"name", "path", "full_path"}

    def test_to_dict_returns_backing_data(self) -> None:
        data = dict(FULL_ROW_DATA)
        row = Row(data)
        d = row.to_dict()
        assert d is data
        assert d["name"] == "readme.md"


# -- Representation --------------------------------------------------------

class TestRowRepr:
    def test_repr(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        r = repr(row)
        assert r.startswith("Row(")
        assert "src" in r

    def test_str_returns_full_path(self) -> None:
        row = Row(FULL_ROW_DATA)
        assert str(row) == "C:\\Projects\\readme.md"

    def test_str_fallback_no_full_path(self) -> None:
        row = Row({"name": "x"})
        # Falls back to repr of data
        assert str(row) == repr({"name": "x"})


# -- Equality --------------------------------------------------------------

class TestRowEquality:
    def test_equal_rows(self) -> None:
        a = Row({"name": "x", "path": "y", "full_path": "y/x"})
        b = Row({"name": "x", "path": "y", "full_path": "y/x"})
        assert a == b

    def test_different_rows(self) -> None:
        a = Row({"name": "x", "path": "y", "full_path": "y/x"})
        b = Row({"name": "z", "path": "y", "full_path": "y/z"})
        assert a != b

    def test_not_equal_to_other_types(self) -> None:
        row = Row(MINIMAL_ROW_DATA)
        assert row != "not a row"
        assert row != 42

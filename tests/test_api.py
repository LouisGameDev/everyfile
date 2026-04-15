"""Tests for the public API — Everything class and module-level functions.

All IPC calls are mocked so tests run without Everything being installed.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from everything_cli import Everything, Cursor, Row, EverythingError, search, count
from everything_cli.api import _resolve_sort
from everything_cli.sdk.constants import SortType


# -- Helpers ---------------------------------------------------------------

def _fake_search_result(
    rows: list[dict[str, Any]], num: int | None = None, total: int | None = None
) -> tuple[Iterator[dict[str, Any]], int, int]:
    """Build a fake ipc_query return value."""
    n = num if num is not None else len(rows)
    t = total if total is not None else len(rows)
    return iter(rows), n, t


SAMPLE_ROWS = [
    {"name": "a.py", "path": "C:\\Src", "full_path": "C:\\Src\\a.py"},
    {"name": "b.py", "path": "C:\\Src", "full_path": "C:\\Src\\b.py"},
    {"name": "c.py", "path": "C:\\Src", "full_path": "C:\\Src\\c.py"},
]


def _mock_api() -> MagicMock:
    """Create a MagicMock standing in for EverythingAPI."""
    mock = MagicMock()
    mock.search.return_value = iter([])
    mock.get_total_results.return_value = 0
    mock.get_num_results.return_value = 0
    mock.instance_name = "default"
    return mock


# -- _resolve_sort ---------------------------------------------------------

class TestResolveSort:
    def test_ascending(self) -> None:
        assert _resolve_sort("name", descending=False) == SortType.NAME_ASCENDING

    def test_descending(self) -> None:
        assert _resolve_sort("name", descending=True) == SortType.NAME_DESCENDING

    def test_size(self) -> None:
        assert _resolve_sort("size", descending=False) == SortType.SIZE_ASCENDING
        assert _resolve_sort("size", descending=True) == SortType.SIZE_DESCENDING

    def test_modified(self) -> None:
        assert _resolve_sort("modified", descending=True) == SortType.DATE_MODIFIED_DESCENDING

    def test_all_valid_names(self) -> None:
        from everything_cli.sdk.constants import SORT_NAME_MAP
        for name in SORT_NAME_MAP:
            asc = _resolve_sort(name, descending=False)
            desc = _resolve_sort(name, descending=True)
            assert asc != desc

    def test_invalid_sort_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown sort field 'bogus'"):
            _resolve_sort("bogus", descending=False)

    def test_invalid_sort_lists_valid(self) -> None:
        with pytest.raises(ValueError, match="name"):
            _resolve_sort("nope", descending=False)


# -- Everything class ------------------------------------------------------

@patch("everything_cli.api.resolve_fields", return_value=["name", "path", "full_path"])
@patch("everything_cli.api._list_instances", return_value=[])
class TestEverythingClass:
    """Tests for Everything using mocked IPC layer.

    Each test patches EverythingAPI so the Everything class constructor
    receives a MagicMock instead of a real IPC client.
    """

    @patch("everything_cli.api.EverythingAPI")
    def test_search_returns_cursor(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.search.return_value = iter(SAMPLE_ROWS)
        mock_api.get_total_results.return_value = 3
        mock_api.get_num_results.return_value = 3
        MockAPI.return_value = mock_api

        ev = Everything()
        cursor = ev.search("*.py")
        assert isinstance(cursor, Cursor)
        assert cursor.total == 3
        assert cursor.count == 3

    @patch("everything_cli.api.EverythingAPI")
    def test_search_cursor_yields_rows(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.search.return_value = iter(SAMPLE_ROWS)
        mock_api.get_total_results.return_value = 3
        mock_api.get_num_results.return_value = 3
        MockAPI.return_value = mock_api

        ev = Everything()
        rows = list(ev.search("*.py"))
        assert len(rows) == 3
        assert all(isinstance(r, Row) for r in rows)
        assert rows[0].name == "a.py"
        assert rows[2].full_path == "C:\\Src\\c.py"

    @patch("everything_cli.api.EverythingAPI")
    def test_count_returns_int(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.search.return_value = iter([])
        mock_api.get_total_results.return_value = 42
        MockAPI.return_value = mock_api

        ev = Everything()
        result = ev.count("*.py")
        assert result == 42
        assert isinstance(result, int)

    @patch("everything_cli.api.EverythingAPI")
    def test_count_passes_flags(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.search.return_value = iter([])
        mock_api.get_total_results.return_value = 10
        MockAPI.return_value = mock_api

        ev = Everything()
        ev.count("test", match_case=True, regex=True)
        call_kwargs = mock_api.search.call_args[1]
        assert call_kwargs["match_case"] is True
        assert call_kwargs["regex"] is True
        assert call_kwargs["max_results"] == 0

    @patch("everything_cli.api.EverythingAPI")
    def test_search_with_limit_and_offset(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.search.return_value = iter(SAMPLE_ROWS[:2])
        mock_api.get_total_results.return_value = 100
        mock_api.get_num_results.return_value = 2
        MockAPI.return_value = mock_api

        ev = Everything()
        cursor = ev.search("*.py", limit=2, offset=10)
        assert cursor.count == 2
        assert cursor.total == 100

        call_kwargs = mock_api.search.call_args[1]
        assert call_kwargs["max_results"] == 2
        assert call_kwargs["offset"] == 10

    @patch("everything_cli.api.EverythingAPI")
    def test_search_sort_descending(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.search.return_value = iter([])
        MockAPI.return_value = mock_api

        ev = Everything()
        ev.search("test", sort="size", descending=True)
        call_kwargs = mock_api.search.call_args[1]
        assert call_kwargs["sort"] == SortType.SIZE_DESCENDING

    @patch("everything_cli.api.EverythingAPI")
    def test_search_invalid_sort_raises(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        MockAPI.return_value = _mock_api()

        ev = Everything()
        with pytest.raises(ValueError, match="Unknown sort field"):
            ev.search("test", sort="nonexistent")

    @patch("everything_cli.api.EverythingAPI")
    def test_version_property(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.get_version.return_value = {
            "major": 1, "minor": 5, "revision": 0, "build": 1000
        }
        MockAPI.return_value = mock_api

        ev = Everything()
        v = ev.version
        assert v["major"] == 1
        assert v["build"] == 1000

    @patch("everything_cli.api.EverythingAPI")
    def test_info_property(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.get_info.return_value = {"total_files": 500000}
        MockAPI.return_value = mock_api

        ev = Everything()
        assert ev.info["total_files"] == 500000

    @patch("everything_cli.api.EverythingAPI")
    def test_instance_name_property(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.instance_name = "1.5a"
        MockAPI.return_value = mock_api

        ev = Everything()
        assert ev.instance_name == "1.5a"

    @patch("everything_cli.api.EverythingAPI")
    def test_repr(self, MockAPI: MagicMock, _li: Any, _rf: Any) -> None:
        mock_api = _mock_api()
        mock_api.instance_name = "default"
        MockAPI.return_value = mock_api

        ev = Everything()
        r = repr(ev)
        assert "Everything(" in r
        assert "default" in r


# -- Module-level convenience functions ------------------------------------

class TestModuleFunctions:
    """Tests for search() and count() module-level wrappers."""

    @patch("everything_cli.api.Everything")
    def test_search_creates_instance_and_delegates(self, MockEv: MagicMock) -> None:
        mock_instance = MockEv.return_value
        mock_cursor = MagicMock(spec=Cursor)
        mock_instance.search.return_value = mock_cursor

        result = search("*.txt", sort="size", descending=True, limit=10)

        MockEv.assert_called_once_with(instance=None)
        mock_instance.search.assert_called_once_with(
            "*.txt",
            fields=None,
            sort="size",
            descending=True,
            limit=10,
            offset=0,
            match_case=False,
            match_path=False,
            match_whole_word=False,
            regex=False,
        )
        assert result is mock_cursor

    @patch("everything_cli.api.Everything")
    def test_search_passes_instance(self, MockEv: MagicMock) -> None:
        mock_instance = MockEv.return_value
        mock_instance.search.return_value = MagicMock(spec=Cursor)

        search("test", instance="1.5a")
        MockEv.assert_called_once_with(instance="1.5a")

    @patch("everything_cli.api.Everything")
    def test_count_creates_instance_and_delegates(self, MockEv: MagicMock) -> None:
        mock_instance = MockEv.return_value
        mock_instance.count.return_value = 99

        result = count("*.py")

        MockEv.assert_called_once_with(instance=None)
        mock_instance.count.assert_called_once_with(
            "*.py",
            match_case=False,
            match_path=False,
            match_whole_word=False,
            regex=False,
        )
        assert result == 99

    @patch("everything_cli.api.Everything")
    def test_count_passes_flags(self, MockEv: MagicMock) -> None:
        mock_instance = MockEv.return_value
        mock_instance.count.return_value = 5

        count("test", match_case=True, match_path=True, instance="custom")
        MockEv.assert_called_once_with(instance="custom")
        call_kwargs = mock_instance.count.call_args[1]
        assert call_kwargs["match_case"] is True
        assert call_kwargs["match_path"] is True


# -- Error handling --------------------------------------------------------

class TestErrorHandling:
    def test_everything_error_is_importable(self) -> None:
        assert issubclass(EverythingError, Exception)

    def test_everything_error_is_not_running_flag(self) -> None:
        err = EverythingError("Not running", is_not_running=True)
        assert err.is_not_running is True
        assert "Not running" in str(err)

    def test_everything_error_default_flag(self) -> None:
        err = EverythingError("Something failed")
        assert err.is_not_running is False


# -- Package exports -------------------------------------------------------

class TestExports:
    def test_all_public_symbols_importable(self) -> None:
        import everything_cli
        for name in ["search", "count", "Everything", "Cursor", "Row", "EverythingError"]:
            assert hasattr(everything_cli, name), f"{name} not exported"

    def test_all_matches_exports(self) -> None:
        import everything_cli
        assert set(everything_cli.__all__) == {
            "search", "count", "Everything", "Cursor", "Row", "EverythingError"
        }

"""Row — typed accessor over a raw Everything result dict."""

from __future__ import annotations

from collections.abc import KeysView
from typing import Any, cast


class Row:
    """Thin typed wrapper over a raw result dict.

    Provides typed property accessors for IDE autocomplete and type checking,
    while retaining full dict-style access to the underlying data.
    """

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # -- Default fields (always present) -----------------------------------

    @property
    def name(self) -> str:
        """File or folder name."""
        return cast(str, self._data["name"])

    @property
    def path(self) -> str:
        """Parent directory path."""
        return cast(str, self._data["path"])

    @property
    def full_path(self) -> str:
        """Full path including filename."""
        return cast(str, self._data["full_path"])

    # -- Optional fields (None when not requested) -------------------------

    @property
    def ext(self) -> str | None:
        """Extension with dot prefix (e.g. ``'.py'``)."""
        return self._data.get("ext")

    @property
    def size(self) -> int | None:
        """Size in bytes."""
        return self._data.get("size")

    @property
    def date_modified(self) -> str | None:
        """ISO 8601 UTC timestamp of last modification."""
        return self._data.get("date_modified")

    @property
    def date_created(self) -> str | None:
        """ISO 8601 UTC timestamp of creation."""
        return self._data.get("date_created")

    @property
    def date_accessed(self) -> str | None:
        """ISO 8601 UTC timestamp of last access."""
        return self._data.get("date_accessed")

    @property
    def date_run(self) -> str | None:
        """ISO 8601 UTC timestamp of last run via Everything."""
        return self._data.get("date_run")

    @property
    def date_recently_changed(self) -> str | None:
        """ISO 8601 UTC timestamp of recent change."""
        return self._data.get("date_recently_changed")

    @property
    def attributes(self) -> str | None:
        """Compact attribute string (e.g. ``'RHA'``)."""
        return self._data.get("attributes")

    @property
    def run_count(self) -> int | None:
        """Number of times opened via Everything."""
        return self._data.get("run_count")

    @property
    def is_file(self) -> bool | None:
        """``True`` if this result is a file."""
        return self._data.get("is_file")

    @property
    def is_folder(self) -> bool | None:
        """``True`` if this result is a folder."""
        return self._data.get("is_folder")

    @property
    def hl_name(self) -> str | None:
        """Highlighted filename."""
        return self._data.get("hl_name")

    @property
    def hl_path(self) -> str | None:
        """Highlighted path."""
        return self._data.get("hl_path")

    @property
    def hl_full_path(self) -> str | None:
        """Highlighted full path."""
        return self._data.get("hl_full_path")

    # -- Dict-style access -------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a field value by key, with an optional default."""
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def keys(self) -> KeysView[str]:
        """Return the field names present in this row."""
        return self._data.keys()

    def to_dict(self) -> dict[str, Any]:
        """Return the underlying raw result dict."""
        return self._data

    # -- Representation ----------------------------------------------------

    def __repr__(self) -> str:
        return f"Row({self._data!r})"

    def __str__(self) -> str:
        return cast(str, self._data.get("full_path", repr(self._data)))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Row):
            return self._data == other._data
        return NotImplemented

"""Public Python API for Everything file search.

Provides :func:`search`, :func:`count`, and the :class:`Everything` class
for querying Voidtools Everything from Python without the CLI.
"""

from __future__ import annotations

from typing import Any

from .cursor import Cursor
from .row import Row
from .sdk.api import EverythingAPI, EverythingError
from .sdk.constants import SORT_NAME_MAP, SortType
from .sdk.ipc import list_instances as _list_instances
from .sdk.types import resolve_fields

# Re-exported from submodules for public API
__all__ = [
    "search",
    "count",
    "Everything",
    "Cursor",
    "Row",
    "EverythingError",
]


def _resolve_sort(sort_name: str, descending: bool) -> SortType:
    """Map a human sort name + direction to a SortType constant."""
    if sort_name not in SORT_NAME_MAP:
        valid = ", ".join(sorted(SORT_NAME_MAP.keys()))
        raise ValueError(
            f"Unknown sort field '{sort_name}'. Valid: {valid}"
        )
    asc, desc = SORT_NAME_MAP[sort_name]
    return desc if descending else asc


class Everything:
    """High-level Everything client with instance affinity.

    Create an instance once and issue multiple queries against the same
    Everything service.

    Parameters
    ----------
    instance:
        Everything instance name (e.g. ``"1.5a"``).
        ``None`` = auto-detect via env var or running instance.

    Raises
    ------
    EverythingError
        If Everything is not running.
    """

    __slots__ = ("_api",)

    def __init__(self, instance: str | None = None) -> None:
        self._api = EverythingAPI(instance=instance)

    # -- Query methods -----------------------------------------------------

    def search(
        self,
        query: str,
        *,
        fields: str | None = None,
        sort: str = "name",
        descending: bool = False,
        limit: int | None = None,
        offset: int = 0,
        match_case: bool = False,
        match_path: bool = False,
        match_whole_word: bool = False,
        regex: bool = False,
    ) -> Cursor:
        """Execute a search and return a :class:`Cursor`.

        Parameters
        ----------
        query:
            Everything search expression (e.g. ``"*.py"``, ``"ext:rs size:>1mb"``).
        fields:
            Comma-separated field names or group alias. ``None`` = default fields.
        sort:
            Sort field name (``"name"``, ``"size"``, ``"modified"``, etc.).
        descending:
            Reverse sort order.
        limit:
            Max results to return. ``None`` = Everything's configured default.
        offset:
            Skip first N results (pagination).
        match_case:
            Case-sensitive search.
        match_path:
            Match query against full path.
        match_whole_word:
            Match whole words only.
        regex:
            Interpret query as regex.

        Returns
        -------
        Cursor
            Forward-only iterator of :class:`Row` results.

        Raises
        ------
        EverythingError
            If IPC communication fails.
        ValueError
            If *fields* or *sort* contains unknown names.
        """
        resolved_fields = resolve_fields(fields)
        sort_type = _resolve_sort(sort, descending)

        result_iter = self._api.search(
            query,
            fields=resolved_fields,
            sort=sort_type,
            max_results=limit,
            offset=offset,
            match_case=match_case,
            match_path=match_path,
            match_whole_word=match_whole_word,
            regex=regex,
        )
        # The underlying API populates totals after the iterator is created
        # but before any results are yielded (from the IPC response header).
        # We need to consume the iterator wrapper to get those stats.
        # EverythingAPI stores them after ipc_query returns.
        return Cursor(
            result_iter,
            total=self._api.get_total_results(),
            count=self._api.get_num_results(),
        )

    def count(
        self,
        query: str,
        *,
        match_case: bool = False,
        match_path: bool = False,
        match_whole_word: bool = False,
        regex: bool = False,
    ) -> int:
        """Return the total number of matches without fetching results.

        Parameters
        ----------
        query:
            Everything search expression.

        Returns
        -------
        int
            Total number of matching files/folders.

        Raises
        ------
        EverythingError
            If IPC communication fails.
        """
        # Minimal fields, limit to 0 results — we only want the total.
        self._api.search(
            query,
            fields=["name"],
            max_results=0,
            match_case=match_case,
            match_path=match_path,
            match_whole_word=match_whole_word,
            regex=regex,
        )
        return self._api.get_total_results()

    # -- Introspection -----------------------------------------------------

    @property
    def version(self) -> dict[str, Any]:
        """Everything version info dict.

        Keys: ``major``, ``minor``, ``revision``, ``build``, ``version``, ``instance``.
        """
        return self._api.get_version()

    @property
    def info(self) -> dict[str, Any]:
        """Everything service info (indexed file/folder counts, etc.)."""
        return self._api.get_info()

    @property
    def instance_name(self) -> str:
        """Resolved instance name (e.g. ``"1.5a"``, ``"default"``)."""
        return self._api.instance_name

    @staticmethod
    def instances() -> list[dict[str, Any]]:
        """List all running Everything instances.

        Returns a list of dicts with ``"name"`` and ``"hwnd"`` keys.
        """
        return _list_instances()

    def __repr__(self) -> str:
        return f"Everything(instance={self.instance_name!r})"


# -- Module-level convenience functions ------------------------------------


def search(
    query: str,
    *,
    fields: str | None = None,
    sort: str = "name",
    descending: bool = False,
    limit: int | None = None,
    offset: int = 0,
    match_case: bool = False,
    match_path: bool = False,
    match_whole_word: bool = False,
    regex: bool = False,
    instance: str | None = None,
) -> Cursor:
    """Execute an Everything search and return a :class:`Cursor`.

    Convenience wrapper that creates a temporary :class:`Everything` client.
    For repeated queries, create an :class:`Everything` instance directly.

    See :meth:`Everything.search` for full parameter documentation.
    """
    ev = Everything(instance=instance)
    return ev.search(
        query,
        fields=fields,
        sort=sort,
        descending=descending,
        limit=limit,
        offset=offset,
        match_case=match_case,
        match_path=match_path,
        match_whole_word=match_whole_word,
        regex=regex,
    )


def count(
    query: str,
    *,
    match_case: bool = False,
    match_path: bool = False,
    match_whole_word: bool = False,
    regex: bool = False,
    instance: str | None = None,
) -> int:
    """Return the total number of Everything matches for a query.

    Convenience wrapper that creates a temporary :class:`Everything` client.
    See :meth:`Everything.count` for full parameter documentation.
    """
    ev = Everything(instance=instance)
    return ev.count(
        query,
        match_case=match_case,
        match_path=match_path,
        match_whole_word=match_whole_word,
        regex=regex,
    )

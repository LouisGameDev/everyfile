"""High-level Pythonic wrapper around Everything IPC.

Uses pure-Python WM_COPYDATA IPC (ipc.py) — no DLL required.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

from .constants import SortType
from .ipc import (
    EverythingNotRunning,
    IPCError,
    detect_instance,
    ipc_get_info,
    ipc_get_version,
    ipc_query,
    list_instances,
)
from .types import compute_request_flags

# Environment variable for persisting instance selection
INSTANCE_ENV_VAR = "EVERYTHING_INSTANCE"


class EverythingError(Exception):
    """Raised when an Everything IPC call fails."""

    def __init__(self, message: str, *, is_not_running: bool = False) -> None:
        super().__init__(message)
        self.is_not_running = is_not_running


def resolve_instance(explicit: str | None = None) -> str | None:
    """Determine which instance to use.

    Priority: explicit argument > EVERYTHING_INSTANCE env var > auto-detect.
    Returns the instance name or None for default.
    """
    # 1. Explicit CLI --instance takes priority
    if explicit is not None:
        return explicit if explicit != "default" else None

    # 2. Check environment variable
    env_val = os.environ.get(INSTANCE_ENV_VAR)
    if env_val:
        return env_val if env_val != "default" else None

    # 3. Auto-detect (may raise EverythingNotRunning)
    return detect_instance()


class EverythingAPI:
    """Pythonic wrapper around Everything IPC."""

    _instance: str | None

    def __init__(self, instance: str | None = ...) -> None:  # type: ignore[assignment]
        # Auto-detect instance on construction
        if instance is ...:  # type: ignore[comparison-overlap]
            try:
                self._instance = resolve_instance()
            except EverythingNotRunning as exc:
                raise EverythingError(str(exc), is_not_running=True) from exc
        else:
            try:
                self._instance = resolve_instance(instance)
            except EverythingNotRunning as exc:
                raise EverythingError(str(exc), is_not_running=True) from exc
        self._last_num_results = 0
        self._last_total_results = 0

    @property
    def instance_name(self) -> str:
        """Return the resolved instance name for display."""
        return self._instance if self._instance else "default"

    def search(
        self,
        query: str,
        *,
        fields: list[str],
        sort: SortType = SortType.NAME_ASCENDING,
        max_results: int | None = None,
        offset: int = 0,
        match_case: bool = False,
        match_path: bool = False,
        match_whole_word: bool = False,
        regex: bool = False,
    ) -> Iterator[dict[str, Any]]:
        """Execute a search and yield result dicts."""
        request_flags = int(compute_request_flags(fields))

        try:
            results, num, total = ipc_query(
                query,
                fields=fields,
                request_flags=request_flags,
                sort=sort,
                max_results=max_results,
                offset=offset,
                match_case=match_case,
                match_path=match_path,
                match_whole_word=match_whole_word,
                regex=regex,
                instance=self._instance,
            )
        except EverythingNotRunning as exc:
            raise EverythingError(str(exc), is_not_running=True) from exc
        except IPCError as exc:
            raise EverythingError(str(exc)) from exc

        self._last_total_results = total
        self._last_num_results = num
        yield from results

    def get_num_results(self) -> int:
        """Get number of visible results (after last query)."""
        return self._last_num_results

    def get_total_results(self) -> int:
        """Get total number of results (after last query)."""
        return self._last_total_results

    def get_version(self) -> dict[str, Any]:
        """Get Everything version info."""
        try:
            return ipc_get_version(self._instance)
        except EverythingNotRunning as exc:
            raise EverythingError(str(exc), is_not_running=True) from exc
        except IPCError as exc:
            raise EverythingError(str(exc)) from exc

    def get_info(self) -> dict[str, Any]:
        """Get Everything service info."""
        try:
            return ipc_get_info(self._instance)
        except EverythingNotRunning as exc:
            raise EverythingError(str(exc), is_not_running=True) from exc
        except IPCError as exc:
            raise EverythingError(str(exc)) from exc

    def cleanup(self) -> None:
        """No-op — IPC is stateless, nothing to clean up."""
        pass

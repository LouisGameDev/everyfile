"""everyfile MCP server.

Exposes Voidtools Everything file search to AI assistants via the
Model Context Protocol (MCP).  Requires ``pip install everyfile[mcp]``.

Transport: stdio (default).  Launch with ``everyfile-mcp`` or
``python -m everyfile.mcp``.
"""
# pyright: reportMissingImports=false

from __future__ import annotations

import json
from collections import defaultdict
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from everyfile import Everything, EverythingError

mcp = FastMCP(
    "everything",
    instructions="Search files instantly on Windows via Voidtools Everything",
)

MAX_RESULTS_CAP = 10_000
DEFAULT_MAX_RESULTS = 200


@mcp.tool()
def search_files(
    query: Annotated[str, Field(description='Everything search expression. Supports wildcards (*.py), extensions (ext:rs|go), size filters (size:>1mb), date filters (dm:today, dm:thisweek), path filters (parent:C:\\Dev), boolean (foo bar = AND, foo|bar = OR, !foo = NOT), content search (content:"TODO"), and duplicates (dupe:).')],
    fields: Annotated[str | None, Field(description='Comma-separated field names to include in results. Options: name, path, full_path, ext, size, date_created, date_modified, date_accessed, attributes, is_file, is_folder, run_count. Groups: "all", "meta", "dates", "highlight". Default: name, path, full_path, date_modified.')] = None,
    sort: Annotated[str, Field(description='Sort field: name, path, size, ext, created, modified, accessed, run-count, date-run, recently-changed, attributes.')] = "name",
    descending: Annotated[bool, Field(description='Reverse sort order.')] = False,
    max_results: Annotated[int, Field(description='Maximum number of results to return (capped at 10,000).')] = DEFAULT_MAX_RESULTS,
    offset: Annotated[int, Field(description='Skip first N results for pagination.')] = 0,
    match_case: Annotated[bool, Field(description='Case-sensitive search.')] = False,
    match_path: Annotated[bool, Field(description='Match against full path, not just filename.')] = False,
    match_whole_word: Annotated[bool, Field(description='Match whole words only.')] = False,
    regex: Annotated[bool, Field(description='Interpret query as a regular expression.')] = False,
) -> str:
    """Search for files and folders instantly across all indexed drives using Voidtools Everything."""
    limit = min(max_results, MAX_RESULTS_CAP)
    try:
        ev = Everything()
        cursor = ev.search(
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
        rows = [row.to_dict() for row in cursor]
        result = {
            "results": rows,
            "count": cursor.count,
            "total": cursor.total,
        }
        return json.dumps(result, ensure_ascii=False)
    except EverythingError as exc:
        raise _mcp_error(exc) from exc


@mcp.tool()
def count_files(
    query: Annotated[str, Field(description='Everything search expression (same syntax as search_files).')],
    match_case: Annotated[bool, Field(description='Case-sensitive search.')] = False,
    match_path: Annotated[bool, Field(description='Match against full path, not just filename.')] = False,
    match_whole_word: Annotated[bool, Field(description='Match whole words only.')] = False,
    regex: Annotated[bool, Field(description='Interpret query as a regular expression.')] = False,
) -> str:
    """Count files/folders matching a query without returning results. Use to check result scale before fetching."""
    try:
        ev = Everything()
        total = ev.count(
            query,
            match_case=match_case,
            match_path=match_path,
            match_whole_word=match_whole_word,
            regex=regex,
        )
        return json.dumps({"query": query, "total": total})
    except EverythingError as exc:
        raise _mcp_error(exc) from exc


_VALID_GROUP_BY = {"ext", "folder", "root"}
_VALID_SORT_BY = {"count", "total_size", "avg_size", "min_size", "max_size"}


def _group_key(row: dict[str, object], group_by: str) -> str:
    """Extract the grouping key from a result row."""
    if group_by == "ext":
        return str(row.get("ext") or "").lower()
    if group_by == "folder":
        return str(row.get("path") or "")
    if group_by == "root":
        fp = str(row.get("full_path") or "")
        return fp[:2] if len(fp) >= 2 else fp
    return ""  # unreachable after validation


@mcp.tool()
def aggregate_files(
    query: Annotated[str, Field(description='Everything search expression (same syntax as search_files).')],
    group_by: Annotated[str | None, Field(description='Group results by: "ext" (file extension), "folder" (parent directory), "root" (drive letter). Null for flat totals only.')] = None,
    top_n: Annotated[int, Field(description='Max number of groups to return, sorted by sort_by. Default 20.')] = 20,
    sort_by: Annotated[str, Field(description='Sort groups by: "count", "total_size", "avg_size", "min_size", "max_size". Default "total_size".')] = "total_size",
    match_case: Annotated[bool, Field(description='Case-sensitive search.')] = False,
    match_path: Annotated[bool, Field(description='Match against full path, not just filename.')] = False,
    match_whole_word: Annotated[bool, Field(description='Match whole words only.')] = False,
    regex: Annotated[bool, Field(description='Interpret query as a regular expression.')] = False,
) -> str:
    """Aggregate file statistics server-side. Returns total count and size, optionally grouped.

    Streams all matching rows internally (no result cap) and computes
    aggregates in-process. Use for analytical questions like "how much space
    do my images use?" or "which extensions are biggest?".
    """
    if group_by is not None and group_by not in _VALID_GROUP_BY:
        valid = ", ".join(sorted(_VALID_GROUP_BY))
        raise _mcp_error(
            EverythingError(f"Unknown group_by '{group_by}'. Valid: {valid}")
        )
    if sort_by not in _VALID_SORT_BY:
        valid = ", ".join(sorted(_VALID_SORT_BY))
        raise _mcp_error(
            EverythingError(f"Unknown sort_by '{sort_by}'. Valid: {valid}")
        )

    # Only request fields we need for aggregation
    fields_needed = ["size"]
    if group_by == "ext":
        fields_needed.append("ext")
    elif group_by == "folder":
        fields_needed.append("path")
    elif group_by == "root":
        fields_needed.append("full_path")

    try:
        ev = Everything()
        cursor = ev.search(
            query,
            fields=",".join(fields_needed),
            limit=None,
            match_case=match_case,
            match_path=match_path,
            match_whole_word=match_whole_word,
            regex=regex,
        )

        total_count = 0
        total_size = 0
        groups: dict[str, dict[str, int]] = defaultdict(
            lambda: {"count": 0, "total_size": 0, "min_size": 2**63, "max_size": 0}
        )

        for row in cursor:
            size = row["size"] or 0
            total_count += 1
            total_size += size

            if group_by is not None:
                key = _group_key(row.to_dict(), group_by)
                g = groups[key]
                g["count"] += 1
                g["total_size"] += size
                if size < g["min_size"]:
                    g["min_size"] = size
                if size > g["max_size"]:
                    g["max_size"] = size

        result: dict[str, object] = {
            "query": query,
            "total_count": total_count,
            "total_size": total_size,
        }

        if group_by is not None:
            # Build final group dicts with all metrics so sort_by can target any of them
            final_groups = [
                {
                    "key": k,
                    "count": v["count"],
                    "total_size": v["total_size"],
                    "avg_size": v["total_size"] // v["count"] if v["count"] else 0,
                    "min_size": v["min_size"] if v["min_size"] != 2**63 else 0,
                    "max_size": v["max_size"],
                }
                for k, v in groups.items()
            ]
            _sort_by = sort_by  # capture for lambda
            final_groups.sort(
                key=lambda g: g[_sort_by],  # type: ignore[arg-type, return-value]
                reverse=True,
            )
            result["group_by"] = group_by
            result["groups_total"] = len(final_groups)
            result["groups"] = final_groups[:top_n]

        return json.dumps(result, ensure_ascii=False)
    except EverythingError as exc:
        raise _mcp_error(exc) from exc


@mcp.tool()
def get_everything_info() -> str:
    """Get Everything service status, version, and diagnostics.

    Returns version info, target architecture, database status,
    and privilege level.  Useful for checking if Everything is running
    and healthy.
    """
    try:
        ev = Everything()
        info = ev.info
        v = info["version"]
        inst = ev.instance_name

        result: dict[str, object] = {
            "version": v,
            "instance": inst,
        }
        if info.get("target") is not None:
            result["target"] = info["target"]
        if info.get("db_loaded") is not None:
            result["db_loaded"] = info["db_loaded"]
        result["is_admin"] = bool(info.get("is_admin"))
        result["is_appdata"] = bool(info.get("is_appdata"))

        return json.dumps(result)
    except EverythingError as exc:
        raise _mcp_error(exc) from exc


def _mcp_error(exc: EverythingError) -> Exception:
    """Convert an EverythingError to an MCP-friendly exception."""
    from mcp.server.fastmcp.exceptions import ToolError

    return ToolError(str(exc))


def main() -> None:
    """Entry point for ``everyfile-mcp`` command."""
    import sys

    if sys.stdin.isatty():
        print(
            "everyfile-mcp: MCP server for Everything file search\n"
            "\n"
            "This is a stdio MCP server — it expects JSON-RPC on stdin\n"
            "and is meant to be launched by an MCP client, not run directly.\n"
            "\n"
            "Add to your MCP client config:\n"
            "\n"
            '  { "mcpServers": { "everything": { "command": "everyfile-mcp" } } }\n'
            "\n"
            "Or test with:  echo '{...}' | everyfile-mcp",
            file=sys.stderr,
        )
        sys.exit(0)
    mcp.run()


if __name__ == "__main__":
    main()

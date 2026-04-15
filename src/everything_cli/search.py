"""Core search logic — default action, --count, --info, --version, --instances modes."""

from __future__ import annotations

import json
import os
import platform
import sys
from typing import Any

from .output import human, ndjson
from .querymatch import matches_query, parse_query
from .sdk.api import (
    INSTANCE_ENV_VAR,
    EverythingAPI,
    EverythingError,
    resolve_instance,
)
from .sdk.constants import SORT_NAME_MAP, SortType
from .sdk.ipc import list_instances
from .sdk.types import resolve_fields, FIELD_GROUPS, ALL_FIELD_NAMES

__version__ = "0.1.0"


def _parse_display_cols(field_spec: str) -> list[str]:
    """Expand a -f spec into display columns without injecting defaults.

    Duplicate column names are preserved (e.g. ``name,size,name``).
    Group aliases expand without internal duplicates but can repeat
    columns already present.
    """
    result: list[str] = []
    for token in (t.strip() for t in field_spec.split(",") if t.strip()):
        if token in FIELD_GROUPS:
            seen_in_group: set[str] = set()
            for f in FIELD_GROUPS[token]:
                if f not in seen_in_group:
                    seen_in_group.add(f)
                    result.append(f)
        elif token in ALL_FIELD_NAMES:
            result.append(token)
    return result or ["name", "path"]


def _instance_source(explicit: str | None) -> str | None:
    """Return a human-readable description of how the instance was selected."""
    if explicit is not None:
        return "--instance flag"
    env = os.environ.get(INSTANCE_ENV_VAR)
    if env:
        return f"${INSTANCE_ENV_VAR}={env}"
    return "auto-detect"


def _write_list_entry(record: dict[str, Any], sep: str) -> None:
    """Write full_path to stdout with the given separator."""
    path = record.get("full_path") or record.get("path", "")
    try:
        sys.stdout.write(path + sep)
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def _resolve_sort(sort_name: str | None, descending: bool) -> tuple[SortType, str | None]:
    """Resolve --sort/--desc flags to a SortType constant and display name.

    Default sort: date_modified descending.
    """
    if sort_name is None:
        return SortType.DATE_MODIFIED_DESCENDING, None
    if sort_name not in SORT_NAME_MAP:
        valid = ", ".join(sorted(SORT_NAME_MAP.keys()))
        human.error(f"unknown sort field '{sort_name}'. Valid: {valid}")
        sys.exit(1)
    asc, desc = SORT_NAME_MAP[sort_name]
    return (desc if descending else asc), sort_name


def run_search(
    query: str,
    *,
    fields_spec: str | None = None,
    columns: list[str] | None = None,
    sort_name: str | None = None,
    descending: bool = False,
    max_results: int | None = None,
    offset: int = 0,
    match_case: bool = False,
    match_path: bool = False,
    match_whole_word: bool = False,
    regex: bool = False,
    quiet: bool = False,
    emit_json: bool = True,
    list_sep: str | None = None,
    instance: str | None = None,
) -> int:
    """Execute search and stream results. Returns exit code.

    When list_sep is set (e.g. "\\n" or "\\0"), outputs full_path with that
    separator instead of NDJSON. emit_json and quiet are overridden.
    """
    try:
        fields = resolve_fields(fields_spec)
    except ValueError as exc:
        human.error(str(exc))
        return 1

    # Determine display columns; ensure they're in the requested fields.
    # If user explicitly set -f but not --columns, display only what they asked for.
    if columns:
        display_cols = columns
    elif fields_spec:
        display_cols = _parse_display_cols(fields_spec)
    else:
        display_cols = human.DEFAULT_COLUMNS
    # Add display columns to fields if not already present
    fields_set = set(fields)
    for col in display_cols:
        if col not in fields_set:
            fields.append(col)
            fields_set.add(col)

    sort_type, sort_display = _resolve_sort(sort_name, descending)

    try:
        api = EverythingAPI(instance=instance)
    except Exception as exc:
        human.error(str(exc))
        return 2

    printer = human.ResultPrinter(display_cols)

    if list_sep is not None:
        emit_json = False
        quiet = True

    try:
        results = api.search(
            query,
            fields=fields,
            sort=sort_type,
            max_results=max_results,
            offset=offset,
            match_case=match_case,
            match_path=match_path,
            match_whole_word=match_whole_word,
            regex=regex,
        )
        for record in results:
            if list_sep is not None:
                _write_list_entry(record, list_sep)
            elif emit_json:
                ndjson.write_record(record)
            if not quiet:
                printer.print_record(record)

        if not quiet:
            printer.print_appendix(
                api.get_num_results(),
                api.get_total_results(),
                query,
                sort_name=sort_display,
                descending=descending,
            )
    except EverythingError as exc:
        human.error(str(exc))
        return 2 if exc.is_not_running else 1
    finally:
        api.cleanup()

    return 0


def run_count(
    query: str,
    *,
    match_case: bool = False,
    match_path: bool = False,
    match_whole_word: bool = False,
    regex: bool = False,
    quiet: bool = False,
    emit_json: bool = True,
    instance: str | None = None,
) -> int:
    """Execute search and emit only the total count. Returns exit code."""
    try:
        api = EverythingAPI(instance=instance)
    except Exception as exc:
        human.error(str(exc))
        return 2

    try:
        # Minimal fields for fastest query
        fields = ["name", "path"]
        for _ in api.search(
            query,
            fields=fields,
            match_case=match_case,
            match_path=match_path,
            match_whole_word=match_whole_word,
            regex=regex,
        ):
            break  # consume generator to trigger query, don't need results

        total = api.get_total_results()
        if emit_json:
            ndjson.write_json({"total": total})
        if not quiet:
            human.info(f'{total:,} results for "{query}"')
    except EverythingError as exc:
        human.error(str(exc))
        return 2 if exc.is_not_running else 1
    finally:
        api.cleanup()

    return 0


def run_info(*, emit_json: bool = True, instance: str | None = None) -> int:
    """Print Everything service info. Returns exit code."""
    try:
        api = EverythingAPI(instance=instance)
    except Exception as exc:
        human.error(str(exc))
        return 2

    try:
        info = api.get_info()
        human.service_info(
            major=info["major"],
            minor=info["minor"],
            revision=info["revision"],
            build=info["build"],
            target=info["target"],
            db_loaded=info["db_loaded"],
            is_admin=info["is_admin"],
            is_appdata=info["is_appdata"],
            instance_name=api.instance_name,
        )
        if emit_json:
            ndjson.write_json(info)
    except EverythingError as exc:
        human.error(str(exc))
        return 2 if exc.is_not_running else 1
    finally:
        api.cleanup()

    return 0


def run_version(*, instance: str | None = None) -> int:
    """Print version info. Returns exit code."""
    python_ver = platform.python_version()
    ev_version: str | None = None
    inst_name: str | None = None
    inst_source = _instance_source(instance)

    try:
        api = EverythingAPI(instance=instance)
        inst_name = api.instance_name
        try:
            ver = api.get_version()
            ev_version = ver["version"]
        except EverythingError:
            pass
        finally:
            api.cleanup()
    except Exception:
        pass

    human.version_info(
        __version__, python_ver, ev_version,
        instance_name=inst_name,
        instance_source=inst_source,
    )
    return 0


def run_instances(*, instance: str | None = None, emit_json: bool = False) -> int:
    """List running Everything instances. Returns exit code."""
    instances = list_instances()
    source = _instance_source(instance)

    # Determine which instance would be active
    active_name: str | None = None
    try:
        resolved = resolve_instance(instance)
        active_name = resolved if resolved else "default"
    except Exception:
        pass

    if emit_json:
        for inst in instances:
            ndjson.write_json({
                "name": inst["name"],
                "class": inst["class"],
                "active": _is_active(inst["name"], active_name),
            })
    else:
        human.instance_list(instances, active_name, source, INSTANCE_ENV_VAR)

    return 0


def _is_active(name: str, active_name: str | None) -> bool:
    if active_name is None:
        return False
    return name == active_name


def run_pipe_filter(
    query: str,
    *,
    columns: list[str] | None = None,
    max_results: int | None = None,
    offset: int = 0,
    quiet: bool = False,
    emit_json: bool = True,
    list_sep: str | None = None,
) -> int:
    """Filter NDJSON records from stdin using Everything search syntax.

    Used when `ev` detects piped input + a query argument.
    Applies the query as a local filter against NDJSON fields.
    Returns exit code.
    """
    parsed = parse_query(query)
    if not parsed:
        human.error("empty query")
        return 1

    display_cols = columns if columns else human.DEFAULT_COLUMNS
    printer = human.ResultPrinter(display_cols)

    if list_sep is not None:
        emit_json = False
        quiet = True

    matched = 0
    total_read = 0
    skipped = 0

    try:
        for lineno, line in enumerate(sys.stdin, 1):
            line = line.rstrip("\n\r")
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                human.error(f"stdin line {lineno}: invalid JSON")
                return 4

            total_read += 1

            # Skip offset records
            if skipped < offset:
                if matches_query(record, parsed):
                    skipped += 1
                continue

            if matches_query(record, parsed):
                matched += 1
                if list_sep is not None:
                    _write_list_entry(record, list_sep)
                elif emit_json:
                    ndjson.write_record(record)
                if not quiet:
                    printer.print_record(record)
                if max_results is not None and matched >= max_results:
                    break
    except BrokenPipeError:
        pass

    if not quiet:
        printer.print_appendix(matched, total_read, query)

    return 0

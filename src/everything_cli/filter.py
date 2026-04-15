from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from .output.human import warning
from .output.ndjson import write_record
from .util.attrs import string_has_attrs
from .util.dates import parse_iso_date
from .util.glob import glob_match


@dataclass
class FilterConfig:
    """All filter options from CLI args."""

    name_glob: str | None = None
    path_glob: str | None = None
    ext: str | None = None
    size_gt: int | None = None
    size_lt: int | None = None
    modified_after: str | None = None
    modified_before: str | None = None
    created_after: str | None = None
    created_before: str | None = None
    is_file: bool = False
    is_folder: bool = False
    attr_chars: str | None = None


def _check_field(record: dict[str, Any], field: str, warned: set[str]) -> bool:
    """Return True if field is present, else warn once and return False."""
    if field in record:
        return True
    if field not in warned:
        warning(f"field '{field}' not present in input, skipping record")
        warned.add(field)
    return False


def _date_gt(record_val: str, threshold: str) -> bool:
    return parse_iso_date(record_val) > parse_iso_date(threshold)


def _date_lt(record_val: str, threshold: str) -> bool:
    return parse_iso_date(record_val) < parse_iso_date(threshold)


def _matches(record: dict[str, Any], config: FilterConfig, warned: set[str]) -> bool:
    """Return True if record passes ALL active filters."""
    if config.name_glob is not None:
        if not _check_field(record, "name", warned):
            return False
        if not glob_match(record["name"], config.name_glob):
            return False

    if config.path_glob is not None:
        if not _check_field(record, "path", warned):
            return False
        if not glob_match(record["path"], config.path_glob):
            return False

    if config.ext is not None:
        if not _check_field(record, "ext", warned):
            return False
        if record["ext"].lower() != config.ext.lower():
            return False

    if config.size_gt is not None:
        if not _check_field(record, "size", warned):
            return False
        if record["size"] <= config.size_gt:
            return False

    if config.size_lt is not None:
        if not _check_field(record, "size", warned):
            return False
        if record["size"] >= config.size_lt:
            return False

    if config.modified_after is not None:
        if not _check_field(record, "date_modified", warned):
            return False
        if not record["date_modified"] or not _date_gt(record["date_modified"], config.modified_after):
            return False

    if config.modified_before is not None:
        if not _check_field(record, "date_modified", warned):
            return False
        if not record["date_modified"] or not _date_lt(record["date_modified"], config.modified_before):
            return False

    if config.created_after is not None:
        if not _check_field(record, "date_created", warned):
            return False
        if not record["date_created"] or not _date_gt(record["date_created"], config.created_after):
            return False

    if config.created_before is not None:
        if not _check_field(record, "date_created", warned):
            return False
        if not record["date_created"] or not _date_lt(record["date_created"], config.created_before):
            return False

    if config.is_file:
        if record.get("is_file") is not True:
            return False

    if config.is_folder:
        if record.get("is_folder") is not True:
            return False

    if config.attr_chars is not None:
        if not _check_field(record, "attributes", warned):
            return False
        if not string_has_attrs(record["attributes"], config.attr_chars):
            return False

    return True


def run_filter(config: FilterConfig) -> int:
    """Read NDJSON from stdin, apply filters, write matches to stdout.

    Returns exit code (0 = success, 4 = invalid JSON).
    """
    warned: set[str] = set()
    try:
        for lineno, line in enumerate(sys.stdin, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"error: stdin line {lineno}: invalid JSON", file=sys.stderr)
                return 4
            if _matches(record, config, warned):
                write_record(record)
    except BrokenPipeError:
        pass
    return 0

"""Field-to-flag mapping, group aliases, and field resolution helpers."""

from __future__ import annotations

from .constants import RequestFlags

# Maps NDJSON output field name → the EVERYTHING_REQUEST_* flag needed to fetch it
FIELD_TO_FLAG: dict[str, RequestFlags] = {
    "name": RequestFlags.FILE_NAME,
    "path": RequestFlags.PATH,
    "full_path": RequestFlags.FULL_PATH_AND_FILE_NAME,
    "ext": RequestFlags.EXTENSION,
    "size": RequestFlags.SIZE,
    "date_created": RequestFlags.DATE_CREATED,
    "date_modified": RequestFlags.DATE_MODIFIED,
    "date_accessed": RequestFlags.DATE_ACCESSED,
    "attributes": RequestFlags.ATTRIBUTES,
    "run_count": RequestFlags.RUN_COUNT,
    "date_run": RequestFlags.DATE_RUN,
    "date_recently_changed": RequestFlags.DATE_RECENTLY_CHANGED,
    "hl_name": RequestFlags.HIGHLIGHTED_FILE_NAME,
    "hl_path": RequestFlags.HIGHLIGHTED_PATH,
    "hl_full_path": RequestFlags.HIGHLIGHTED_FULL_PATH_AND_FILE_NAME,
}

# Derived fields — always available after a query, no request flag needed.
DERIVED_FIELDS: set[str] = {"is_file", "is_folder"}

ALL_FIELD_NAMES: set[str] = set(FIELD_TO_FLAG.keys()) | DERIVED_FIELDS

FIELD_GROUPS: dict[str, list[str]] = {
    "default": ["name", "path"],
    "all": sorted(ALL_FIELD_NAMES),
    "dates": ["date_created", "date_modified", "date_accessed"],
    "meta": ["size", "ext", "attributes", "is_file", "is_folder"],
    "highlight": ["hl_name", "hl_path", "hl_full_path"],
    "hl": ["hl_name", "hl_path", "hl_full_path"],  # alias
}

# Per spec: name, path always included; full_path for convenience; date_modified for default column.
# size included by default — nearly free from MFT index and broadly useful.
DEFAULT_FIELDS: list[str] = ["name", "path", "full_path", "size", "date_modified"]


def resolve_fields(field_spec: str | None) -> list[str]:
    """Resolve a comma-separated field spec string into a list of unique field names.

    Handles group aliases (default, all, dates, meta, highlight, hl).
    Always includes DEFAULT_FIELDS.
    Raises ValueError for unknown field names.

    Examples:
        resolve_fields(None) -> ["name", "path", "full_path"]
        resolve_fields("default,size") -> ["name", "path", "full_path", "size"]
        resolve_fields("all") -> all fields
        resolve_fields("meta,dates") -> default + meta + dates fields
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add(name: str) -> None:
        if name not in seen:
            seen.add(name)
            result.append(name)

    for field in DEFAULT_FIELDS:
        _add(field)

    if field_spec is not None:
        tokens = [t.strip() for t in field_spec.split(",") if t.strip()]
        unknown: list[str] = []
        for token in tokens:
            if token in FIELD_GROUPS:
                for field in FIELD_GROUPS[token]:
                    _add(field)
            elif token in ALL_FIELD_NAMES:
                _add(token)
            else:
                unknown.append(token)
        if unknown:
            raise ValueError(
                f"Unknown field(s): {', '.join(unknown)}. "
                f"Valid fields: {', '.join(sorted(ALL_FIELD_NAMES))}. "
                f"Valid groups: {', '.join(sorted(FIELD_GROUPS.keys()))}."
            )

    return result


def compute_request_flags(fields: list[str]) -> RequestFlags:
    """Compute the OR'd EVERYTHING_REQUEST_* flags for the given field list.

    Skips derived fields (is_file, is_folder) since they don't need flags.
    """
    flags = RequestFlags(0)
    for field in fields:
        if field in FIELD_TO_FLAG:
            flags |= FIELD_TO_FLAG[field]
    return flags

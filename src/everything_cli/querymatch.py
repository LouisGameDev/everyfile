"""Query matcher for filtering NDJSON records using Everything search syntax.

Supports a practical subset of Everything's search syntax for pipe filtering:
  - Bare terms:  case-insensitive substring match on full_path (or name+path)
  - Wildcards:   * and ? in bare terms → glob match on full_path
  - path:X       substring match on path / full_path
  - ext:X        extension match (with or without dot)
  - name:X       substring match on name
  - "phrase"     exact substring on full_path
  - !term        NOT (invert the match)
  - term1 term2  AND (all must match) — space-separated
  - term1|term2  OR (any can match) — pipe-separated within a group
  - file:        only files (is_file == True)
  - folder:      only folders (is_folder == True)
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class _Term:
    """A single parsed query term."""
    field: str | None  # None = match full_path; "path", "name", "ext"
    pattern: str       # the value to match
    negate: bool       # ! prefix
    is_glob: bool      # contains * or ?
    special: str | None = None  # "file" or "folder"


def _parse_query(query: str) -> list[list[_Term]]:
    """Parse query into AND-groups of OR-terms.

    "foo bar" → AND([foo], [bar])
    "foo|bar" → AND([foo OR bar])
    "foo bar|baz" → AND([foo], [bar OR baz])
    """
    # Tokenize: respect quoted strings, split on whitespace
    tokens: list[str] = []
    i = 0
    while i < len(query):
        if query[i] in (' ', '\t'):
            i += 1
            continue
        if query[i] == '"':
            end = query.find('"', i + 1)
            if end == -1:
                tokens.append(query[i + 1:])
                break
            tokens.append(query[i:end + 1])  # keep quotes for _parse_term
            i = end + 1
        else:
            end = i
            while end < len(query) and query[end] not in (' ', '\t'):
                end += 1
            tokens.append(query[i:end])
            i = end

    # Split each token on | to form OR groups
    and_groups: list[list[_Term]] = []
    for token in tokens:
        or_parts = token.split('|')
        or_terms = [_parse_term(p) for p in or_parts if p]
        if or_terms:
            and_groups.append(or_terms)

    return and_groups


def _parse_term(raw: str) -> _Term:
    """Parse a single term like 'path:foo', '!ext:py', '"exact"', 'file:', etc."""
    negate = False
    if raw.startswith('!'):
        negate = True
        raw = raw[1:]

    # Quoted exact phrase
    if raw.startswith('"') and raw.endswith('"') and len(raw) > 1:
        return _Term(field=None, pattern=raw[1:-1], negate=negate, is_glob=False)

    # Special: file: / folder:
    if raw.lower() in ('file:', 'file'):
        return _Term(field=None, pattern='', negate=negate, is_glob=False, special='file')
    if raw.lower() in ('folder:', 'folder'):
        return _Term(field=None, pattern='', negate=negate, is_glob=False, special='folder')

    # field:value prefixes
    for prefix in ('path:', 'ext:', 'name:'):
        if raw.lower().startswith(prefix):
            field = prefix[:-1]
            value = raw[len(prefix):]
            has_glob = '*' in value or '?' in value
            return _Term(field=field, pattern=value, negate=negate, is_glob=has_glob)

    # Bare term
    has_glob = '*' in raw or '?' in raw
    return _Term(field=None, pattern=raw, negate=negate, is_glob=has_glob)


def _get_match_target(record: dict[str, Any], field: str | None) -> str:
    """Get the string to match against from the record."""
    if field == 'path':
        return str(record.get('full_path', '') or record.get('path', ''))
    if field == 'name':
        return str(record.get('name', ''))
    if field == 'ext':
        ext = record.get('ext', '')
        # Strip leading dot for matching (Everything ext: doesn't use dot)
        return str(ext).lstrip('.') if ext else ''
    # Default: full_path (covers both name and path)
    return str(record.get('full_path', '') or _synthesize_path(record))


def _synthesize_path(record: dict[str, Any]) -> str:
    """Build a full path from name + path if full_path is missing."""
    path = record.get('path', '')
    name = record.get('name', '')
    if path and name:
        return f"{path}\\{name}"
    return str(name or path)


def _term_matches(record: dict[str, Any], term: _Term) -> bool:
    """Check if a single term matches a record."""
    # Special file/folder checks
    if term.special == 'file':
        result = record.get('is_file', True)  # default to True if unknown
        return (not result) if term.negate else result
    if term.special == 'folder':
        result = record.get('is_folder', False)
        return (not result) if term.negate else result

    target = _get_match_target(record, term.field)

    if term.is_glob:
        # fnmatch is case-sensitive; we want case-insensitive
        result = fnmatch.fnmatch(target.lower(), term.pattern.lower())
    elif term.field == 'ext':
        # Extension: exact match (case-insensitive)
        result = target.lower() == term.pattern.lower()
    else:
        # Substring match (case-insensitive)
        result = term.pattern.lower() in target.lower()

    return (not result) if term.negate else result


def matches_query(record: dict[str, Any], parsed: list[list[_Term]]) -> bool:
    """Check if a record matches a parsed query (AND of OR groups)."""
    for or_group in parsed:
        # At least one term in the OR group must match
        if not any(_term_matches(record, term) for term in or_group):
            return False
    return True


def parse_query(query: str) -> list[list[_Term]]:
    """Parse a query string. Returns opaque parsed object for matches_query()."""
    return _parse_query(query)

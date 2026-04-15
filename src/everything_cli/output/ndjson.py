from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from typing import Any


def write_record(record: dict[str, Any]) -> None:
    """Write a single JSON object as one line to stdout.

    Uses json.dumps with ensure_ascii=False for Unicode support.
    Separators are (',', ':') for compact output (no spaces).
    Flushes after write for pipe-friendliness.
    """
    try:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        sys.stdout.buffer.write(line.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    except BrokenPipeError:
        # Downstream pipe closed (e.g. `| head`); exit silently.
        try:
            sys.stdout.close()
        except BrokenPipeError:
            pass
        sys.exit(0)


def write_json(obj: dict[str, Any]) -> None:
    """Write a single JSON object to stdout (same as write_record, for semantic clarity with --count/--info)."""
    write_record(obj)


def write_records(records: Iterable[dict[str, Any]]) -> None:
    """Write an iterable of records as NDJSON to stdout."""
    for record in records:
        write_record(record)

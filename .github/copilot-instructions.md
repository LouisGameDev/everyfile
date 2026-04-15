# Copilot Instructions for everything-cli

## Project Overview

`everything-cli` is a zero-dependency Python CLI for querying Voidtools Everything file search on Windows. It communicates via pure Python IPC (ctypes `WM_COPYDATA`) with no DLL required.

## Technical Stack

- **Language:** Python ≥ 3.11, stdlib only (zero external dependencies)
- **Platform:** Windows only (NTFS MFT + Windows IPC)
- **Build:** setuptools via `pyproject.toml`
- **Version scheme:** CalVer (`YYYY.MM.DD`)
- **Entry points:** `everything`, `every`, `ev` (all identical)

## Code Conventions

- Type annotations on all public signatures
- Linting: Pylint (with `C0103` disabled for Win32 constant names in `sdk/ipc.py`), Pyright (basic mode), mypy (strict)
- No external runtime dependencies — only stdlib and ctypes
- IPC layer in `sdk/ipc.py` uses Win32 patterns: `HWND`, `COPYDATASTRUCT`, `WM_COPYDATA`, `WM_USER`

## Project Structure

```
src/everything_cli/
  __main__.py        CLI entry, argparse, dispatch
  search.py          Search orchestration, pipe filter, count, info
  filter.py          Structured NDJSON filter subcommand
  pick.py            NDJSON field extraction subcommand
  querymatch.py      Local query matching for pipe composition
  sdk/               Everything IPC layer
    ipc.py           Pure Python ctypes IPC (WM_COPYDATA, WM_USER)
    api.py           High-level API wrapper, instance resolution
    constants.py     IPC constants, request flags, sort types
    types.py         Field-to-flag mapping, field groups
  output/            Output formatters
    ndjson.py        NDJSON serializer (stdout)
    human.py         Human-readable formatter (stderr)
  util/              Shared utilities
    glob.py          Glob matching
    dates.py         FILETIME ↔ ISO 8601
    attrs.py         FILE_ATTRIBUTE_* ↔ compact string
```

## Output Architecture

- **stderr:** Human-readable table (interactive use)
- **stdout:** NDJSON when piped, or when `-j`/`-l`/`-0` flags are used
- Pipe composition: when `ev` receives NDJSON on stdin, it filters locally instead of re-querying Everything

## Testing

```powershell
pip install -e ".[dev]"
mypy src/
pytest  # requires Everything running
```

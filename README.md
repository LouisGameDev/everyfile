# everything-cli

A zero-dependency Python CLI for [Voidtools Everything](https://www.voidtools.com/) search.

```
ev ext:py dm:thisweek -n 5
```
```
views.py     C:\Projects\webapp\src\api          2026-04-15 14:32
models.py    C:\Projects\webapp\src\db           2026-04-14 23:18
cli.py       C:\Projects\toolkit\src             2026-04-14 22:05
conftest.py  C:\Projects\webapp\tests            2026-04-14 21:30
setup.py     C:\Projects\toolkit                 2026-04-14 20:12

── 5 results (of 18,294 total) for "ext:py dm:thisweek" ──
  Unique filenames: 5
```

## What is Everything?

[Everything](https://www.voidtools.com/) by Voidtools is a **free, lightweight file search engine** for Windows. When you install it, Everything reads the Master File Table (MFT) of every NTFS volume on your system and builds a complete filename index — typically in **under a second**, even for drives with millions of files. It then monitors the USN Change Journal to keep that index current in real time. The result: **every file and folder on your machine is searchable instantly**.

Everything runs as a small background process (~15 MB of RAM for 1 million files) and provides a rich search syntax for filtering by extension, size, date, path, content, duplicates, and more.

### Why not just use Windows Search?

| | **Everything** | **Windows Search** | **`Get-ChildItem -Recurse`** | **`fd`** / **`find`** |
|---|---|---|---|---|
| **Speed** | **~10 ms** for any query | Seconds to minutes; often misses files | Traverses the entire filesystem every time | Traverses the filesystem every time |
| **Completeness** | Every file and folder on all NTFS volumes | Only indexes "included locations"; skips system dirs, app data, etc. | Complete, but slow | Complete, but slow |
| **Index size** | ~75 MB for 1 M files | Hundreds of MB to GB, with CPU spikes during re-indexing | No index (brute-force walk) | No index (brute-force walk) |
| **Startup** | Indexes a fresh 1 M-file drive in ~1 s | Initial indexing can take **hours** | N/A | N/A |
| **Advanced filters** | `ext:`, `size:`, `dm:`, `dupe:`, `regex:`, `content:`, `parent:`, macros | Basic filters, inconsistent behaviour | `-Filter`, `-Include` flags | `-e`, `-S`, `--size` flags |
| **Real-time updates** | Via NTFS USN journal — instant | Periodic, often delayed minutes | N/A | N/A |
| **Resource usage** | ~15 MB RAM | Heavy (SearchIndexer.exe) | Spikes CPU/disk during scan | Spikes CPU/disk during scan |

### See the difference yourself

Run this in PowerShell to compare a full-drive extension search:

```powershell
# Built-in: traverses every directory on C:\ (slow)
Measure-Command { Get-ChildItem C:\ -Recurse -Filter *.py -ErrorAction SilentlyContinue } | Select-Object TotalSeconds

# Everything via ev: queries the pre-built index (instant)
Measure-Command { ev ext:py -l } | Select-Object TotalSeconds
```

Typical results on a drive with ~1 M files:

| Method | Time |
|---|---|
| `Get-ChildItem -Recurse` | **30 – 120 s** |
| `ev ext:py -l` | **0.02 – 0.1 s** |

The difference grows with drive size. On multi-drive systems with millions of files, Everything stays under 100 ms while filesystem traversals can take **minutes**.

## Features

- **Instant search** — queries Everything's indexed database, returns results in milliseconds
- **Pipe-friendly** — human-readable output on stderr, NDJSON on stdout when piped
- **Pipe composition** — chain `ev` commands to filter results without re-querying
- **Zero dependencies** — stdlib + ctypes only, no DLL needed
- **Everything search syntax** — full pass-through (`ext:`, `dm:`, `size:`, `content:`, `dupe:`, regex, wildcards, macros)
- **Importable Python API** — use as a library with typed `Cursor`/`Row` objects, DB-API 2.0 semantics
- **Multi-instance support** — works with Everything 1.4, 1.5, and 1.5a side by side
- **Pure Python IPC** — communicates via ctypes `SendMessageW` / `WM_COPYDATA`, no DLL required

## Requirements

- **Windows** (Everything uses NTFS and Windows IPC)
- **Python ≥ 3.11**
- **[Voidtools Everything](https://www.voidtools.com/downloads/)** running in the background (1.4, 1.5, or 1.5a)

## Installation

```powershell
pip install everything-cli
```

Or install from source:

```powershell
pip install git+https://github.com/LouisGameDev/everything-cli.git
```

This registers three identical command aliases:

```powershell
everything ext:py          # full name
every ext:py               # short form
ev ext:py                  # shortest — recommended for daily use
```

All three run the same binary. Examples in this README use `ev`.

## Quick Start

```powershell
ev ext:py                          # all Python files
ev ext:py dm:today                 # Python files modified today
ev ext:py -n 5                     # 5 most recently modified
ev ext:py --sort size -d           # largest first
ev --count ext:py                  # just the total count
```

## Using Results With Other Commands

The `-l` flag outputs one full path per line — perfect for feeding into other tools.

### Open a file in VS Code

Find a file by name and open it instantly:

```powershell
code $(ev server.py -n 1 -l)
# opens C:\Projects\webapp\src\server.py in VS Code
```

### Open multiple files

```powershell
# Open all recently modified Python files in VS Code
ev ext:py dm:today -l | ForEach-Object { code $_ }
```

### Delete files

```powershell
# Clean up temp files
ev ext:tmp -l | ForEach-Object { Remove-Item $_ }

# With confirmation prompt
ev ext:tmp -l | ForEach-Object { Remove-Item $_ -Confirm }
```

### Copy or move files

```powershell
# Copy all project configs to a backup folder
ev "ext:toml|ext:cfg path:Projects" -l | ForEach-Object { Copy-Item $_ D:\Backup\ }

# Move all .log files to archive
ev ext:log -l | ForEach-Object { Move-Item $_ D:\Archive\Logs\ }
```

### Count lines of code

```powershell
# Total line count across all Python files in a project
ev "ext:py path:webapp\src" -l | ForEach-Object { Get-Content $_ } | Measure-Object -Line

Lines Words Characters Property
----- ----- ---------- --------
  331
```

### Find TODOs across search results

```powershell
# Find TODO comments in recently changed Python files
ev "ext:py dm:thisweek" -l | ForEach-Object { Select-String -Path $_ -Pattern "TODO" }
C:\Projects\webapp\src\api\views.py:42:    # TODO: add pagination
C:\Projects\webapp\src\db\models.py:17:    # TODO: add index
```

### Paginate results

```powershell
# Skip first 10, show next 5
ev ext:py -l | Select-Object -Skip 10 -First 5

# Or use --offset and -n directly
ev ext:py --offset 10 -n 5
```

### Combine with jq

```powershell
# Get names of large files as a JSON array
ev "ext:py size:>100kb" -j | jq -s '[.[].name]'
["generate_parser.py", "codegen.py", "transformer.py"]
```

## Examples

### Basic search with custom fields

Find the 5 largest Python files, showing name and size:

```
$ ev ext:py -n 5 --sort size -d -f name,size
generate_parser.py  3.8 MB
codegen.py          2.1 MB
codegen.py          2.1 MB
transformer.py      1.9 MB
get-pip.py          1.3 MB

── 5 results (of 18,294 total) for "ext:py"  [sorted by size ↓] ──
  Total size: 11.2 MB
  Duplicate filenames:
    codegen.py  ×2
```

### Combined functions — extension + size

Search functions compose with AND. Find Python files over 1 MB:

```
$ ev "ext:py size:>1mb" -n 5 -f name,size,path
generate_parser.py  3.8 MB  C:\Projects\compiler\src
codegen.py          2.1 MB  C:\Python313\Lib\site-packages\torch\jit
codegen.py          2.1 MB  D:\Envs\ml-project\.venv\Lib\site-packages\torch\jit
transformer.py      1.9 MB  C:\Python313\Lib\site-packages\torch\nn\modules
get-pip.py          1.3 MB  C:\Python313\Scripts

── 5 results (of 7 total) for "ext:py size:>1mb" ──
  Total size: 11.2 MB
```

### Date-scoped search with multiple columns

Python files modified this week, with size and timestamps:

```
$ ev "ext:py dm:thisweek" -n 5 -f name,path,size,date_modified
views.py     C:\Projects\webapp\src\api       8.2 KB  2026-04-15 14:32
models.py    C:\Projects\webapp\src\db        6.4 KB  2026-04-14 23:18
cli.py       C:\Projects\toolkit\src          4.1 KB  2026-04-14 22:05
conftest.py  C:\Projects\webapp\tests         3.7 KB  2026-04-14 21:30
setup.py     C:\Projects\toolkit              1.2 KB  2026-04-14 20:12

── 5 results (of 342 total) for "ext:py dm:thisweek" ──
  Total size: 23.6 KB
```

### OR operator and size filter

Use `|` to combine extensions. Quote the pipe so the shell doesn't intercept it:

```
$ ev "ext:log|ext:tmp size:>100kb" -n 5 -f name,size,path
app-2026-04-14.log   1006.3 KB  C:\Projects\webapp\logs
webpack.log          512.0 KB   C:\Projects\webapp\node_modules\.cache
crash-report.log     8.0 MB     C:\ProgramData\MyApp\logs
session-7a2f.tmp     314.1 KB   C:\Users\dev\AppData\Local\Temp
build-output.log     3.0 MB     D:\CI\artifacts\build-1842

── 5 results (of 4,161 total) for "ext:log|ext:tmp size:>100kb" ──
  Total size: 12.8 MB
```

### Regex search

Find test files using Everything's `regex:` function:

```
$ ev "regex:^test_.*\.py$" -n 5 -f name,path
test_views.py         C:\Projects\webapp\tests\api
test_models.py        C:\Projects\webapp\tests\db
test_serializers.py   C:\Projects\webapp\tests\api
test_auth.py          C:\Projects\webapp\tests\auth
test_utils.py         C:\Projects\toolkit\tests

── 5 results (of 1,847 total) for "regex:^test_.*\.py$" ──
```

### Duplicate detection

Everything's `dupe:` function finds files with identical names across drives:

```
$ ev "dupe: ext:dll" -n 6 -f name,size,path
vcruntime140.dll  99.0 KB   C:\Windows\System32
vcruntime140.dll  99.0 KB   C:\Program Files\Common Files\Microsoft
sqlite3.dll       1.8 MB    C:\Python313\DLLs
sqlite3.dll       1.8 MB    D:\Envs\ml-project\.venv\DLLs
libcrypto-3.dll   4.2 MB    C:\Program Files\Git\usr\bin
libcrypto-3.dll   4.2 MB    C:\Python313\DLLs

── 6 results (of 184,387 total) for "dupe: ext:dll" ──
  Duplicate filenames:
    vcruntime140.dll  ×2
    sqlite3.dll  ×2
    libcrypto-3.dll  ×2
```

### Finding large system files

Discover the biggest executables in System32:

```
$ ev "ext:exe path:Windows\System32" -n 5 --sort size -d -f name,size,path
MRT.exe             210.9 MB  C:\Windows\System32
OneDriveSetup.exe   48.0 MB   C:\Windows\System32
MpCmdRun.exe        18.3 MB   C:\Windows\System32
msiexec.exe         12.4 MB   C:\Windows\System32
svchost.exe         8.6 MB    C:\Windows\System32

── 5 results (of 1,676 total) for "ext:exe path:Windows\System32"  [sorted by size ↓] ──
  Total size: 298.2 MB
```

### Finding empty files

`size:empty` locates zero-byte placeholder files:

```
$ ev "size:empty ext:py" -n 5 -f name,size,path
__init__.py  0 B  C:\Python313\Lib\site-packages\pip\_vendor\urllib3
__init__.py  0 B  C:\Python313\Lib\site-packages\setuptools\_vendor
__init__.py  0 B  C:\Projects\webapp\src\api
__init__.py  0 B  C:\Projects\webapp\src\db
__init__.py  0 B  C:\Projects\webapp\tests

── 5 results (of 4,206 total) for "size:empty ext:py" ──
```

### Count mode

Just the number — no results, no table:

```
$ ev --count "ext:py size:>1mb"
everything: 7 results for "ext:py size:>1mb"
```

### Pipe composition — chaining filters

When you pipe `ev` into `ev`, the second invocation filters locally (no re-query).
Search project files → exclude `__init__` → narrow to API:

```
$ ev "ext:py path:webapp\src" -n 20 -j | ev "!__init__" | ev "path:api" -f name,path
views.py        C:\Projects\webapp\src\api
serializers.py  C:\Projects\webapp\src\api
urls.py         C:\Projects\webapp\src\api
permissions.py  C:\Projects\webapp\src\api

── 4 results (of 14 total) for "path:api" ──
```

### `ev filter` — structured NDJSON filtering

`ev filter` applies typed conditions to NDJSON fields — like `jq` but zero-dep.
Find project source files > 5 KB:

```
$ ev "ext:py path:webapp\src" -f all -j | ev filter --size-gt 5000 --is-file | ev pick name size
{"name":"views.py","size":8412}
{"name":"models.py","size":6553}
{"name":"serializers.py","size":7201}
{"name":"admin.py","size":5890}
{"name":"middleware.py","size":6104}
```

### `ev pick` — field extraction

Extract only the fields you need from NDJSON:

```
$ ev "ext:py path:webapp\src" -n 5 -f all -j | ev pick name size
{"name":"views.py","size":8412}
{"name":"models.py","size":6553}
{"name":"urls.py","size":345}
{"name":"__init__.py","size":0}
{"name":"admin.py","size":5890}
```

### Output modes

| Flag | Description | Use case |
|------|-------------|----------|
| *(default)* | Human table on stderr, NDJSON on stdout when piped | Interactive browsing |
| `-l` / `--list` | One full path per line | `ForEach-Object`, `$(...)` |
| `-0` / `--null` | Null-separated full paths | Paths with special characters |
| `-j` / `--json` | Force NDJSON to stdout | Processing with `ev filter`/`ev pick`/`jq` |
| `-q` / `--quiet` | Suppress stderr | Silent scripting |

```
$ ev ext:py -n 3 -l
C:\Projects\webapp\src\api\views.py
C:\Projects\webapp\src\db\models.py
C:\Projects\toolkit\src\cli.py
```

## Columns & Fields

`--columns` controls the human-readable stderr display. `-f` / `--fields` controls NDJSON output fields.

```powershell
ev ext:py -f name,size             # display: name + size
ev ext:py -f all                   # all fields in NDJSON
ev ext:py -f dates,meta            # default + date + metadata groups
ev ext:py --columns name,size      # custom stderr only, default NDJSON
```

Run `ev --help-columns` for the full list:

```
available columns:
  * name                      file or folder name
  * path                      parent directory path
    full_path                 complete path including filename
    ext                       file extension (without dot)
    size                      file size in bytes
    date_created              creation timestamp
  * date_modified             last modified timestamp
    date_accessed             last accessed timestamp
    date_run                  last run timestamp
    date_recently_changed     recently changed timestamp
    run_count                 number of times file was executed
    attributes                file system attributes string
    is_file                   true if result is a file (derived)
    is_folder                 true if result is a folder (derived)
    hl_name                   highlighted matching name
    hl_path                   highlighted matching path
    hl_full_path              highlighted matching full path

  * = included in default display

groups (use with -f):
    default      name, path
    all          every available column
    dates        date_created, date_modified, date_accessed
    meta         size, ext, attributes, is_file, is_folder
    hl           hl_name, hl_path, hl_full_path
```

## Sorting

Default sort is **date modified descending** (newest first), so `-n 5` gives the 5 most recently modified matches.

```powershell
ev ext:py                          # newest first (default)
ev ext:py --sort name              # alphabetical
ev ext:py --sort size -d           # largest first
ev ext:py --sort created           # oldest created first
```

Sort fields: `name`, `path`, `size`, `ext`, `created`, `modified`, `accessed`, `run-count`, `date-run`, `recently-changed`, `attributes`.

## `ev filter` flags

| Flag | Description |
|------|-------------|
| `--name GLOB` | Glob match on name |
| `--path GLOB` | Glob match on path |
| `--ext .EXT` | Exact extension match |
| `--size-gt N` | Size > N bytes |
| `--size-lt N` | Size < N bytes |
| `--modified-after DATE` | Modified after ISO date |
| `--modified-before DATE` | Modified before ISO date |
| `--created-after DATE` | Created after ISO date |
| `--created-before DATE` | Created before ISO date |
| `--is-file` | Only files |
| `--is-folder` | Only folders |
| `--attr CHARS` | Require attribute chars (e.g. `RHA`) |

## Everything Search Syntax

The query is passed verbatim to Everything. Full syntax reference:

```
Operators:    space=AND  |=OR  !=NOT  < >=group  " "=exact phrase
Wildcards:    *=any chars  ?=one char
Functions:    ext:py  size:>1mb  dm:today  parent:C:\Dev  content:TODO
              dc: da: dr: rc: depth: len: dupe: child: childcount:
Modifiers:    case: nocase: regex: path: ww: file: folder:
Macros:       audio: video: doc: pic: zip: exe:
Size:         size:1kb..10mb  size:>1gb  size:empty  size:tiny..huge
Dates:        dm:today  dm:thisweek  dc:yesterday  da:last2weeks
```

Shell metacharacters need quoting:

```powershell
ev 'foo|bar'              # OR (quote the pipe)
ev '!secret'              # NOT (quote the bang)
ev 'size:>1mb'            # function (quote the >)
ev ext:py dm:today        # no special chars — no quoting needed
```

## Instance Management

Multiple Everything versions can run side-by-side. The CLI auto-detects instances in priority order: `1.5a → 1.5 → 1.4 → default`.

```powershell
ev --instances                              # list running instances
ev --instance 1.4 ext:py                    # query via Everything 1.4

# Persist your choice
$env:EVERYTHING_INSTANCE = "1.5a"           # session
[System.Environment]::SetEnvironmentVariable('EVERYTHING_INSTANCE', '1.5a', 'User')  # permanent
```

Priority: `--instance` flag > `$EVERYTHING_INSTANCE` env var > auto-detect.

## Service Info

```
$ ev --version
everything-cli 2026.04.15 (Python 3.13.5) / Everything 1.5.0.1404
Instance: 1.5a  (via auto-detect)

$ ev --info
Everything v1.5.0.1404
Admin: no
AppData: no
Instance: 1.5a

$ ev --instances
Running Everything instances:

  1.5a         class: EVERYTHING_TASKBAR_NOTIFICATION_(1.5a)  ←  active

Active instance: 1.5a
  Selected via: auto-detect
```

## Python API

`everything-cli` is also a fully importable Python library — no CLI needed. The API uses DB-API 2.0 cursor/row semantics, is fully type-annotated, and has zero dependencies.

```powershell
pip install everything-cli
```

### Quick Start

```python
from everything_cli import search, count

# Iterate results
for row in search("ext:py"):
    print(row.name, row.full_path)

# Count matches without fetching
print(f"Python files: {count('ext:py')}")
```

### Search with Options

```python
from everything_cli import search

# Find the 10 largest log files
cursor = search(
    "ext:log",
    fields="size",
    sort="size",
    descending=True,
    limit=10,
)

print(f"Showing {cursor.count} of {cursor.total} total matches")
for row in cursor:
    print(f"  {row.size:>12,} bytes  {row.full_path}")
```

Parameters: `query`, `fields`, `sort`, `descending`, `limit`, `offset`, `match_case`, `match_path`, `match_whole_word`, `regex`, `instance`.

### Cursor — Fetch Patterns

`search()` returns a `Cursor` — a forward-only iterator with DB-API 2.0 fetch methods.

```python
from everything_cli import search

cursor = search("ext:py", limit=100)

# Metadata is available immediately (before iterating)
print(f"Total matches: {cursor.total}")
print(f"Results in cursor: {cursor.count}")

# Fetch one at a time
first = cursor.fetchone()       # Row | None

# Fetch in batches
batch = cursor.fetchmany(20)    # list[Row] (up to 20)

# Fetch all remaining
rest = cursor.fetchall()        # list[Row]
```

Batch processing large result sets:

```python
cursor = search("ext:log", limit=10_000, fields="size")

while batch := cursor.fetchmany(500):
    for row in batch:
        process(row)
```

### Row — Typed Property Access

Each result is a `Row` with typed properties and dict-style access.

```python
from everything_cli import search

for row in search("ext:py dm:today", fields="size,dates"):
    # Typed properties (IDE autocomplete works)
    row.name            # str    — always present
    row.path            # str    — always present
    row.full_path       # str    — always present
    row.size            # int | None
    row.date_modified   # str | None (ISO 8601)
    row.date_created    # str | None (ISO 8601)
    row.is_file         # bool | None

    # Dict-style access
    row["name"]
    row.get("size", 0)
    "size" in row       # True

    # Serialize to dict
    row.to_dict()       # {"name": ..., "path": ..., ...}
```

### Everything Class — Reusable Connection

For repeated queries or service introspection, create an `Everything` instance.

```python
from everything_cli import Everything

ev = Everything()               # auto-detect running instance
# ev = Everything("1.5a")      # target a specific instance

# Reuse connection for multiple queries
py_files = ev.search("ext:py", limit=5)
log_files = ev.search("ext:log", sort="size", descending=True, limit=5)
total_py = ev.count("ext:py")

# Service introspection
print(ev.version)               # {"major": 1, "minor": 5, "revision": 0, ...}
print(ev.info)                  # indexed file/folder counts
print(ev.instance_name)         # "1.5a"

# List all running instances
for inst in Everything.instances():
    print(inst["name"], inst["hwnd"])
```

### Error Handling

```python
from everything_cli import search, EverythingError

try:
    results = search("ext:py").fetchall()
except EverythingError as e:
    if e.is_not_running:
        print("Everything is not running")
    else:
        print(f"IPC error: {e}")
```

### Fields and Sorting

```python
from everything_cli import search

# Field groups: "default", "all", "dates", "meta", "hl"
search("*.py", fields="all")            # every available field
search("*.py", fields="meta")           # size, ext, attributes, is_file, is_folder
search("*.py", fields="size,ext")       # individual fields

# Sort options: name, path, size, ext, created, modified, accessed, ...
search("*.py", sort="size", descending=True)
search("*.py", sort="modified")         # oldest first
search("*.py", sort="modified", descending=True)  # newest first
```

For the full API reference, see [docs/PYTHON_API_SPEC.md](docs/PYTHON_API_SPEC.md).

## Architecture

```
src/everything_cli/
  __main__.py        CLI entry point, argparse, dispatch
  search.py          Search orchestration, pipe filter, count, info, version
  filter.py          Structured NDJSON filter (ev filter)
  pick.py            NDJSON field extraction (ev pick)
  querymatch.py      Local query matching for pipe composition
  sdk/
    ipc.py           Pure Python IPC via ctypes (WM_COPYDATA, WM_USER)
    api.py           High-level API wrapper, instance resolution
    constants.py     Everything IPC constants, request flags, sort types
    types.py         Field-to-flag mapping, field groups, resolution
  output/
    ndjson.py        NDJSON serializer (stdout)
    human.py         Human-readable formatter (stderr)
  util/
    glob.py          Glob matching for filter command
    dates.py         FILETIME ↔ ISO 8601 conversion
    attrs.py         FILE_ATTRIBUTE_* ↔ compact string
```

**IPC approach**: Pure Python ctypes — `FindWindowW` to locate Everything's hidden IPC window, `SendMessageW` with `WM_COPYDATA` for search queries, `WM_USER` for version/info. No DLL dependency.

## Development

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

# Type check
mypy src/

# Test (requires Everything running for integration tests)
pytest
```

## See Also

- [Everything SDK Python documentation](https://www.voidtools.com/support/everything/sdk/python/)
- [Everything search syntax](https://www.voidtools.com/support/everything/searching/)
- [Everything downloads](https://www.voidtools.com/downloads/)

## License

MIT

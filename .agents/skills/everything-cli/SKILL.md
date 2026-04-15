---
name: everything-cli
description: >
  Use the everything-cli (ev) command or Python API to search files instantly on
  Windows via Voidtools Everything. Use when the user asks to "find files",
  "search for files", "locate a file", "list files by extension", "find large files",
  "find recent files", "find duplicates", or any file discovery task on Windows.
  Also use when the user wants to search files programmatically from Python code.
  Do NOT use for Linux/macOS file search or when Everything is not installed.
license: MIT
compatibility: >
  Requires Windows, Python >= 3.11, and Voidtools Everything (1.4, 1.5, or 1.5a)
  running in the background.
---

# everything-cli

Instant file search on Windows via [Voidtools Everything](https://www.voidtools.com/).

Everything indexes every file and folder on all NTFS volumes via the Master File
Table in under a second. Queries return in ~10 ms regardless of drive size. The
CLI communicates with Everything via pure Python IPC (ctypes WM_COPYDATA) — no
DLL or SDK required.

## When to use this skill

Use when the user needs to:
- Find files by name, extension, path, size, or date
- Locate recently modified files
- Find duplicate filenames across drives
- Search file contents
- Count files matching a pattern
- Feed file search results into other commands
- Search files programmatically from Python code
- Build scripts or tools that need fast file search on Windows

Do NOT use when:
- The user is on Linux or macOS (Everything is Windows-only)
- Everything is not installed or not running
- The user wants to search inside file contents only (use `grep`/`Select-String` directly)

## Installation

```powershell
pip install everything-cli
```

## Command Aliases

All three are identical — use `ev` for brevity:

```
everything <query>
every <query>
ev <query>
```

## Core Search Patterns

```powershell
ev ext:py                          # all Python files
ev ext:py dm:today                 # modified today
ev ext:py dm:thisweek              # modified this week
ev ext:py -n 5                     # top 5 most recently modified
ev ext:py --sort size -d           # largest first
ev --count ext:py                  # just the count
ev "ext:py size:>1mb"              # files over 1 MB
ev "ext:log|ext:tmp"               # OR: logs or temp files
ev "dupe: ext:dll"                 # duplicate filenames
ev "regex:^test_.*\.py$"           # regex search
ev "size:empty ext:py"             # zero-byte files
ev "ext:py path:webapp\src"        # scoped to directory
ev "ext:py content:TODO"           # search file contents
```

## Everything Search Syntax

The query is passed verbatim to Everything:

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

## Output Modes

| Flag | Output | Use Case |
|------|--------|----------|
| *(default)* | Human table on stderr, NDJSON on stdout when piped | Interactive |
| `-l` / `--list` | One full path per line | `ForEach-Object`, `$(...)` |
| `-0` / `--null` | Null-separated paths | Paths with special characters |
| `-j` / `--json` | NDJSON to stdout | `ev filter`, `ev pick`, `jq` |
| `-q` / `--quiet` | Suppress stderr | Silent scripting |

## Fields and Columns

```powershell
ev ext:py -f name,size             # select NDJSON fields
ev ext:py -f all                   # all fields
ev ext:py -f dates,meta            # field groups
ev ext:py --columns name,size      # human-readable display
ev --help-columns                  # list all fields
```

Available fields: `name`, `path`, `full_path`, `ext`, `size`, `date_created`,
`date_modified`, `date_accessed`, `date_run`, `date_recently_changed`,
`run_count`, `attributes`, `is_file`, `is_folder`, `hl_name`, `hl_path`,
`hl_full_path`

Groups: `default`, `all`, `dates`, `meta`, `hl`

## Sorting

Default: date modified descending (newest first).

```powershell
ev ext:py --sort name              # alphabetical
ev ext:py --sort size -d           # largest first
ev ext:py --sort created           # oldest created first
```

Sort fields: `name`, `path`, `size`, `ext`, `created`, `modified`, `accessed`,
`run-count`, `date-run`, `recently-changed`, `attributes`

## Pipe Composition

When piped NDJSON from another `ev`, the second invocation filters locally
without re-querying Everything:

```powershell
ev ext:py | ev "path:src"              # filter by path
ev ext:py | ev "!__pycache__"          # exclude pattern
ev ext:py | ev "path:src" | ev "!test" # chain filters
```

Use `-S` to force an Everything query even when stdin is piped.

## Subcommands

### `ev filter` — structured NDJSON filtering

```powershell
ev ext:py -f all -j | ev filter --size-gt 5000 --is-file
ev ext:py -f all -j | ev filter --modified-after 2026-01-01
```

Flags: `--name GLOB`, `--path GLOB`, `--ext .EXT`, `--size-gt N`,
`--size-lt N`, `--modified-after DATE`, `--modified-before DATE`,
`--created-after DATE`, `--created-before DATE`, `--is-file`, `--is-folder`,
`--attr CHARS`

### `ev pick` — field extraction

```powershell
ev ext:py -f all -j | ev pick name size
# {"name":"views.py","size":8412}
```

## Scripting Patterns

```powershell
# Open in VS Code
code $(ev server.py -n 1 -l)

# Process each result
ev ext:py dm:today -l | ForEach-Object { code $_ }

# Delete files
ev ext:tmp -l | ForEach-Object { Remove-Item $_ }

# Copy to backup
ev "ext:toml path:Projects" -l | ForEach-Object { Copy-Item $_ D:\Backup\ }

# Count lines of code
ev "ext:py path:src" -l | ForEach-Object { Get-Content $_ } | Measure-Object -Line

# Search contents of matched files
ev "ext:py dm:thisweek" -l | ForEach-Object { Select-String -Path $_ -Pattern "TODO" }

# Paginate
ev ext:py -l | Select-Object -Skip 10 -First 5

# JSON processing with jq
ev "ext:py size:>100kb" -j | jq -s '[.[].name]'
```

## Instance Management

```powershell
ev --instances                         # list running instances
ev --instance 1.4 ext:py              # target specific version
$env:EVERYTHING_INSTANCE = "1.5a"     # persist for session
```

Priority: `--instance` flag > `$EVERYTHING_INSTANCE` > auto-detect
(1.5a → 1.5 → 1.4 → default)

## Service Info

```powershell
ev --version      # CLI + Everything version
ev --info         # Everything service status
ev --instances    # running instances
```

## Python API

`everything-cli` is also a fully importable Python library with typed
`Cursor`/`Row` objects following DB-API 2.0 semantics. Use the API when the user
wants to search files from Python code rather than the CLI.

### Import Surface

```python
from everything_cli import search, count          # module-level functions
from everything_cli import Everything             # reusable connection
from everything_cli import Cursor, Row            # types for annotation
from everything_cli import EverythingError        # error handling
```

### Quick Search

```python
from everything_cli import search, count

# Iterate results
for row in search("ext:py"):
    print(row.name, row.full_path)

# Count without fetching
total = count("ext:py")
```

### Search with Options

```python
cursor = search(
    "ext:log",
    fields="size",           # "all", "meta", "dates", or comma-separated
    sort="size",             # name, path, size, ext, created, modified, ...
    descending=True,
    limit=10,
    offset=0,
    match_case=False,
    match_path=False,
    regex=False,
    instance=None,           # "1.5a", "1.4", or None for auto-detect
)
```

### Cursor Fetch Patterns

```python
cursor = search("ext:py", limit=100)

cursor.total                  # total matches in Everything DB
cursor.count                  # results in this cursor
len(cursor)                   # same as cursor.count

first = cursor.fetchone()     # Row | None
batch = cursor.fetchmany(20)  # list[Row] up to 20
rest = cursor.fetchall()      # list[Row] all remaining

# Batch processing
cursor = search("ext:log", limit=10_000, fields="size")
while batch := cursor.fetchmany(500):
    process(batch)
```

### Row Access

```python
for row in search("ext:py dm:today", fields="size,dates"):
    row.name                  # str   (always present)
    row.path                  # str   (always present)
    row.full_path             # str   (always present)
    row.size                  # int | None
    row.date_modified         # str | None (ISO 8601)
    row.date_created          # str | None (ISO 8601)
    row.is_file               # bool | None

    row["name"]               # dict-style access
    row.get("size", 0)        # with default
    "size" in row             # membership test
    row.to_dict()             # serialize to dict
```

### Reusable Connection

```python
from everything_cli import Everything

ev = Everything()             # auto-detect instance
ev = Everything("1.5a")      # target specific instance

results = ev.search("ext:py", limit=5)
total = ev.count("ext:py")

ev.version                    # {"major": 1, "minor": 5, ...}
ev.info                       # indexed file/folder counts
ev.instance_name              # "1.5a"
Everything.instances()        # list all running instances
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

### When to Use API vs CLI

| Scenario | Use |
|----------|-----|
| User asks to find/list files in terminal | CLI (`ev`) |
| User wants file search in a Python script | API (`search()`) |
| One-off file lookup from agent | CLI (`ev -l`) |
| Building a tool that needs file search | API (`Everything` class) |
| Piping results between commands | CLI (pipe composition) |
| Processing results programmatically | API (iterate `Cursor`) |

## Safety

- Always confirm with the user before piping results into destructive commands
  (`Remove-Item`, `Move-Item`)
- Use `-n` to limit results when testing queries
- Use `--count` or `count()` first to check how many files match before bulk operations
- Everything must be running — if it's not, the CLI/API will error

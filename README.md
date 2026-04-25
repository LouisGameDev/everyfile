# everyfile

[![CI](https://github.com/LouisGameDev/everyfile/actions/workflows/ci.yml/badge.svg)](https://github.com/LouisGameDev/everyfile/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/everyfile)](https://pypi.org/project/everyfile/)
[![ClawHub](https://img.shields.io/badge/ClawHub-everyfile-blue)](https://clawhub.ai/louisgamedev/everyfile)

> **Query every file on every drive — by name, regex, extension, size, date, attributes, duplicates — with full boolean logic. Results in under a millisecond. Your filesystem is a database.**

10 million files across multiple drives. Agents and workflows that navigate them with `Get-ChildItem`, `os.walk`, or `glob` are flying blind — slow, fragile, and context-starved. `everyfile` changes that.

Backed by [Voidtools Everything](https://www.voidtools.com/)'s real-time NTFS index, every query resolves in **< 1 ms** regardless of drive size. No recursion. No indexing wait. An agent goes from guessing paths to **instant, structured answers** across your entire filesystem.

```powershell
# Find every test file across all drives — Python and JS/TS — in one query
ev "regex:^test_.+\.py$ | regex:^spec_.+\.(js|ts)$" -n 8
```

```
test_controllers.py  2026-04-18 18:40  E:\Projects\chatbot\tests\controllers          19.7 KB
test_credentials.py  2026-04-18 18:33  E:\Projects\filesearch\.venv\Lib\site-packages  7.8 KB
test_platform.py     2026-04-18 18:33  E:\Projects\filesearch\.venv\Lib\site-packages 11.4 KB
test_backends.py     2026-04-18 18:33  E:\Projects\filesearch\.venv\Lib\site-packages  1.2 KB
test_typeops.py      2026-04-18 08:30  E:\Projects\filesearch\.venv\Lib\site-packages  3.9 KB
test_tuples.py       2026-04-18 08:30  E:\Projects\filesearch\.venv\Lib\site-packages  1.1 KB
test_structs.py      2026-04-18 08:30  E:\Projects\filesearch\.venv\Lib\site-packages  3.9 KB
test_statements.py   2026-04-18 08:30  E:\Projects\filesearch\.venv\Lib\site-packages  5.5 KB

  8 of 20,755 results for "regex:^test_.+\.py$ | regex:^spec_.+\.(js|ts)$"
```

```powershell
# Find duplicate DLLs wasting disk space — across every drive, instantly
ev "sizedupe: ext:dll size:>1mb" -n 4
```

```
graphics_engine.dll  2024-03-31 05:58  C:\Program Files\NVIDIA\RTXVoice         402.5 MB
graphics_engine.dll  2024-03-31 05:58  C:\Program Files\NVIDIA\Installer2\nv    402.5 MB
browser_core.dll     2026-04-16 03:51  C:\Program Files\Edge\Application        303.8 MB
browser_core.dll     2026-04-16 03:51  C:\Program Files\Edge\Optimized          303.8 MB

  4 of 11,800 results for "sizedupe: ext:dll size:>1mb"

  ├ size      1.4 GB
  └ names     browser_core.dll×2  graphics_engine.dll×2
```

Three integration surfaces cover every use case:

| Surface | Best for |
|---------|----------|
| **CLI** (`ev`) | Shell scripts, pipelines, terminal power users |
| **Python API** | Scripts and tools that iterate results programmatically |

## Table of Contents

| | Section | What's inside |
|---|---------|---------------|
| **Intro** | [What is Everything?](#what-is-everything) | Why Everything beats Windows Search, benchmark comparison |
| | [Features](#features) | Capabilities at a glance |
| **Setup** | [Install](#install) | |
| | [Prerequisites](#prerequisites) | Windows, Python ≥ 3.11, Everything running |
| | [CLI](#cli--search-files-from-the-terminal) | `pip install everyfile` — `ev` command |
| | [Python API](#python-api--search-files-from-code) | `from everyfile import search` |
| | [Agent Skill](#agent-skill--teach-any-ai-agent-to-use-everything) | `npx skills add LouisGameDev/everyfile` |
| | [OpenClaw](#openclaw--use-everything-from-openclaw-agents) | Skill for OpenClaw gateway agents |
| | [Install from source](#install-from-source) | Editable dev install |
| | [Command aliases](#command-aliases) | `ev`, `every`, `everyfile` |
| **CLI** | [Quick Start](#quick-start) | First commands to try |
| | [Using Results](#using-results-with-other-commands) | VS Code, delete, copy, grep, jq, pagination |
| | [Examples](#examples) | Sort, filter, regex, count, pipes, `ev filter`, `ev pick`, output modes |
| **CLI Reference** | [Fields](#fields) | `-f` / `--fields` options and groups |
| | [Sorting](#sorting) | `--sort` options, default order |
| | [`ev filter` flags](#ev-filter-flags) | Structured NDJSON filtering flags |
| | [Search Syntax](#everything-search-syntax) | Operators, wildcards, functions, macros, size/date filters |
| | [Instance Management](#instance-management) | Multi-version Everything, `--instance`, env var |
| | [Service Info](#service-info) | `--version`, `--info`, `--instances` |
| **Python API** | [Python API](#python-api) | `search()`, `count()`, `Cursor`, `Row`, `Everything` class, error handling |
| **Internals** | [Versioning](#versioning) | CalVer scheme, release workflow |
| | [Architecture](#architecture) | Module layout, IPC approach |
| | [Development](#development) | Clone, install, type-check, test |
| | [See Also](#see-also) | External links |
| | [License](#license) | MIT |

A zero-dependency Python CLI for [Voidtools Everything](https://www.voidtools.com/) search.

```powershell
ev ext:py path:fixtures -n 5
```

<!-- example:hero -->
```
views.py  2026-04-17 00:00  webapp\src\api  652 B
models.py  2026-04-16 23:00  webapp\src\db  608 B
serializers.py  2026-04-16 22:00  webapp\src\api  783 B
middleware.py  2026-04-16 21:00  webapp\src  1011 B
admin.py  2026-04-16 20:00  webapp\src  523 B

  5 of 18 results for "ext:py path:fixtures"

  ├ size      3.5 KB
  └ names     admin.py  middleware.py  models.py  serializers.py  views.py
```
<!-- /example:hero -->

## What is Everything?

[Everything](https://www.voidtools.com/) by Voidtools is a **free, lightweight file search engine** for Windows. When you install it, Everything reads the Master File Table (MFT) of every NTFS volume on your system and builds a complete filename index — typically in **under a second**, even for drives with millions of files. It then monitors the USN Change Journal to keep that index current in real time. The result: **every file and folder on your machine is searchable instantly**.

Everything runs as a small background process (~15 MB of RAM for 1 million files) and provides a rich search syntax for filtering by extension, size, date, path, content, duplicates, and more.

### Why not just use Windows Search?

| | **Everything** | **Windows Search** | **`Get-ChildItem -Recurse`** |
|---|---|---|---|
| **Speed** | **~10 ms** for any query | Seconds to minutes; often misses files | Traverses the entire filesystem every time |
| **Completeness** | Every file and folder on all NTFS volumes | Only indexes "included locations"; skips system dirs, app data, etc. | Complete, but slow |
| **Index size** | ~75 MB for 1 M files | Hundreds of MB to GB, with CPU spikes during re-indexing | No index (brute-force walk) |
| **Startup** | Indexes a fresh 1 M-file drive in ~1 s | Initial indexing can take **hours** | N/A |
| **Advanced filters** | `ext:`, `size:`, `dm:`, `dupe:`, `regex:`, `content:`, `parent:`, macros | Basic filters, inconsistent behaviour | `-Filter`, `-Include` flags |
| **Real-time updates** | Via NTFS USN journal — instant | Periodic, often delayed minutes | N/A |
| **Resource usage** | ~15 MB RAM | Heavy (SearchIndexer.exe) | Spikes CPU/disk during scan |

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

# Install

## Prerequisites

1. **Windows** — Everything uses NTFS and Windows IPC
2. **Python ≥ 3.11**
3. **[Voidtools Everything](https://www.voidtools.com/downloads/)** running in the background

> **New to Everything?** Download [Everything 1.5a](https://www.voidtools.com/downloads/#alpha) (recommended). It's the latest alpha with the most features, runs alongside stable versions, and is what most power users run. Install it, let it index your drives (takes ~1 second), and leave it running in the system tray.

Pick what you need — each layer builds on the one before it.

## CLI — search files from the terminal

```powershell
pip install everyfile
```

This gives you the `ev` command (plus `every` and `everyfile` as aliases):

```powershell
ev ext:py                          # find all Python files instantly
ev ext:log size:>1mb dm:today      # large log files modified today
ev server.py -n 1 -l | code -     # open first match in VS Code
```

## Python API — search files from code

Same package, just import it:

```python
from everyfile import search, count

for row in search("ext:py dm:today", limit=10):
    print(row.name, row.full_path)

print(f"Total Python files: {count('ext:py')}")
```

## Agent Skill — teach any AI agent to use Everything

Install to any [Agent Skills](https://agentskills.io/)-compatible agent (Copilot, Claude Code, Cursor, Codex, and [40+ more](https://agentskills.io/clients)):

```powershell
npx skills add LouisGameDev/everyfile -g
```

Or install from a local clone:

```powershell
npx skills add ./path/to/everyfile -g
```

The skill teaches agents *when* and *how* to use `ev` and the Python API — with search syntax, safety guidelines, and decision logic included.

## OpenClaw — use Everything from OpenClaw agents

If you run [OpenClaw](https://openclaw.ai/), you can give your agents instant file search on Windows.

**Install the skill** (via [ClawHub](https://clawhub.ai/) or manually):

```bash
openclaw skills install everyfile
```

Or copy the skill folder manually into your workspace:

```bash
cp -r .agents/skills/everyfile <workspace>/skills/everyfile
```

**Install the Python package** (the skill gates on the `ev` binary):

```powershell
pip install everyfile
```

The skill auto-gates on `win32` and requires `ev` on PATH. Once installed, your OpenClaw agents will use Everything for all file discovery instead of slow filesystem traversals.

## Install from source

```powershell
git clone https://github.com/LouisGameDev/everyfile.git
cd everyfile
pip install -e ".[dev]"           # editable install with dev tools
```

## Command aliases

All three run the same binary. Examples in this README use `ev`.

```powershell
everyfile ext:py           # full name
every ext:py               # short form
ev ext:py                  # shortest — recommended for daily use
```

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

### Sort by size

Find the 5 largest Python files:

```powershell
ev ext:py path:fixtures -n 5 --sort size -d -f name,size
```

<!-- example:sort-size -->
```
middleware.py  1011 B
utils.py  824 B
serializers.py  783 B
test_views.py  718 B
views.py  652 B

  5 of 18 results for "ext:py path:fixtures"  │  sorted by size ↓

  ├ size      3.9 KB
  └ names     middleware.py  serializers.py  test_views.py  utils.py  views.py
```
<!-- /example:sort-size -->

### Combined functions — extension + size

Search functions compose with AND. Find Python files over 500 bytes:

```powershell
ev "ext:py size:>500" path:fixtures -n 5 -f name,size,path
```

<!-- example:size-filter -->
```
views.py  652 B  webapp\src\api
models.py  608 B  webapp\src\db
serializers.py  783 B  webapp\src\api
middleware.py  1011 B  webapp\src
admin.py  523 B  webapp\src

  5 of 10 results for "ext:py size:>500 path:fixtures"

  ├ size      3.5 KB
  └ names     admin.py  middleware.py  models.py  serializers.py  views.py
```
<!-- /example:size-filter -->

### Custom field order

Show name, path, size, and date in any order you want:

```powershell
ev "ext:py path:fixtures" -n 5 -f name,path,size,date_modified
```

<!-- example:date-scope -->
```
views.py  webapp\src\api  652 B  2026-04-17 00:00
models.py  webapp\src\db  608 B  2026-04-16 23:00
serializers.py  webapp\src\api  783 B  2026-04-16 22:00
middleware.py  webapp\src  1011 B  2026-04-16 21:00
admin.py  webapp\src  523 B  2026-04-16 20:00

  5 of 18 results for "ext:py path:fixtures"

  ├ size      3.5 KB
  └ names     admin.py  middleware.py  models.py  serializers.py  views.py
```
<!-- /example:date-scope -->

### OR operator

Use `|` to combine extensions. Quote the pipe so the shell doesn't intercept it:

```powershell
ev 'ext:log|ext:tmp path:fixtures' -n 5 -f name,size,path
```

<!-- example:or-operator -->
```
cache.tmp  195.3 KB  webapp
app-2026-04-14.log  258.8 KB  webapp\logs
debug.log  12.6 KB  webapp\logs

  3 of 3 results for "ext:log|ext:tmp path:fixtures"

  ├ size      466.7 KB
  └ names     app-2026-04-14.log  cache.tmp  debug.log
```
<!-- /example:or-operator -->

### Regex search

Find test files using Everything's `regex:` function:

```powershell
ev 'regex:^test_.*\.py$ path:fixtures' -n 5 -f name,path
```

<!-- example:regex -->
```
test_views.py  webapp\tests
test_serializers.py  webapp\tests
test_auth.py  webapp\tests
test_utils.py  toolkit\tests

  4 of 4 results for "regex:^test_.*\.py$ path:fixtures"

  └ names     test_auth.py  test_serializers.py  test_utils.py  test_views.py
```
<!-- /example:regex -->

### Finding empty files

`size:empty` locates zero-byte placeholder files:

```powershell
ev 'size:empty ext:py path:fixtures' -f name,size,path
```

<!-- example:empty-files -->
```
__init__.py  0 B  webapp\tests
__init__.py  0 B  webapp\src\db
__init__.py  0 B  webapp\src\api
__init__.py  0 B  webapp\src

  4 of 4 results for "size:empty ext:py path:fixtures"

  ├ size      0 B
  └ names     __init__.py×4
```
<!-- /example:empty-files -->

### Count mode

Just the number — no results, no table:

```powershell
ev --count 'ext:py path:fixtures'
```

<!-- example:count -->
```
everything: 18 results for "ext:py path:fixtures"
```
<!-- /example:count -->

### Pipe composition — chaining filters

When you pipe `ev` into `ev`, the second invocation filters locally (no re-query).
Start broad, then narrow to API:

```powershell
ev 'ext:py path:webapp\src' -n 20 -j | ev '!__init__' | ev 'path:api' -f name,path
```

```
views.py        C:\Projects\webapp\src\api
serializers.py  C:\Projects\webapp\src\api
urls.py         C:\Projects\webapp\src\api
permissions.py  C:\Projects\webapp\src\api
```

### `ev filter` — structured NDJSON filtering

`ev filter` applies typed conditions to NDJSON fields — like `jq` but zero-dep.
Find project source files > 5 KB:

```powershell
ev 'ext:py path:webapp\src' -f all -j | ev filter --size-gt 5000 --is-file | ev pick name size
```

```
{"name":"views.py","size":8412}
{"name":"models.py","size":6553}
{"name":"serializers.py","size":7201}
{"name":"admin.py","size":5890}
{"name":"middleware.py","size":6104}
```

### `ev pick` — field extraction

Extract only the fields you need from NDJSON:

```powershell
ev 'ext:py path:webapp\src' -n 5 -f all -j | ev pick name size
```

```
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

```powershell
ev ext:py path:fixtures -n 3 -l
```

<!-- example:list-mode -->
```
webapp\src\api\views.py
webapp\src\db\models.py
webapp\src\api\serializers.py
```
<!-- /example:list-mode -->

## Fields

`-f` / `--fields` controls both the human-readable stderr display and NDJSON output fields.

```powershell
ev ext:py -f name,size             # display and NDJSON: name + size
ev ext:py -f all                   # all fields
ev ext:py -f dates,meta            # default + date + metadata groups
```

Run `ev --help-fields` for the full list:

```
available fields (use with -f/--fields):

  * name                      file or folder name
  * path                      parent directory path
    full_path                 complete path including filename
    ext                       file extension (without dot)
  * size                      file size in bytes
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

groups:
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
everyfile 2026.04.15 (Python 3.13.5) / Everything 1.5.0.1404
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

`everyfile` is also a fully importable Python library — no CLI needed. The API uses DB-API 2.0 cursor/row semantics, is fully type-annotated, and has zero dependencies.

### Quick Start

```python
from everyfile import search, count

# Iterate results
for row in search("ext:py"):
    print(row.name, row.full_path)

# Count matches without fetching
print(f"Python files: {count('ext:py')}")
```

### Search with Options

```python
from everyfile import search

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
from everyfile import search

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
from everyfile import search

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
from everyfile import Everything

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
from everyfile import search, EverythingError

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
from everyfile import search

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
src/everyfile/
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

## Versioning

everyfile uses **CalVer** — `YYYY.M.D` (no leading zeros).

| Where | Example | Notes |
|-------|---------|-------|
| PyPI | `2026.4.18` | `pip install everyfile==2026.4.18` |
| Git tag | `v2026.4.18` | `git checkout v2026.4.18` |
| ClawHub | `2026.4.18` | `openclaw skills install everyfile@2026.4.18` |

Same-day patch releases append a pre-release suffix: `2026.4.18-2`, `2026.4.18-3`, etc.

### Release workflow

```powershell
# 1. Bump version in pyproject.toml
#    version = "2026.4.18"   (or "2026.4.18-2" for same-day patches)

# 2. Commit, tag, push
git add pyproject.toml
git commit -m "release: v2026.4.18"
git tag v2026.4.18
git push && git push --tags

# 3. Publish to PyPI
python -m build && twine upload dist/*

# 4. Publish to ClawHub
clawhub publish .agents/skills/everyfile --slug everyfile --version 2026.4.18
```

## Development

```powershell
git clone https://github.com/LouisGameDev/everyfile.git
cd everyfile
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

## Download History

[![Download History](https://skill-history.com/chart/louisgamedev/everyfile.svg)](https://skill-history.com/louisgamedev/everyfile)

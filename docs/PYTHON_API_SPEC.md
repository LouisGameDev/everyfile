# Python API Specification

> Public importable API for using `everything-cli` as a library — no CLI needed.

## Design Goals

1. **One-liner for common tasks** — `search("*.py")` just works
2. **Zero learning curve** — results use cursor/row semantics familiar from DB-API 2.0
3. **Full power when needed** — all Everything search modifiers accessible
4. **Lazy by default** — `Cursor` streams results; nothing materialised unless you ask
5. **Zero dependencies** — same stdlib-only constraint as the CLI
6. **Type-annotated** — `Row` has typed property accessors with full IDE autocomplete

## Import Surface

```python
# Primary API (95% of usage)
from everything_cli import search, count, Everything

# Types for annotation / error handling
from everything_cli import Cursor, Row, EverythingError
```

The public API lives in `everything_cli/__init__.py`.  
Internal modules (`sdk.*`, `output.*`, `util.*`) are **not** part of the public API.

---

## Quick Reference

| Want to…                         | Code                                                     |
|----------------------------------|----------------------------------------------------------|
| Search for files                 | `search("*.py")`                                         |
| Iterate results                  | `for row in search("*.py"): print(row.name)`             |
| Get first match                  | `search("*.py").fetchone()`                              |
| Batch read                       | `search("*.py").fetchmany(50)`                           |
| Materialise all                  | `search("*.py").fetchall()`                              |
| Limit results                    | `search("*.py", limit=10)`                               |
| Skip results                     | `search("*.py", offset=100)`                             |
| Sort by size descending          | `search("*.py", sort="size", descending=True)`           |
| Count matches                    | `count("*.py")`                                          |
| Request extra fields             | `search("*.py", fields="all")`                           |
| Use a specific instance          | `search("*.py", instance="1.5a")`                        |
| Reuse a connection               | `ev = Everything(); ev.search("*.py")`                   |
| Get Everything version           | `Everything().version`                                   |
| List running instances           | `Everything.instances()`                                  |

---

## 1. Module-Level Functions

### `search()`

```python
def search(
    query: str,
    *,
    fields: str | None = None,
    sort: str = "name",
    descending: bool = False,
    limit: int | None = None,
    offset: int = 0,
    match_case: bool = False,
    match_path: bool = False,
    match_whole_word: bool = False,
    regex: bool = False,
    instance: str | None = None,
) -> Cursor:
```

Execute an Everything search and return a `Cursor`.

**Parameters:**

| Parameter          | Type             | Default   | Description                                                      |
|--------------------|------------------|-----------|------------------------------------------------------------------|
| `query`            | `str`            | required  | Everything search expression (e.g. `"*.py"`, `"ext:rs size:>1mb"`) |
| `fields`           | `str \| None`    | `None`    | Comma-separated field names or group alias (see §4). `None` = default fields. |
| `sort`             | `str`            | `"name"`  | Sort field name (see §5). |
| `descending`       | `bool`           | `False`   | Reverse sort order. |
| `limit`            | `int \| None`    | `None`    | Max results to return. `None` = Everything's configured default. |
| `offset`           | `int`            | `0`       | Skip first N results (pagination). |
| `match_case`       | `bool`           | `False`   | Case-sensitive search. |
| `match_path`       | `bool`           | `False`   | Match query against full path (not just filename). |
| `match_whole_word` | `bool`           | `False`   | Match whole words only. |
| `regex`            | `bool`           | `False`   | Interpret query as regex. |
| `instance`         | `str \| None`    | `None`    | Everything instance name. `None` = auto-detect. |

**Returns:** `Cursor` — a forward-only iterable of `Row` objects (see §3).

**Raises:** `EverythingError` if Everything is not running or the IPC call fails.

**Example:**
```python
from everything_cli import search

for row in search("ext:py dm:today"):
    print(row.full_path, row.size)
```

---

### `count()`

```python
def count(
    query: str,
    *,
    match_case: bool = False,
    match_path: bool = False,
    match_whole_word: bool = False,
    regex: bool = False,
    instance: str | None = None,
) -> int:
```

Return the total number of Everything matches for a query, without fetching results.

**Example:**
```python
from everything_cli import count

print(f"Python files: {count('ext:py')}")
```

---

## 2. `Everything` Class

For repeated queries or service introspection, create an `Everything` instance to reuse the resolved connection.

```python
class Everything:
    def __init__(self, instance: str | None = None) -> None: ...

    def search(
        self,
        query: str,
        *,
        fields: str | None = None,
        sort: str = "name",
        descending: bool = False,
        limit: int | None = None,
        offset: int = 0,
        match_case: bool = False,
        match_path: bool = False,
        match_whole_word: bool = False,
        regex: bool = False,
    ) -> Cursor: ...

    def count(
        self,
        query: str,
        *,
        match_case: bool = False,
        match_path: bool = False,
        match_whole_word: bool = False,
        regex: bool = False,
    ) -> int: ...

    @property
    def version(self) -> dict: ...

    @property
    def info(self) -> dict: ...

    @property
    def instance_name(self) -> str: ...

    @staticmethod
    def instances() -> list[dict]: ...
```

**Constructor:**

| Parameter  | Type           | Default | Description                                       |
|------------|----------------|---------|---------------------------------------------------|
| `instance` | `str \| None`  | `None`  | Instance name (`"1.5a"`, `"1.4"`). `None` = auto-detect (env var → running instance). |

**Raises:** `EverythingError` if Everything is not running.

### Properties

| Property        | Type         | Description                                           |
|-----------------|--------------|-------------------------------------------------------|
| `version`       | `dict`       | `{"major": int, "minor": int, "revision": int, "build": int, "version": str, "instance": str}` |
| `info`          | `dict`       | Service info: indexed file/folder counts, etc.        |
| `instance_name` | `str`        | Resolved instance name (e.g. `"1.5a"`, `"default"`). |

### Static Methods

| Method        | Returns       | Description                         |
|---------------|---------------|-------------------------------------|
| `instances()` | `list[dict]`  | List all running Everything instances. Each dict: `{"name": str, "hwnd": int}`. |

---

## 3. `Cursor` and `Row`

### `Cursor`

Returned by `search()` and `Everything.search()`. Forward-only iterator following DB-API 2.0 conventions.

```python
class Cursor:
    total: int        # total matches in Everything DB (available immediately)
    count: int        # number of results in this cursor (respects limit/offset)

    def __iter__(self) -> Iterator[Row]: ...
    def __len__(self) -> int: ...                    # same as count
    def fetchone(self) -> Row | None: ...            # next result or None
    def fetchmany(self, size: int) -> list[Row]: ... # up to size results
    def fetchall(self) -> list[Row]: ...              # all remaining results
```

**Important:** `Cursor` is a **forward-only stream**. After full iteration, re-iterating yields nothing. Use `.fetchall()` if you need random access.

**Metadata is available immediately** (before iteration):
```python
cursor = search("*.py")
print(f"Found {cursor.total} total matches")  # works before iterating
```

**Batch reading:**
```python
cursor = search("ext:log", limit=1000)

# Read in batches of 100
while batch := cursor.fetchmany(100):
    process_batch(batch)
```

### `Row`

Each result from a `Cursor` is a `Row` — a thin typed wrapper over the raw result dict.

```python
class Row:
    # Typed property accessors (IDE autocomplete, type-checked)
    name: str
    path: str
    full_path: str
    ext: str | None
    size: int | None
    date_modified: str | None
    date_created: str | None
    date_accessed: str | None
    date_run: str | None
    date_recently_changed: str | None
    attributes: str | None
    run_count: int | None
    is_file: bool | None
    is_folder: bool | None
    hl_name: str | None
    hl_path: str | None
    hl_full_path: str | None

    # Raw dict access
    def get(self, key: str, default: Any = None) -> Any: ...
    def __getitem__(self, key: str) -> Any: ...
    def __contains__(self, key: str) -> bool: ...
    def keys(self) -> KeysView[str]: ...
    def to_dict(self) -> dict[str, Any]: ...
```

**Default fields** (`name`, `path`, `full_path`) are always present and return `str`.  
**Optional fields** return `T | None` — `None` when the field wasn't requested.

**Usage:**
```python
for row in search("*.py", fields="size"):
    # Typed access — IDE autocomplete works
    print(row.name)           # str
    print(row.size)           # int | None

    # Dict-style — for dynamic field access
    print(row["full_path"])
    print(row.get("size", 0))

    # Serialization
    print(row.to_dict())      # → {"name": ..., "path": ..., ...}
```

### Result Dict Schema

| Key                       | Type   | Default? | Description                          |
|---------------------------|--------|----------|--------------------------------------|
| `"name"`                  | `str`  | Yes      | File or folder name                  |
| `"path"`                  | `str`  | Yes      | Parent directory path                |
| `"full_path"`             | `str`  | Yes      | Full path including filename         |
| `"date_modified"`         | `str`  | Yes      | ISO 8601 UTC timestamp               |
| `"ext"`                   | `str`  | No       | Extension with dot prefix            |
| `"size"`                  | `int`  | No       | Size in bytes                        |
| `"date_created"`          | `str`  | No       | ISO 8601 UTC                         |
| `"date_accessed"`         | `str`  | No       | ISO 8601 UTC                         |
| `"date_run"`              | `str`  | No       | ISO 8601 UTC                         |
| `"date_recently_changed"` | `str`  | No       | ISO 8601 UTC                         |
| `"attributes"`            | `str`  | No       | Compact attribute string (`"RHA"`)   |
| `"run_count"`             | `int`  | No       | Times opened via Everything          |
| `"is_file"`               | `bool` | No       | `True` if file                       |
| `"is_folder"`             | `bool` | No       | `True` if folder                     |
| `"hl_name"`               | `str`  | No       | Highlighted filename                 |
| `"hl_path"`               | `str`  | No       | Highlighted path                     |
| `"hl_full_path"`          | `str`  | No       | Highlighted full path                |

---

## 4. Fields

The `fields` parameter accepts a comma-separated string of individual field names and/or group aliases.

### Field Groups

| Group         | Expands to                                                |
|---------------|-----------------------------------------------------------|
| `"default"`   | `name, path`                                              |
| `"all"`       | Every available field                                     |
| `"dates"`     | `date_created, date_modified, date_accessed`              |
| `"meta"`      | `size, ext, attributes, is_file, is_folder`               |
| `"highlight"` | `hl_name, hl_path, hl_full_path`                         |
| `"hl"`        | Same as `"highlight"`                                     |

**Note:** `name`, `path`, `full_path`, and `date_modified` are **always included** regardless of what you specify, matching CLI behaviour.

**Examples:**
```python
search("*.py", fields="meta")          # default + size, ext, attributes, is_file, is_folder
search("*.py", fields="all")           # every field
search("*.py", fields="size,ext")      # default + size + ext
search("*.py", fields="dates,meta")    # default + all dates + all meta
```

---

## 5. Sort Options

The `sort` parameter accepts a string name. Combined with `descending` for direction.

| Sort name            | Sorts by                |
|----------------------|-------------------------|
| `"name"`             | Filename                |
| `"path"`             | Parent path             |
| `"size"`             | File size               |
| `"ext"`              | Extension               |
| `"created"`          | Date created            |
| `"modified"`         | Date modified           |
| `"accessed"`         | Date accessed           |
| `"run-count"`        | Run count               |
| `"date-run"`         | Date last run           |
| `"recently-changed"` | Date recently changed   |
| `"attributes"`       | File attributes         |

**Example:**
```python
# Largest files first
search("ext:log", sort="size", descending=True, limit=20)
```

---

## 6. `EverythingError`

```python
class EverythingError(Exception):
    is_not_running: bool   # True if Everything service is not running
```

Raised when:
- Everything is not running (`is_not_running=True`)
- IPC communication fails (timeout, malformed response)
- Invalid instance name specified

**Example:**
```python
from everything_cli import search, EverythingError

try:
    cursor = search("*.py")
    for row in cursor:
        print(row.full_path)
except EverythingError as e:
    if e.is_not_running:
        print("Start Everything first!")
    else:
        print(f"Search failed: {e}")
```

---

## 7. Instance Management

Multiple Everything instances can run simultaneously (e.g. Everything 1.4 and 1.5a).

**Resolution priority** (same as CLI):
1. Explicit `instance=` parameter
2. `EVERYTHING_INSTANCE` environment variable
3. Auto-detect (prefers newest: 1.5a → 1.5 → 1.4 → default)

```python
# Auto-detect (most common)
search("*.py")

# Specific instance
search("*.py", instance="1.5a")

# Via environment (for scripts)
import os
os.environ["EVERYTHING_INSTANCE"] = "1.5a"
search("*.py")  # uses 1.5a

# List all running
from everything_cli import Everything
for inst in Everything.instances():
    print(inst["name"])
```

---

## 8. Internal Architecture

The public API is a thin layer on top of existing internals:

```
search() / count()              ← module-level convenience
    └── Everything              ← class with instance affinity
        └── EverythingAPI       ← internal SDK wrapper (sdk/api.py)
            └── ipc_query()     ← pure-Python ctypes IPC (sdk/ipc.py)
```

**What the public API adds over `sdk.api.EverythingAPI`:**
- String-based `sort` parameter (resolves `"modified"` → `SortType.DATE_MODIFIED_ASCENDING`)
- String-based `fields` parameter (resolves `"all"` → full field list)
- `Cursor` wrapper with `.total`, `.count`, `.fetchone()`, `.fetchmany()`, `.fetchall()`
- `Row` wrapper with typed property accessors + dict-style fallback
- `count()` function that fetches only the total without streaming results
- Module-level functions that don't require class instantiation
- Cleaner constructor (`instance=None` instead of sentinel `...`)

**What stays internal:**
- `SortType`, `RequestFlags` enums (users pass strings instead)
- `ipc_query()`, `ipc_get_version()`, `ipc_get_info()`
- `resolve_fields()`, `compute_request_flags()`
- All output formatting (`human.py`, `ndjson.py`)
- CLI arg parsing, pipe detection, filter/pick subcommands

---

## 9. Platform Behaviour

- **Windows:** Full functionality (IPC with Everything service)
- **Other OS:** `import everything_cli` succeeds, but `search()`/`count()` raise `EverythingError` with a clear message. This allows cross-platform code that conditionally uses Everything.

---

## 10. Future Work (Deferred)

- **Query builder** — `Query("*.py").ext("py").size_gt("1mb").modified_today()` compiles to search string
- **Async support** — `async search()` via `asyncio.to_thread()`
- **`pathlib.Path` helper** — `cursor.paths()` yielding `Path(row.full_path)`
- **Pagination helper** — `ev.paginate(query, page_size=1000)` auto-advances offset

# everyfile MCP Server — Design Spec

> MCP (Model Context Protocol) server exposing Voidtools Everything file search to AI assistants.
> Built on top of `everyfile`'s Python API.

---

## 1. Goals

| # | Goal | Detail |
|---|------|--------|
| 1 | **Instant file discovery for AI agents** | Let LLMs search the entire filesystem in milliseconds via Everything |
| 2 | **Thin wrapper over existing API** | All logic lives in `everyfile`; the MCP layer is just transport |
| 3 | **Minimal new dependencies** | Only add `mcp` (the official Python MCP SDK) as an optional dependency |
| 4 | **Composable** | Search results return structured data that agents can reason over |
| 5 | **Safe by default** | Read-only — no file mutations, no writes, no deletes |

---

## 2. Packaging

### Install target

```
pip install everyfile[mcp]
```

### `pyproject.toml` additions

```toml
[project.optional-dependencies]
mcp = ["mcp[cli]>=1.0"]
dev = ["pytest", "mypy"]

[project.scripts]
everyfile-mcp = "everyfile.mcp:main"
```

### Module location

```
src/everyfile/
  mcp.py              # MCP server entry point + tool definitions
```

Single file. The MCP layer is a thin adapter over `everyfile.api`.

---

## 3. Transport

- **Default:** stdio (launched by the AI client as a subprocess)
- **Entry point:** `everyfile-mcp` CLI command (or `python -m everyfile.mcp`)

### MCP client configuration (e.g. Claude Desktop, VS Code)

```json
{
  "mcpServers": {
    "everything": {
      "command": "everyfile-mcp"
    }
  }
}
```

Or if installed in a venv:

```json
{
  "mcpServers": {
    "everything": {
      "command": "python",
      "args": ["-m", "everyfile.mcp"]
    }
  }
}
```

---

## 4. Tools

### 4.1 `search_files`

Search the filesystem using Everything query syntax. Returns matching files/folders with metadata.

**Input Schema:**

| Parameter          | Type     | Required | Default   | Description |
|--------------------|----------|----------|-----------|-------------|
| `query`            | string   | **yes**  | —         | Everything search expression (e.g. `"*.py"`, `"ext:rs size:>1mb"`, `"dm:today"`) |
| `fields`           | string   | no       | `null`    | Comma-separated field names or group alias (`"all"`, `"meta"`, `"dates"`). Default = `name,path,full_path,date_modified` |
| `sort`             | string   | no       | `"name"`  | Sort field: `name`, `path`, `size`, `ext`, `created`, `modified`, `accessed`, `run-count`, `date-run`, `recently-changed`, `attributes` |
| `descending`       | boolean  | no       | `false`   | Reverse sort order |
| `max_results`      | integer  | no       | `200`     | Maximum number of results to return (capped at server-side max, see §6) |
| `offset`           | integer  | no       | `0`       | Skip first N results (pagination) |
| `match_case`       | boolean  | no       | `false`   | Case-sensitive search |
| `match_path`       | boolean  | no       | `false`   | Match against full path (not just filename) |
| `match_whole_word` | boolean  | no       | `false`   | Match whole words only |
| `regex`            | boolean  | no       | `false`   | Interpret query as regex |

**Output:** Text content containing NDJSON — one JSON object per line:

```json
{"name": "app.py", "path": "C:\\Dev", "full_path": "C:\\Dev\\app.py", "date_modified": "2025-03-01T14:22:31Z"}
{"name": "lib.py", "path": "C:\\Dev", "full_path": "C:\\Dev\\lib.py", "date_modified": "2025-03-01T10:15:00Z"}
```

Plus a summary line:

```
Found 2 results (of 1,247 total matches)
```

**Rationale for NDJSON:** Keeps output compact and parseable. Agents can reason over structured fields directly. Matches the CLI's existing output format.

---

### 4.2 `count_files`

Count matching files/folders without returning results. Useful for quick checks before deciding to fetch details.

**Input Schema:**

| Parameter          | Type     | Required | Default  | Description |
|--------------------|----------|----------|----------|-------------|
| `query`            | string   | **yes**  | —        | Everything search expression |
| `match_case`       | boolean  | no       | `false`  | Case-sensitive search |
| `match_path`       | boolean  | no       | `false`  | Match against full path |
| `match_whole_word` | boolean  | no       | `false`  | Match whole words only |
| `regex`            | boolean  | no       | `false`  | Interpret query as regex |

**Output:** Text content:

```
1,247 files/folders match "ext:py"
```

---

### 4.3 `get_everything_info`

Return Everything service status and version information. Useful for checking if Everything is running and what it has indexed.

**Input Schema:** *(no parameters)*

**Output:** Text content:

```
Everything v1.5.0.1383a (instance: "1.5a")
Indexed: 2,345,678 files, 456,789 folders (2,802,467 total)
```

---

### 4.4 `aggregate_files`

Aggregate file statistics server-side. Streams all matching rows internally (no result cap) and computes totals and optional grouping. Use for analytical questions like "how much space do my images use?" or "which extensions are biggest?".

**Input Schema:**

| Parameter          | Type     | Required | Default        | Description |
|--------------------|----------|----------|----------------|-------------|
| `query`            | string   | **yes**  | —              | Everything search expression |
| `group_by`         | string   | no       | `null`         | `"ext"` (file extension), `"folder"` (parent directory), `"root"` (drive letter), or null for flat totals |
| `top_n`            | integer  | no       | `20`           | Max groups to return (sorted by sort_by) |
| `sort_by`          | string   | no       | `"total_size"` | Sort groups by: `"count"`, `"total_size"`, `"avg_size"`, `"min_size"`, `"max_size"` |
| `match_case`       | boolean  | no       | `false`        | Case-sensitive search |
| `match_path`       | boolean  | no       | `false`        | Match against full path |
| `match_whole_word` | boolean  | no       | `false`        | Match whole words only |
| `regex`            | boolean  | no       | `false`        | Interpret query as regex |

**Output (flat, no grouping):**

```json
{"query": "ext:jpg;png", "total_count": 542585, "total_size": 411286099738}
```

**Output (grouped):**

```json
{
  "query": "ext:jpg;png",
  "total_count": 542585,
  "total_size": 411286099738,
  "group_by": "ext",
  "groups_total": 2,
  "groups": [
    {"key": ".jpg", "count": 159299, "total_size": 313052571018, "avg_size": 1965188, "min_size": 0, "max_size": 304323712},
    {"key": ".png", "count": 383286, "total_size": 53753168114, "avg_size": 140241, "min_size": 0, "max_size": 474547418}
  ]
}
```

**Group keys:**

| `group_by` | Key value |
|---|---|
| `"ext"` | Lowercased extension with dot (e.g. `".jpg"`, `".png"`) |
| `"folder"` | Parent directory path (e.g. `"C:\\Users\\Alice\\Photos"`) |
| `"root"` | Drive letter (e.g. `"C:"`, `"D:"`) |

---

## 5. Tool Behavior Details

### Result shape

Each result object in `search_files` output contains only the fields that were requested. Default fields when `fields` is null:

| Field           | Type   | Always present |
|-----------------|--------|----------------|
| `name`          | string | yes            |
| `path`          | string | yes            |
| `full_path`     | string | yes            |
| `size`          | int    | yes (default)  |
| `date_modified` | string | yes (default)  |

When `fields="all"` is requested, all available fields are included:

| Field                    | Type   |
|--------------------------|--------|
| `name`                   | string |
| `path`                   | string |
| `full_path`              | string |
| `ext`                    | string |
| `size`                   | int    |
| `date_created`           | string |
| `date_modified`          | string |
| `date_accessed`          | string |
| `date_run`               | string |
| `date_recently_changed`  | string |
| `attributes`             | string |
| `run_count`              | int    |
| `is_file`                | bool   |
| `is_folder`              | bool   |

### Error handling

Errors are returned as MCP tool errors (not exceptions in the output):

| Condition | Error message |
|-----------|---------------|
| Everything not running | `"Everything is not running. Please start Voidtools Everything and try again."` |
| IPC failure | `"IPC communication failed: {detail}"` |
| Invalid field name | `"Unknown field '{name}'. Valid fields: ..."` |
| Invalid sort field | `"Unknown sort field '{name}'. Valid: ..."` |

---

## 6. Safety & Limits

| Concern | Mitigation |
|---------|------------|
| **Read-only** | No tool can create, modify, or delete files. Everything itself is read-only. |
| **Result cap** | `search_files`: `max_results` capped at **10,000**, default **200**. `aggregate_files`: no result cap (streams internally, returns only summaries). |
| **No file content** | Results include metadata only (paths, sizes, dates). File contents are never read or returned. |
| **No path traversal** | Everything operates on its own index. No user-supplied paths are resolved or opened. |
| **Instance isolation** | If multiple Everything instances run, each MCP server connects to one (auto-detected or configured). |

---

## 7. Example Conversations

### "Find all Python files modified today"

```
Agent → search_files(query="ext:py dm:today", sort="modified", descending=true)
```

### "How many Rust files are in my workspace?"

```
Agent → count_files(query="ext:rs parent:C:\\Dev\\myproject")
```

### "Find the largest log files"

```
Agent → search_files(query="ext:log", fields="name,full_path,size", sort="size", descending=true, max_results=20)
```

### "Is Everything running?"

```
Agent → get_everything_info()
```

### "How much disk space do my images use?"

```
Agent → aggregate_files(query="ext:jpg;png;gif;webp;heic;svg")
→ {total_count: 657727, total_size: 411286099738}
```

### "Break down image space by extension"

```
Agent → aggregate_files(query="ext:jpg;png;gif;webp;heic;svg", group_by="ext", sort_by="total_size")
→ groups sorted by total size, top 20
```

### "Which drive has the most images?"

```
Agent → aggregate_files(query="ext:jpg;png;gif", group_by="root")
→ [{key: "F:", count: 289921, total_size: ...}, ...]
```

### "Which formats are heaviest per file?"

```
Agent → aggregate_files(query="ext:jpg;png;gif;raw;nef;tif", group_by="ext", sort_by="avg_size")
→ groups sorted by average file size
```

---

## 8. Future Considerations (Not in v1)

| Feature | Notes |
|---------|-------|
| **Resources** | Expose search results as `file://` resources for direct file reading by the client. Blocked on deciding scope/security model. |
| **Prompts** | Pre-built prompt templates (e.g. "find duplicates", "disk usage by extension"). Low priority — agents can compose queries directly. |
| **SSE transport** | For remote/multi-client setups. stdio is sufficient for local use. |
| **Streaming results** | MCP supports streaming; could yield results incrementally for very large result sets. |
| **File content reading** | Optionally read file contents for matched results. Security implications need careful design. |

---

## 9. Implementation Skeleton

```python
"""everyfile MCP server."""

from mcp.server.fastmcp import FastMCP

from everyfile import Everything, EverythingError

mcp = FastMCP(
    "everything",
    description="Search files instantly on Windows via Voidtools Everything",
)

MAX_RESULTS_CAP = 10_000
DEFAULT_MAX_RESULTS = 200


@mcp.tool()
def search_files(
    query: str,
    fields: str | None = None,
    sort: str = "name",
    descending: bool = False,
    max_results: int = DEFAULT_MAX_RESULTS,
    offset: int = 0,
    match_case: bool = False,
    match_path: bool = False,
    match_whole_word: bool = False,
    regex: bool = False,
) -> str:
    """Search for files and folders using Everything query syntax.

    Uses Voidtools Everything's instant search to find files across all
    indexed drives. Supports Everything's full query syntax including:
    - Wildcards: *.py, foo*.txt
    - Extensions: ext:py, ext:rs|go
    - Size filters: size:>1mb, size:<100kb
    - Date filters: dm:today, dm:thisweek, dc:2024
    - Path filters: parent:C:\\Dev, path:src
    - Boolean: foo bar (AND), foo|bar (OR), !foo (NOT)
    - Content search: content:"TODO"
    - Duplicates: dupe:
    - Regex: Use regex=True
    """
    limit = min(max_results, MAX_RESULTS_CAP)
    ev = Everything()
    cursor = ev.search(
        query,
        fields=fields,
        sort=sort,
        descending=descending,
        limit=limit,
        offset=offset,
        match_case=match_case,
        match_path=match_path,
        match_whole_word=match_whole_word,
        regex=regex,
    )
    import json
    lines = [json.dumps(row.to_dict(), ensure_ascii=False) for row in cursor]
    lines.append(f"\nFound {cursor.count} results (of {cursor.total:,} total matches)")
    return "\n".join(lines)


@mcp.tool()
def count_files(
    query: str,
    match_case: bool = False,
    match_path: bool = False,
    match_whole_word: bool = False,
    regex: bool = False,
) -> str:
    """Count files/folders matching an Everything query without returning results.

    Useful for quickly checking how many matches exist before fetching details.
    Supports the same query syntax as search_files.
    """
    ev = Everything()
    total = ev.count(
        query,
        match_case=match_case,
        match_path=match_path,
        match_whole_word=match_whole_word,
        regex=regex,
    )
    return f'{total:,} files/folders match "{query}"'


@mcp.tool()
def get_everything_info() -> str:
    """Get Everything service status, version, and index statistics.

    Returns version info and the number of indexed files/folders.
    Useful for checking if Everything is running and healthy.
    """
    ev = Everything()
    version = ev.version
    info = ev.info
    v = version["version"]
    inst = version.get("instance", "default")
    total = info.get("total_files", 0) + info.get("total_folders", 0)
    return (
        f'Everything v{v} (instance: "{inst}")\n'
        f'Indexed: {info.get("total_files", 0):,} files, '
        f'{info.get("total_folders", 0):,} folders ({total:,} total)'
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
```

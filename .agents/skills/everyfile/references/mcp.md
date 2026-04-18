# everyfile — MCP Tools Reference

Three MCP tools for instant file search via Voidtools Everything.
Available when the `everything` MCP server is configured.

## Setup

```jsonc
// In your MCP client config (VS Code mcp.json, Claude Desktop, etc.)
{
  "mcpServers": {
    "everything": {
      "command": "everyfile-mcp"
    }
  }
}
```

Requires: `pip install everyfile[mcp]`

## Tools

### `search_files` — Search for files and folders

Returns NDJSON results + summary line.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | *required* | Everything search expression |
| `fields` | str \| null | default set | Comma-separated: `name,path,full_path,ext,size,date_created,date_modified,date_accessed,attributes,is_file,is_folder,run_count`. Groups: `all`, `meta`, `dates`, `highlight` |
| `sort` | str | `"name"` | `name` `path` `size` `ext` `created` `modified` `accessed` `run-count` `date-run` `recently-changed` `attributes` |
| `descending` | bool | false | Reverse sort order |
| `max_results` | int | 200 | Capped at 10,000 |
| `offset` | int | 0 | Pagination offset |
| `match_case` | bool | false | Case-sensitive |
| `match_path` | bool | false | Match against full path, not just filename |
| `match_whole_word` | bool | false | Whole words only |
| `regex` | bool | false | Interpret query as regex |

### `count_files` — Count matches without fetching

Returns a single line: `"N files/folders match "query""`. Use to gauge result scale before searching.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | *required* | Everything search expression |
| `match_case` | bool | false | Case-sensitive |
| `match_path` | bool | false | Match full path |
| `match_whole_word` | bool | false | Whole words only |
| `regex` | bool | false | Regex mode |

### `get_everything_info` — Service diagnostics

No parameters. Returns version, instance name, admin status, AppData status.

### `aggregate_files` — Server-side analytics

Streams all matching rows internally and computes aggregates in-process.
No result cap — handles millions of files. Use for analytical questions
("how much space?", "which extensions are biggest?", "which folders?").

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | *required* | Everything search expression |
| `group_by` | str \| null | null | `"ext"` (extension), `"folder"` (parent dir), `"root"` (drive letter), or null for flat totals |
| `top_n` | int | 20 | Max groups returned (sorted by sort_by) |
| `sort_by` | str | `"total_size"` | `"count"` or `"total_size"` |
| `match_case` | bool | false | Case-sensitive |
| `match_path` | bool | false | Match full path |
| `match_whole_word` | bool | false | Whole words only |
| `regex` | bool | false | Regex mode |

**Returns (flat):** `{total_count, total_size}`

**Returns (grouped):** `{total_count, total_size, group_by, groups_total, groups: [{key, count, total_size, avg_size, min_size, max_size}, ...]}`

## When to use which tool

| Question pattern | Tool |
|---|---|
| "How many X files?" (just a count) | `count_files` — O(1), instant |
| "Show me the 20 biggest log files" | `search_files` — returns rows |
| "How much disk space do images use?" | `aggregate_files` — flat, no group_by |
| "Which extensions use the most space?" | `aggregate_files` — `group_by="ext"` |
| "Break down images by drive" | `aggregate_files` — `group_by="root"` |
| "Which folders have the most images?" | `aggregate_files` — `group_by="folder"` |
| "Drill into F:\ images by subfolder" | `aggregate_files` — add `parent:F:\` to query, `group_by="folder"` |

## Search Syntax Quick Reference

```
Operators:    space=AND  |=OR  !=NOT  " "=exact phrase
Wildcards:    *=any  ?=single char
Functions:    ext:py  size:>1mb  dm:today  dc:thisweek  parent:C:\Dev
              content:"TODO"  dupe:  depth:  len:  child:
Macros:       audio:  video:  doc:  pic:  zip:  exe:
Size:         size:1kb..10mb  size:>1gb  size:empty
Dates:        dm:today  dm:thisweek  dc:yesterday  da:last2weeks
```

## Complex Examples

### Find large recently modified files
```
search_files(query="ext:py size:>50kb dm:thisweek", sort="size", descending=true, max_results=20, fields="name,full_path,size,date_modified")
```

### Scope to a directory (use path: function in query)
```
search_files(query="path:everything-cli ext:py", sort="modified", descending=true, max_results=30)
```

### Regex: find test files
```
search_files(query="regex:^test_.*\.py$", sort="modified", descending=true, fields="name,full_path")
```
Note: use `regex:` prefix in the query. The `regex=true` flag is equivalent but the prefix is simpler.

### Count before searching
```
count_files(query="ext:log size:>100mb")
→ "847 files/folders match "ext:log size:>100mb""

# If reasonable, fetch:
search_files(query="ext:log size:>100mb", sort="size", descending=true, max_results=20, fields="name,full_path,size")
```

### Find duplicate DLLs
```
search_files(query="dupe: ext:dll", sort="name", max_results=50, fields="name,full_path,size")
```

### Content search
```
search_files(query='ext:py content:"async def"', max_results=30, fields="name,full_path")
```

### Paginate through results
```
search_files(query="ext:rs", max_results=50, offset=0)   # page 1
search_files(query="ext:rs", max_results=50, offset=50)  # page 2
```

### Zero-byte files
```
search_files(query="size:empty ext:py|ext:js", fields="name,full_path")
```

### Check service health
```
get_everything_info()
→ Everything v1.5.0.1404 (instance: "1.5a")
  Running as admin: no
  Using AppData: no
```

## Tips

- Default `max_results` is 200. Increase for bulk operations, but cap at 10,000.
- Use `count_files` first when you're unsure how many matches to expect.
- Use `aggregate_files` for any "how much?" or "what's the distribution?" question — it handles millions of files in seconds with no pagination.
- To drill down by folder, narrow the query with `parent:` and use `group_by="folder"` — each call shows one level of the tree.
- Use `path:dirname` in the query to scope results to a directory. The `match_path` flag makes the *filename query* match against the full path — it's rarely needed.
- `sort="modified"` + `descending=true` gives most recently changed first.
- All tools are read-only — safe to call without confirmation.

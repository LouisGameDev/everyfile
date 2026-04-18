---
name: everyfile
description: >
  Use the everyfile (ev) command, Python API, or MCP tools to search files
  instantly on Windows via Voidtools Everything. Use when the user asks to "find
  files", "search for files", "locate a file", "list files by extension", "find
  large files", "find recent files", "find duplicates", or any file discovery
  task on Windows. Also use for programmatic file search from Python code or
  AI assistant tool calls. Do NOT use for Linux/macOS file search or when
  Everything is not installed.
license: MIT
compatibility: >
  Requires Windows, Python >= 3.11, and Voidtools Everything (1.4, 1.5, or 1.5a)
  running in the background.
metadata:
  author: LouisGameDev
  version: "2026.04.18"
---

# everyfile

Instant file search on Windows via [Voidtools Everything](https://www.voidtools.com/).
Three interfaces — choose based on context:

| Interface | When to use | Reference |
|-----------|-------------|-----------|
| **CLI** (`ev`) | Terminal commands, shell scripts, piping results between commands | [cli.md](references/cli.md) |
| **Python API** | Python scripts/tools that need programmatic file search, Cursor/Row iteration | [api.md](references/api.md) |
| **MCP Tools** | AI assistants calling `search_files`, `count_files`, `aggregate_files`, `get_everything_info` via MCP | [mcp.md](references/mcp.md) |

For Everything search syntax details beyond this cheat sheet, see the scraped SDK docs in [everything-sdk/](references/everything-sdk/) (especially [everything-sdk/index.md](references/everything-sdk/index.md) for search syntax and [everything-sdk/ipc.md](references/everything-sdk/ipc.md) for IPC internals).

## Decision Guide

- **User asks to find/list files in terminal** → CLI (`ev`)
- **User writes a Python script that needs file search** → API (`from everyfile import search`)
- **You (the agent) need to find files on Windows** → MCP tools (`search_files`, `count_files`)
- **User asks "how many X files?"** → MCP `count_files` or CLI `ev --count`
- **User asks "how much space?" / "what's the distribution?"** → MCP `aggregate_files`
- **User asks "break down by extension/folder/drive"** → MCP `aggregate_files` with `group_by`
- **User asks for file contents after search** → CLI `ev -l | ForEach-Object { ... }` or API iteration
- **User asks about Everything status** → MCP `get_everything_info` or CLI `ev --info`

## Install

```powershell
pip install everyfile          # CLI + API
pip install everyfile[mcp]     # + MCP server
```

## Search Syntax (shared across all interfaces)

### Operators & Wildcards
```
space   AND       |   OR        !   NOT      < >   grouping     " "  exact phrase
*   zero or more chars (matches whole filename by default)
?   one char
```

### Modifiers — prefix any term or function
```
Filename matching:
  exact:  wfn:  wholefilename:      match whole filename ← use before regex for exact names
  nowfn:  nowholefilename:          match anywhere in filename
  path:   nopath:                   match full path vs filename only
  wildcards:  nowildcards:          enable/disable wildcard expansion

Files/folders:
  file:  files:                     files only
  folder:  folders:                 folders only

Case / encoding:
  case:  nocase:                    case-sensitive / insensitive
  diacritics:  nodiacritics:        match/ignore accent marks
  ascii:  utf8:  noascii:           fast ASCII case comparisons

Word / regex:
  ww:  wholeword:  noww:  nowholeword:   whole words only
  regex:  noregex:                       enable/disable regex
```

### Functions
```
Extension / type:
  ext:<ext>              ext:py   ext:py;js;ts  (semicolon OR list)
  type:<type>            file type description string

Paths:
  parent:<path>          in path, including subfolders
  infolder:<path>        in path, NO subfolders  (alias: nosubfolders:<path>)
  depth:<n>              folder depth from drive root
  root:                  items with no parent folder (drive roots)
  shell:<name>           known shell folder (Desktop, Downloads, Documents…)
  child:<name>           folders containing a matching child
  childcount:<n>         folders with n total children
  childfilecount:<n>     folders with n files
  childfoldercount:<n>   folders with n subfolders

Size:
  size:<size>            size:>1mb  size:2mb..10mb
  size words: empty  tiny  small  medium  large  huge  gigantic

Dates (all share same value syntax):
  dm:   datemodified:     dc:  datecreated:
  da:   dateaccessed:     dr:  daterun:
  rc:   recentchange:
  Constants: today  yesterday
    <last|past|prev|this|current|next><year|month|week>
    last<n><years|months|weeks|days|hours|minutes|seconds>
    january..december  jan..dec  sunday..saturday  sun..sat  unknown

Attributes:
  attrib:<flags>    A=archive  C=compressed  D=dir  E=encrypted  H=hidden
                    I=not-indexed  L=reparse  N=normal  O=offline  P=sparse
                    R=readonly  S=system  T=temp

Duplicates:
  dupe:          same filename       namepartdupe:  same name (no ext)
  sizedupe:      same size           dmdupe:        same date modified
  dcdupe:        same date created   dadupe:        same date accessed
  attribdupe:    same attributes

Filename text:
  startwith:<text>         filename starts with
  endwith:<text>           filename ends with
  len:<n>                  filename character length

Miscellaneous:
  empty:                   empty folders
  count:<n>                limit results to n
  runcount:<n>             Everything run count
  filelist:<a|b|c>         pipe-delimited filename list
  filelistfilename:<file>  load list from file
  frn:<list>               semicolon-delimited File Reference Numbers
  fsi:<index>              internal file system index

Content search (slow — narrow with other filters first!):
  content:<text>           via iFilter, falls back to UTF-8
  ansicontent:  utf8content:  utf16content:  utf16becontent:

Images (slow): width:<px>  height:<px>  dimensions:<w>x<h>  orientation:landscape|portrait  bitdepth:<n>
ID3/FLAC (slow): title:  artist:  album:  genre:  track:  year:  comment:
```

### Value / range syntax
```
fn:value      fn:=value    fn:>value    fn:>=value    fn:<value    fn:<=value
fn:start..end   (range, inclusive)     fn:start-end  (alternative range)
```

### Built-in macros
```
File groups:    audio:  video:  doc:  pic:  zip:  exe:
Literal chars:  quot:"  apos:'  amp:&  lt:<  gt:>  #<n>:  #x<n>:  (unicode dec/hex)
```

### Key examples
```
exact:env.json                           exact filename (not substring)
ext:py;js;ts                             multiple extensions
ext:py dm:thisweek size:>10kb            AND combination
parent:C:\Dev\myproject                  in folder (+ subfolders)
infolder:C:\Dev\myproject                in folder only, no subfolders
sizedupe: ext:mp4 size:>1gb             large duplicate videos
ext:py content:"TODO"                   content search (slow)
attrib:H                                 hidden files
dm:last7days size:>1mb                   modified last 7 days
startwith:test_ ext:py                   files starting with test_
```

## Safety

- Confirm with the user before piping results into destructive commands
- Use count first (`count_files` / `ev --count` / `count()`) to check scale before bulk operations
- Use `limit`/`-n`/`max_results` when testing queries
- Everything must be running — all interfaces error if it's not

"""everything-cli entry point — flat, grep-like CLI for Everything search."""

from __future__ import annotations

import argparse
import platform
import sys
import textwrap

from .filter import FilterConfig, run_filter
from .pick import run_pick
from .search import run_count, run_info, run_instances, run_pipe_filter, run_search, run_version

_EPILOG = textwrap.dedent("""\
    search syntax (passed verbatim to Everything):
      Operators:   space=AND  |=OR  !=NOT  < >=group  " "=exact phrase
      Wildcards:   *=any chars  ?=one char
      Functions:   ext:py  size:>1mb  dm:today  parent:C:\\Dev  content:TODO
                   dc: da: dr: rc: depth: len: dupe: child: childcount:
      Modifiers:   case: nocase: regex: path: ww: file: folder:
      Macros:      audio: video: doc: pic: zip: exe:
      Size:        size:1kb..10mb  size:>1gb  size:empty  size:tiny..huge
      Dates:       dm:today  dm:thisweek  dc:yesterday  da:last2weeks

    output modes:
      (default)    human-readable table on stderr + NDJSON on stdout when piped
      -j/--json    force NDJSON to stdout even on a terminal
      -l/--list    newline-separated full paths (for ForEach-Object, etc.)
      -0/--null    null-separated full paths (for paths with special characters)
      -q/--quiet   suppress all stderr output

    sorting:
      Default sort is modified-date descending (newest first), so -n 5
      gives the 5 most recently modified matches. Override with --sort.

    instance selection:
      Multiple Everything versions can run side-by-side (e.g. 1.4 and 1.5a).
      The CLI auto-detects instances in priority order: 1.5a → 1.5 → 1.4 → default.
      Override with --instance or the $EVERYTHING_INSTANCE environment variable:

        ev --instances                          list running instances
        ev --instance 1.4 ext:py                query via Everything 1.4
        $env:EVERYTHING_INSTANCE = "1.5a"       persist for session

      Priority: --instance flag > $EVERYTHING_INSTANCE > auto-detect.

    pipe composition:
      When stdin is piped NDJSON, ev automatically switches to local
      filter mode instead of querying Everything:
        ev ext:py | ev "path:src"        filter by path
        ev ext:py | ev "name:test"       filter by name
        ev ext:py | ev "!__pycache__"    exclude results
      Use -S/--search to force an Everything query with piped input.
      When stdout is piped, stderr is silenced automatically.

    columns & fields:
      --columns controls the human-readable stderr display.
      -f/--fields controls which fields appear in NDJSON output.
      Run ev --help-columns for the full list of available names and groups.

      Defaults:  --columns name,path,date_modified
                 -f        name,path,full_path,date_modified

        ev ext:py --columns name,size        compact display
        ev ext:py -f all                     all fields in NDJSON
        ev ext:py -f dates,meta              default + date + metadata fields

    using results with other commands:
      Open in VS Code:      code $(ev myfile.py -n 1 -l)
      Open in editor:       notepad $(ev myconfig -n 1 -l)
      Delete temp files:    ev ext:tmp -l | ForEach-Object { Remove-Item $_ }
      Open all matches:     ev ext:py -l | ForEach-Object { code $_ }
      Select a range:       ev ext:py -l | Select-Object -Skip 5 -First 3
      Count matches:        (ev ext:py -l | Measure-Object).Count
      Chain filters:        ev ext:py | ev "path:src" | ev "!test"

    examples:
      ev ext:py dm:thisweek            recent Python files
      ev ext:py -n 10                  10 most recently modified .py files
      ev ext:py --sort size --desc     largest Python files first
      ev "*.rs" -c -r                  case-sensitive regex search
      ev --count ext:py                just the count
      ev ext:py -l | Measure-Object -Line    count matching files
      ev ext:py -f all | ev filter --size-gt 5000
      ev ext:py -f all | ev pick full_path size
""")

_SORT_CHOICES = [
    "name", "path", "size", "ext", "created", "modified",
    "accessed", "run-count", "date-run", "recently-changed", "attributes",
]

# Column/field descriptions for --help-columns
_COLUMN_DESCRIPTIONS: dict[str, str] = {
    "name":                   "file or folder name",
    "path":                   "parent directory path",
    "full_path":              "complete path including filename",
    "ext":                    "file extension (without dot)",
    "size":                   "file size in bytes",
    "date_created":           "creation timestamp",
    "date_modified":          "last modified timestamp",
    "date_accessed":          "last accessed timestamp",
    "date_run":               "last run timestamp",
    "date_recently_changed":  "recently changed timestamp",
    "run_count":              "number of times file was executed",
    "attributes":             "file system attributes string",
    "is_file":                "true if result is a file (derived)",
    "is_folder":              "true if result is a folder (derived)",
    "hl_name":                "highlighted matching name",
    "hl_path":                "highlighted matching path",
    "hl_full_path":           "highlighted matching full path",
}

_GROUP_DESCRIPTIONS: dict[str, str] = {
    "default":   "name, path",
    "all":       "every available column",
    "dates":     "date_created, date_modified, date_accessed",
    "meta":      "size, ext, attributes, is_file, is_folder",
    "hl":        "hl_name, hl_path, hl_full_path",
}


def _print_columns_help() -> None:
    """Print available columns/fields reference to stderr."""
    from .output.human import DEFAULT_COLUMNS
    lines = [
        "available columns (use with --columns and -f/--fields):",
        "",
    ]
    for col, desc in _COLUMN_DESCRIPTIONS.items():
        marker = "  *" if col in DEFAULT_COLUMNS else "   "
        lines.append(f"{marker} {col:<25s} {desc}")
    lines.append("")
    lines.append("  * = included in default --columns display")
    lines.append("")
    lines.append("groups (use with -f/--fields):")
    lines.append("")
    for group, desc in _GROUP_DESCRIPTIONS.items():
        lines.append(f"    {group:<12s} {desc}")
    lines.append("")
    lines.append("examples:")
    lines.append(f"  ev ext:py --columns name,size,date_modified")
    lines.append(f"  ev ext:py -f all                              # all fields in NDJSON")
    lines.append(f"  ev ext:py -f dates,size                       # default + dates + size")
    lines.append(f"  ev ext:py --columns name,path,size -f meta    # custom display + NDJSON fields")
    print("\n".join(lines), file=sys.stderr)

def _build_main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="everything",
        description="Search files instantly with Voidtools Everything.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Mode flags
    parser.add_argument("--version", action="store_true", help="show version info and exit")
    parser.add_argument("--info", action="store_true", help="show Everything service status and exit")
    parser.add_argument("--count", action="store_true", help="print only the result count as JSON")
    parser.add_argument("--instances", action="store_true",
                        help="list running Everything instances and exit")
    parser.add_argument("--help-columns", action="store_true",
                        help="list available column/field names and exit")

    # Instance selection
    parser.add_argument("--instance", metavar="NAME", default=None,
                        help="target a specific Everything instance (e.g. 1.5a, 1.4, default). "
                             "Overrides $EVERYTHING_INSTANCE env var")

    # Search modifiers
    parser.add_argument("-c", "--case", action="store_true", help="case-sensitive search")
    parser.add_argument("-p", "--path", action="store_true", help="match against full path")
    parser.add_argument("-w", "--whole-word", action="store_true", help="match whole words only")
    parser.add_argument("-r", "--regex", action="store_true", help="enable regex search")

    # Pagination
    parser.add_argument("-n", "--max", type=int, default=None, metavar="N", help="max results to return")
    parser.add_argument("--offset", type=int, default=0, metavar="N", help="skip first N results")

    # Sort
    parser.add_argument("-s", "--sort", choices=_SORT_CHOICES, default=None, metavar="FIELD", help="sort field")
    parser.add_argument("-d", "--desc", action="store_true", help="descending sort order")

    # Fields
    parser.add_argument("-f", "--fields", default=None, metavar="F1,F2,...",
                        help="comma-separated NDJSON fields (or: default, all, dates, meta, hl)")

    # Display columns (human-readable stderr output)
    parser.add_argument("--columns", default=None, metavar="C1,C2,...",
                        help="columns for human-readable stderr output (default: name,path,date_modified)")

    # Output
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress stderr output (NDJSON only)")
    parser.add_argument("-j", "--json", action="store_true",
                        help="force NDJSON to stdout even when interactive (auto when piped)")
    parser.add_argument("-l", "--list", action="store_true",
                        help="output newline-separated full paths (for ForEach-Object, etc.)")
    parser.add_argument("-0", "--null", action="store_true",
                        help="like --list but null-separated (for paths with special characters)")
    parser.add_argument("-S", "--search", action="store_true",
                        help="force Everything search even when stdin is piped")

    # Query (all remaining positional args)
    parser.add_argument("query", nargs="*", help="Everything search query")

    return parser


def _build_filter_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="everything filter",
        description="Filter NDJSON records from stdin.",
    )
    parser.add_argument("--name", metavar="GLOB", help="glob match on name field")
    parser.add_argument("--path", metavar="GLOB", help="glob match on path field")
    parser.add_argument("--ext", metavar=".EXT", help="exact extension match")
    parser.add_argument("--size-gt", type=int, metavar="N", help="size greater than N bytes")
    parser.add_argument("--size-lt", type=int, metavar="N", help="size less than N bytes")
    parser.add_argument("--modified-after", metavar="DATE", help="modified after ISO date")
    parser.add_argument("--modified-before", metavar="DATE", help="modified before ISO date")
    parser.add_argument("--created-after", metavar="DATE", help="created after ISO date")
    parser.add_argument("--created-before", metavar="DATE", help="created before ISO date")
    parser.add_argument("--is-file", action="store_true", help="only files")
    parser.add_argument("--is-folder", action="store_true", help="only folders")
    parser.add_argument("--attr", metavar="CHARS", help="require all attribute chars (e.g. RHA)")
    return parser


def _build_pick_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="everything pick",
        description="Extract fields from NDJSON records on stdin.",
    )
    parser.add_argument("fields", nargs="+", help="field names to extract")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]

    # Platform check — Everything is Windows-only
    # (filter/pick subcommands work anywhere since they process stdin NDJSON)
    needs_ipc = not (args and args[0] in ("filter", "pick"))
    if needs_ipc and platform.system() != "Windows":
        print(
            "everything: error: Everything search requires Windows.\n"
            "  Voidtools Everything is a Windows-only application.\n"
            "  The 'filter' and 'pick' subcommands work on any platform\n"
            "  (they process NDJSON from stdin).",
            file=sys.stderr,
        )
        sys.exit(2)

    # Detect subcommands by checking first positional arg
    if args and args[0] == "filter":
        parser = _build_filter_parser()
        ns = parser.parse_args(args[1:])
        config = FilterConfig(
            name_glob=ns.name,
            path_glob=ns.path,
            ext=ns.ext,
            size_gt=ns.size_gt,
            size_lt=ns.size_lt,
            modified_after=ns.modified_after,
            modified_before=ns.modified_before,
            created_after=ns.created_after,
            created_before=ns.created_before,
            is_file=ns.is_file,
            is_folder=ns.is_folder,
            attr_chars=ns.attr,
        )
        sys.exit(run_filter(config))

    if args and args[0] == "pick":
        parser = _build_pick_parser()
        ns = parser.parse_args(args[1:])
        sys.exit(run_pick(ns.fields))

    # Default: search mode
    parser = _build_main_parser()
    ns = parser.parse_args(args)

    # Resolve instance from --instance flag (env var handled inside API)
    inst = ns.instance

    # Mode flags (no query needed)
    if ns.instances:
        emit_json = ns.json or not sys.stdout.isatty()
        sys.exit(run_instances(instance=inst, emit_json=emit_json))
    if ns.help_columns:
        _print_columns_help()
        sys.exit(0)
    if ns.version:
        sys.exit(run_version(instance=inst))
    if ns.info:
        emit_json = ns.json or not sys.stdout.isatty()
        sys.exit(run_info(emit_json=emit_json, instance=inst))

    # Join positional args into query string
    query = " ".join(ns.query)

    if ns.count:
        stdout_piped_c = not sys.stdout.isatty()
        emit_json = ns.json or stdout_piped_c
        sys.exit(run_count(
            query,
            match_case=ns.case,
            match_path=ns.path,
            match_whole_word=ns.whole_word,
            regex=ns.regex,
            quiet=ns.quiet or stdout_piped_c,
            emit_json=emit_json,
            instance=inst,
        ))

    if not query:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Parse --columns into a list
    columns = None
    if ns.columns:
        columns = [c.strip() for c in ns.columns.split(",") if c.strip()]

    # Pipe composition: if stdin is piped NDJSON (and not --search), filter locally
    stdin_piped = not sys.stdin.isatty()
    stdout_piped = not sys.stdout.isatty()

    # --list / --null → plain path output
    list_sep: str | None = None
    if getattr(ns, 'null', False):
        list_sep = "\0"
    elif getattr(ns, 'list', False):
        list_sep = "\n"

    # When piping out, silence stderr (quiet) — only data flows through
    quiet = ns.quiet or (stdout_piped and list_sep is None)

    if stdin_piped and not ns.search:
        emit_json = (ns.json or stdout_piped) and list_sep is None
        sys.exit(run_pipe_filter(
            query,
            columns=columns,
            max_results=ns.max,
            offset=ns.offset,
            quiet=quiet,
            emit_json=emit_json,
            list_sep=list_sep,
        ))

    # Determine whether to emit NDJSON: always when piped, only with --json on TTY
    emit_json = (ns.json or stdout_piped) and list_sep is None

    sys.exit(run_search(
        query,
        fields_spec=ns.fields,
        columns=columns,
        sort_name=ns.sort,
        descending=ns.desc,
        max_results=ns.max,
        offset=ns.offset,
        match_case=ns.case,
        match_path=ns.path,
        match_whole_word=ns.whole_word,
        regex=ns.regex,
        quiet=quiet,
        emit_json=emit_json,
        list_sep=list_sep,
        instance=inst,
    ))


if __name__ == "__main__":
    main()

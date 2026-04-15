"""Pure Python IPC client for Everything via WM_COPYDATA.

Talks directly to Everything's hidden notification window, bypassing the
SDK DLL entirely.  Supports both Everything 1.4 (default instance) and
1.5a (named instance) via the instance-name suffix convention.

Protocol summary (IPC2 – Unicode):
  1. Find Everything's hidden window: class "EVERYTHING_TASKBAR_NOTIFICATION"
     (or "EVERYTHING_TASKBAR_NOTIFICATION_(<instance>)" for named instances).
  2. Create our own hidden window to receive the reply WM_COPYDATA message.
  3. Pack an EVERYTHING_IPC_QUERY2 struct:
       reply_hwnd(4)  reply_msg(4)  search_flags(4)  offset(4)
       max_results(4)  request_flags(4)  sort_type(4)  search_string(var)
  4. Send via WM_COPYDATA (dwData = 18 = EVERYTHING_IPC_COPYDATA_QUERY2W).
  5. Pump messages until we receive a COPYDATASTRUCT reply.
  6. Parse the EVERYTHING_IPC_LIST2 header + ITEM2 array + column data blobs.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import struct
from collections.abc import Iterator
from typing import Any

from .constants import RequestFlags, SortType

# ── Win32 constants ──────────────────────────────────────────────────
WM_COPYDATA = 0x004A
WM_QUIT = 0x0012

# IPC message IDs
_COPYDATA_QUERY2W = 18
_REPLY_MSG_ID = 0  # we'll use 0 as our reply_copydata_message tag

# IPC search flags
_IPC_MATCHCASE = 0x01
_IPC_MATCHWHOLEWORD = 0x02
_IPC_MATCHPATH = 0x04
_IPC_REGEX = 0x08

# IPC item flags
_IPC_FOLDER = 0x01

# ── ctypes helpers ───────────────────────────────────────────────────
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM
)


class COPYDATASTRUCT(ctypes.Structure):
    _fields_ = [
        ("dwData", ctypes.c_size_t),  # ULONG_PTR
        ("cbData", wt.DWORD),
        ("lpData", ctypes.c_void_p),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.UINT),
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE),
        ("hIcon", wt.HICON),
        ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HANDLE),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
        ("hIconSm", wt.HICON),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wt.HWND),
        ("message", wt.UINT),
        ("wParam", wt.WPARAM),
        ("lParam", wt.LPARAM),
        ("time", wt.DWORD),
        ("pt", wt.POINT),
    ]


# ── Exceptions ───────────────────────────────────────────────────────

class EverythingNotRunning(Exception):
    """Everything process is not running or IPC window not found."""


class IPCError(Exception):
    """IPC communication failed."""


# ── Configure Win32 function signatures ──────────────────────────────
user32.FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
user32.FindWindowW.restype = wt.HWND

user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SendMessageW.restype = ctypes.c_long

user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_long

user32.PeekMessageW.argtypes = [
    ctypes.POINTER(MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT
]
user32.PeekMessageW.restype = wt.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.TranslateMessage.restype = wt.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = ctypes.c_long

user32.CreateWindowExW.argtypes = [
    wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wt.HWND, wt.HANDLE, wt.HINSTANCE, wt.LPVOID,
]
user32.CreateWindowExW.restype = wt.HWND

user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wt.ATOM

user32.DestroyWindow.argtypes = [wt.HWND]
user32.DestroyWindow.restype = wt.BOOL


# ── Window discovery ─────────────────────────────────────────────────

_BASE_CLASS = "EVERYTHING_TASKBAR_NOTIFICATION"

# Known instance suffixes to scan (priority order)
_KNOWN_INSTANCES = ("1.5a", "1.5", "1.4")


def list_instances() -> list[dict[str, Any]]:
    """Scan for all running Everything instances.

    Returns a list of dicts, each with:
      name     – instance name (e.g. "1.5a") or "default" for bare class
      class    – window class string
      hwnd     – window handle as int
    """
    found: list[dict[str, Any]] = []
    for name in _KNOWN_INSTANCES:
        cls = f"{_BASE_CLASS}_({name})"
        hwnd = user32.FindWindowW(cls, None)
        if hwnd:
            found.append({"name": name, "class": cls, "hwnd": hwnd})
    # Check bare class (default / unnamed instance)
    hwnd = user32.FindWindowW(_BASE_CLASS, None)
    if hwnd:
        found.append({"name": "default", "class": _BASE_CLASS, "hwnd": hwnd})
    return found


def _find_everything_window(instance: str | None = None) -> wt.HWND:
    """Locate Everything's hidden IPC window.

    Tries instance-suffixed class first (e.g. "_(1.5a)"), then bare class.
    """
    candidates: list[str] = []
    if instance:
        candidates.append(f"{_BASE_CLASS}_({instance})")
    candidates.append(_BASE_CLASS)

    for cls in candidates:
        hwnd = user32.FindWindowW(cls, None)
        if hwnd:
            return wt.HWND(hwnd)

    raise EverythingNotRunning(
        "Everything IPC window not found. Everything may have been closed.\n"
        "  • Restart Everything and try again."
    )


def detect_instance() -> str | None:
    """Auto-detect the Everything instance name by scanning for known classes.

    Returns the instance name (e.g. "1.5a") or None for default instance.
    Raises EverythingNotRunning if no Everything window is found.
    """
    for name in _KNOWN_INSTANCES:
        cls = f"{_BASE_CLASS}_({name})"
        if user32.FindWindowW(cls, None):
            return name
    # Check bare class (default instance)
    if user32.FindWindowW(_BASE_CLASS, None):
        return None

    raise EverythingNotRunning(
        "Everything is not running (no IPC window found).\n"
        "  • Make sure Voidtools Everything is installed and running.\n"
        "  • Supported versions: Everything 1.4, 1.5, 1.5a.\n"
        "  • Download: https://www.voidtools.com/downloads/\n"
        "  • If Everything is running, check it has IPC enabled\n"
        "    (Options → General → Everything Service)."
    )


# ── Reply window ─────────────────────────────────────────────────────

# Module-level state for the reply callback
_reply_data: bytearray | None = None
_reply_received = False
_CLASS_NAME = "EVERYTHING_CLI_REPLY"
_class_registered = False


def _wnd_proc(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
    global _reply_data, _reply_received

    if msg == WM_COPYDATA:
        cds = ctypes.cast(lparam, ctypes.POINTER(COPYDATASTRUCT)).contents
        # Copy the data before returning (the buffer is only valid during this call)
        size = cds.cbData
        if size > 0 and cds.lpData:
            buf = (ctypes.c_ubyte * size).from_address(cds.lpData)
            _reply_data = bytearray(buf)
        else:
            _reply_data = bytearray()
        _reply_received = True
        return 1  # TRUE = message handled

    # Use kernel DefWindowProcW directly via ctypes to avoid LPARAM overflow
    return _def_window_proc(hwnd, msg, wparam, lparam)


# Separate DefWindowProcW with proper pointer-sized arg types to handle 64-bit values
_DefWindowProcW = ctypes.windll.user32.DefWindowProcW
_DefWindowProcW.argtypes = [
    ctypes.c_void_p,  # HWND
    wt.UINT,          # msg
    ctypes.c_void_p,  # WPARAM (pointer-sized)
    ctypes.c_void_p,  # LPARAM (pointer-sized)
]
_DefWindowProcW.restype = ctypes.c_long


def _def_window_proc(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
    return int(_DefWindowProcW(hwnd, msg, wparam, lparam))


# Must keep a reference to prevent GC of the callback
_wnd_proc_cb = WNDPROC(_wnd_proc)


def _create_reply_window() -> wt.HWND:
    """Create a hidden window to receive WM_COPYDATA reply messages."""
    global _class_registered

    hinstance = kernel32.GetModuleHandleW(None)

    if not _class_registered:
        wcex = WNDCLASSEXW()
        wcex.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wcex.lpfnWndProc = _wnd_proc_cb
        wcex.hInstance = hinstance
        wcex.lpszClassName = _CLASS_NAME
        atom = user32.RegisterClassExW(ctypes.byref(wcex))
        if not atom:
            raise IPCError(f"RegisterClassExW failed: {kernel32.GetLastError()}")
        _class_registered = True

    HWND_MESSAGE = wt.HWND(-3)  # message-only window
    hwnd = user32.CreateWindowExW(
        0, _CLASS_NAME, None, 0,
        0, 0, 0, 0,
        HWND_MESSAGE, None, hinstance, None,
    )
    if not hwnd:
        raise IPCError(f"CreateWindowExW failed: {kernel32.GetLastError()}")
    return wt.HWND(hwnd)


def _hwnd_to_int(hwnd: wt.HWND) -> int:
    """Extract integer value from a ctypes HWND (c_void_p)."""
    if hwnd is None:
        return 0
    val = getattr(hwnd, 'value', hwnd)
    return int(val) if val is not None else 0


# ── Query building ───────────────────────────────────────────────────

def _build_query2(
    reply_hwnd: int,
    search: str,
    *,
    search_flags: int = 0,
    offset: int = 0,
    max_results: int = 0xFFFFFFFF,
    request_flags: int = 0,
    sort_type: int = 1,
) -> bytes:
    """Build an EVERYTHING_IPC_QUERY2 struct as raw bytes.

    Layout (7 × DWORD header + null-terminated UTF-16LE search string):
      reply_hwnd          DWORD
      reply_copydata_msg  DWORD
      search_flags        DWORD
      offset              DWORD
      max_results         DWORD
      request_flags       DWORD
      sort_type           DWORD
      search_string       wchar_t[]  (null-terminated)
    """
    search_bytes = search.encode("utf-16-le") + b"\x00\x00"
    header = struct.pack(
        "<IIIIIII",
        reply_hwnd & 0xFFFFFFFF,
        _REPLY_MSG_ID,
        search_flags,
        offset,
        max_results,
        request_flags,
        sort_type,
    )
    return header + search_bytes


def _send_query(
    ev_hwnd: wt.HWND,
    reply_hwnd: wt.HWND,
    query_buf: bytes,
) -> bytearray:
    """Send the query via WM_COPYDATA and wait for the reply."""
    global _reply_data, _reply_received
    _reply_data = None
    _reply_received = False

    # Build COPYDATASTRUCT for SendMessage
    buf = ctypes.create_string_buffer(query_buf)
    cds = COPYDATASTRUCT()
    cds.dwData = _COPYDATA_QUERY2W
    cds.cbData = len(query_buf)
    cds.lpData = ctypes.cast(buf, ctypes.c_void_p)

    # Use a dedicated SendMessage with c_void_p args to avoid type issues
    _SendMessageW = ctypes.windll.user32.SendMessageW
    _SendMessageW.argtypes = [ctypes.c_void_p, wt.UINT, ctypes.c_void_p, ctypes.c_void_p]
    _SendMessageW.restype = ctypes.c_long

    reply_val = _hwnd_to_int(reply_hwnd)
    result = _SendMessageW(
        ev_hwnd,
        WM_COPYDATA,
        reply_val,
        ctypes.addressof(cds),
    )
    if not result:
        raise IPCError(
            "Everything rejected the IPC query.\n"
            "  • This may happen if Everything's version doesn't support IPC2.\n"
            "  • Supported versions: Everything 1.4.1+, 1.5, 1.5a.\n"
            "  • Try restarting Everything."
        )

    # Pump messages until we receive the reply
    import time
    msg = MSG()
    deadline = time.monotonic() + 30.0

    while not _reply_received:
        if time.monotonic() > deadline:
            raise IPCError(
                "Timed out waiting for Everything IPC reply (30s).\n"
                "  • Everything may be busy indexing or unresponsive.\n"
                "  • Try restarting Everything."
            )
        # PeekMessage to avoid blocking forever
        if user32.PeekMessageW(ctypes.byref(msg), reply_hwnd, 0, 0, 1):  # PM_REMOVE
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        else:
            time.sleep(0.001)

    if _reply_data is None:
        raise IPCError("Received empty reply from Everything")
    return _reply_data


# ── Response parsing ─────────────────────────────────────────────────

# Struct sizes
_LIST2_HEADER_SIZE = 5 * 4  # totitems(4) + numitems(4) + offset(4) + request_flags(4) + sort_type(4)
_ITEM2_SIZE = 2 * 4  # flags(4) + data_offset(4)

# Field parsers: how to read each field type from the data blob
# Returns (value, bytes_consumed)

def _read_wstring(data: bytearray, pos: int) -> tuple[str, int]:
    """Read a DWORD length + null-terminated wchar_t string."""
    length = struct.unpack_from("<I", data, pos)[0]  # length in wchars (excl. null)
    pos += 4
    byte_len = length * 2
    text = data[pos:pos + byte_len].decode("utf-16-le", errors="replace")
    pos += (length + 1) * 2  # skip null terminator too
    return text, pos


def _read_uint64(data: bytearray, pos: int) -> tuple[int, int]:
    """Read a LARGE_INTEGER / FILETIME (8 bytes)."""
    val = struct.unpack_from("<Q", data, pos)[0]
    return val, pos + 8


def _read_dword(data: bytearray, pos: int) -> tuple[int, int]:
    """Read a DWORD (4 bytes)."""
    val = struct.unpack_from("<I", data, pos)[0]
    return val, pos + 4


# The ordered list of (request_flag_bit, field_name, reader, is_string)
# Order MUST match the order Everything writes data (same as _es_ipc2_get_column_data)
_FIELD_ORDER: list[tuple[int, str, str]] = [
    (RequestFlags.FILE_NAME, "name", "wstring"),
    (RequestFlags.PATH, "path", "wstring"),
    (RequestFlags.FULL_PATH_AND_FILE_NAME, "full_path", "wstring"),
    (RequestFlags.EXTENSION, "ext", "wstring"),
    (RequestFlags.SIZE, "size", "uint64"),
    (RequestFlags.DATE_CREATED, "date_created", "uint64"),
    (RequestFlags.DATE_MODIFIED, "date_modified", "uint64"),
    (RequestFlags.DATE_ACCESSED, "date_accessed", "uint64"),
    (RequestFlags.ATTRIBUTES, "attributes", "dword"),
    (RequestFlags.FILE_LIST_FILE_NAME, "file_list_filename", "wstring"),
    (RequestFlags.RUN_COUNT, "run_count", "dword"),
    (RequestFlags.DATE_RUN, "date_run", "uint64"),
    (RequestFlags.DATE_RECENTLY_CHANGED, "date_recently_changed", "uint64"),
    (RequestFlags.HIGHLIGHTED_FILE_NAME, "hl_name", "wstring"),
    (RequestFlags.HIGHLIGHTED_PATH, "hl_path", "wstring"),
    (RequestFlags.HIGHLIGHTED_FULL_PATH_AND_FILE_NAME, "hl_full_path", "wstring"),
]


def _parse_item_data(
    data: bytearray,
    data_offset: int,
    request_flags: int,
    wanted_fields: set[str],
) -> dict[str, Any]:
    """Parse one item's data blob according to request_flags ordering."""
    pos = data_offset
    record: dict[str, Any] = {}

    for flag_bit, field_name, reader_type in _FIELD_ORDER:
        if not request_flags & flag_bit:
            continue

        if reader_type == "wstring":
            sval, pos = _read_wstring(data, pos)
            if field_name in wanted_fields:
                record[field_name] = sval
        elif reader_type == "uint64":
            ival, pos = _read_uint64(data, pos)
            if field_name in wanted_fields:
                record[field_name] = ival
        elif reader_type == "dword":
            dval, pos = _read_dword(data, pos)
            if field_name in wanted_fields:
                record[field_name] = dval

    return record


def parse_response(
    data: bytearray,
    fields: list[str],
    request_flags: int,  # pylint: disable=unused-argument  # kept for API compat; resp uses header flags
) -> Iterator[dict[str, Any]]:
    """Parse an EVERYTHING_IPC_LIST2 response buffer into result dicts.

    Yields one dict per result with the requested fields.
    """
    from ..util.dates import filetime_to_iso
    from ..util.attrs import attrs_to_string

    if len(data) < _LIST2_HEADER_SIZE:
        return

    _, numitems, _, resp_flags, _ = struct.unpack_from(
        "<IIIII", data, 0
    )
    wanted = set(fields)
    # Also track derived fields
    need_is_file = "is_file" in wanted
    need_is_folder = "is_folder" in wanted

    # Item array starts right after the header
    items_offset = _LIST2_HEADER_SIZE

    for i in range(numitems):
        item_pos = items_offset + i * _ITEM2_SIZE
        if item_pos + _ITEM2_SIZE > len(data):
            break
        item_flags, data_offset = struct.unpack_from("<II", data, item_pos)

        if data_offset >= len(data):
            break

        record = _parse_item_data(data, data_offset, resp_flags, wanted)

        # Post-process: extension dot prefix (SDK omits it)
        if "ext" in record:
            raw_ext = record["ext"]
            record["ext"] = "." + raw_ext if raw_ext else ""

        # Post-process: FILETIME → ISO 8601
        for date_field in (
            "date_created", "date_modified", "date_accessed",
            "date_run", "date_recently_changed",
        ):
            if date_field in record:
                record[date_field] = filetime_to_iso(record[date_field])

        # Post-process: attributes → string
        if "attributes" in record:
            raw = record["attributes"]
            record["attributes"] = attrs_to_string(raw) if raw != 0xFFFFFFFF else ""

        # Derived fields from item flags
        is_folder = bool(item_flags & _IPC_FOLDER)
        if need_is_file:
            record["is_file"] = not is_folder
        if need_is_folder:
            record["is_folder"] = is_folder

        yield record


# ── High-level query function ────────────────────────────────────────

def ipc_query(
    search: str,
    *,
    fields: list[str],
    request_flags: int,
    sort: SortType = SortType.NAME_ASCENDING,
    max_results: int | None = None,
    offset: int = 0,
    match_case: bool = False,
    match_path: bool = False,
    match_whole_word: bool = False,
    regex: bool = False,
    instance: str | None = None,
) -> tuple[Iterator[dict[str, Any]], int, int]:
    """Execute an IPC2 query and return (results_iterator, num_results, total_results).

    The caller should consume the iterator (it parses lazily from the response buffer).
    """
    # Find Everything window
    ev_hwnd = _find_everything_window(instance)

    # Create reply window
    reply_hwnd = _create_reply_window()

    try:
        # Build search flags
        sflags = 0
        if match_case:
            sflags |= _IPC_MATCHCASE
        if match_whole_word:
            sflags |= _IPC_MATCHWHOLEWORD
        if match_path:
            sflags |= _IPC_MATCHPATH
        if regex:
            sflags |= _IPC_REGEX

        max_res = max_results if max_results is not None else 0xFFFFFFFF

        query_buf = _build_query2(
            _hwnd_to_int(reply_hwnd),
            search,
            search_flags=sflags,
            offset=offset,
            max_results=max_res,
            request_flags=request_flags,
            sort_type=int(sort),
        )

        # Send and wait for reply
        response = _send_query(ev_hwnd, reply_hwnd, query_buf)

        # Parse header for totals
        if len(response) >= _LIST2_HEADER_SIZE:
            totitems, numitems = struct.unpack_from("<II", response, 0)
        else:
            totitems, numitems = 0, 0

        results = parse_response(response, fields, request_flags)
        return results, numitems, totitems

    finally:
        user32.DestroyWindow(reply_hwnd)


def ipc_get_version(instance: str | None = None) -> dict[str, Any]:
    """Get Everything version via WM_IPC messages.

    Sends 4 WM_USER messages (major/minor/revision/build). Safe for all versions
    including Everything 1.5a which restarts when receiving 5+ rapid WM_USER messages.
    """
    ev_hwnd = _find_everything_window(instance)

    WM_USER = 0x0400
    IPC_GET_MAJOR = 0
    IPC_GET_MINOR = 1
    IPC_GET_REVISION = 2
    IPC_GET_BUILD = 3

    major = user32.SendMessageW(ev_hwnd, WM_USER, IPC_GET_MAJOR, 0)
    minor = user32.SendMessageW(ev_hwnd, WM_USER, IPC_GET_MINOR, 0)
    revision = user32.SendMessageW(ev_hwnd, WM_USER, IPC_GET_REVISION, 0)
    build = user32.SendMessageW(ev_hwnd, WM_USER, IPC_GET_BUILD, 0)

    return {
        "major": major,
        "minor": minor,
        "revision": revision,
        "build": build,
        "version": f"{major}.{minor}.{revision}.{build}",
    }


# wParam values that cause Everything 1.5a to restart:
#   6  (IPC_GET_TARGET_MACHINE) — triggers restart immediately
#   7  (IPC_IS_DB_LOADED)       — also problematic on 1.5a
# These are skipped for 1.5a instances; safe values are inferred instead.


def ipc_get_info(instance: str | None = None) -> dict[str, Any]:
    """Get Everything service info via WM_IPC messages.

    Everything 1.5a restarts when it receives IPC_GET_TARGET_MACHINE
    (wParam=6) or IPC_IS_DB_LOADED (wParam=7).  These are skipped for
    1.5a and returned as None.
    """
    ev_hwnd = _find_everything_window(instance)

    WM_USER = 0x0400
    IPC_GET_MAJOR = 0
    IPC_GET_MINOR = 1
    IPC_GET_REVISION = 2
    IPC_GET_BUILD = 3
    IPC_GET_TARGET = 6
    IPC_IS_DB_LOADED = 7
    IPC_IS_ADMIN = 25
    IPC_IS_APPDATA = 26

    def _send(wp: int) -> int:
        return int(user32.SendMessageW(ev_hwnd, WM_USER, wp, 0))

    is_15a = instance == "1.5a"

    major = _send(IPC_GET_MAJOR)
    minor = _send(IPC_GET_MINOR)
    revision = _send(IPC_GET_REVISION)
    build = _send(IPC_GET_BUILD)

    # wParam 6 and 7 cause Everything 1.5a to restart — skip entirely.
    if is_15a:
        target = None
        db_loaded = None
    else:
        target_code = _send(IPC_GET_TARGET)
        target_names = {1: "x86", 2: "x64", 3: "arm", 4: "arm64"}
        target = target_names.get(target_code, f"unknown({target_code})")
        db_loaded = bool(_send(IPC_IS_DB_LOADED))

    is_admin = _send(IPC_IS_ADMIN)
    is_appdata = _send(IPC_IS_APPDATA)

    return {
        "major": major,
        "minor": minor,
        "revision": revision,
        "build": build,
        "version": f"{major}.{minor}.{revision}.{build}",
        "target": target,
        "db_loaded": db_loaded,
        "is_admin": bool(is_admin),
        "is_appdata": bool(is_appdata),
    }

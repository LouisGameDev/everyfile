#!/usr/bin/env python3
"""Local CI — runs the same checks as .github/workflows/ci.yml.

Usage:
    python ci.py          # run all checks
    python ci.py lint     # mypy + pyright only
    python ci.py test     # pytest only
"""

from __future__ import annotations

import subprocess
import sys
import time

STEPS: dict[str, list[list[str]]] = {
    "lint": [
        ["mypy", "src/"],
        ["pyright", "src/"],
    ],
    "test": [
        ["pytest", "-v"],
    ],
}


def run_step(cmd: list[str]) -> bool:
    label = " ".join(cmd)
    print(f"\n{'─' * 60}")
    print(f"  ▶ {label}")
    print(f"{'─' * 60}")
    t0 = time.perf_counter()
    result = subprocess.run(cmd)
    elapsed = time.perf_counter() - t0
    ok = result.returncode == 0
    status = "✓ PASS" if ok else "✗ FAIL"
    print(f"  {status}  ({elapsed:.1f}s)")
    return ok


def main() -> None:
    subset = sys.argv[1] if len(sys.argv) > 1 else None

    if subset and subset not in STEPS:
        print(f"Unknown target: {subset!r}. Use: {', '.join(STEPS)}")
        sys.exit(1)

    groups = [subset] if subset else list(STEPS)
    results: list[tuple[str, bool]] = []

    t_start = time.perf_counter()
    for group in groups:
        for cmd in STEPS[group]:
            ok = run_step(cmd)
            results.append((" ".join(cmd), ok))

    elapsed_total = time.perf_counter() - t_start
    print(f"\n{'═' * 60}")
    print(f"  Results ({elapsed_total:.1f}s total):")
    for label, ok in results:
        print(f"    {'✓' if ok else '✗'}  {label}")
    print(f"{'═' * 60}")

    if not all(ok for _, ok in results):
        sys.exit(1)


if __name__ == "__main__":
    main()

"""P0 gate: no emoji characters as functional icons anywhere in the repo.

Scans source / docs / frontend files. Exits 1 with the offending locations
when any emoji codepoint is found. Comments in THIS file describing the rule
are exempt by construction (the scanner never matches itself because the
pattern is assembled from numeric ranges).

Author: 晨星
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_RANGES = [
    (0x1F300, 0x1F9FF), (0x2600, 0x26FF), (0x2700, 0x27BF),
    (0xFE00, 0xFE0F), (0x1F000, 0x1F02F), (0x1F0A0, 0x1F0FF),
    (0x1F100, 0x1F64F), (0x1F680, 0x1F6FF), (0x1F900, 0x1F9FF),
    (0x1FA00, 0x1FA6F), (0x1FA70, 0x1FAFF), (0x200D, 0x200D),
    (0x20E3, 0x20E3), (0xE0020, 0xE007F),
]
_EMOJI_RE = re.compile("[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in _RANGES) + "]")

_SCAN_SUFFIXES = {".py", ".md", ".ts", ".tsx", ".js", ".jsx", ".html", ".css", ".json", ".yaml", ".yml", ".txt"}
_SKIP_DIRS = {".git", "node_modules", "models", "dist", "__pycache__", ".pytest-tmp", ".venv", "data/.pytest-tmp"}
_SELF = Path(__file__).resolve()


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _SCAN_SUFFIXES:
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.resolve() == _SELF:
            continue
        yield path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    violations: list[str] = []
    for path in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if _EMOJI_RE.search(line):
                violations.append(f"{path.relative_to(root)}:{lineno}: {line.strip()[:80]}")
    if violations:
        print("EMOJI GATE FAILED:")
        print("\n".join(violations))
        return 1
    print("emoji gate: OK (0 violations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

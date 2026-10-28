"""Repo-wide vendor-leak audit: every hit with a short, single-line context.

Prints one line per hit so a wall of crawled HTML cannot flood the terminal.
Run:  python scripts/audit_vendors.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", ".next", "out", "__pycache__", ".pytest_cache", "tavily_cache"}
SKIP_SUFFIXES = {".mp4", ".wav", ".mp3", ".png", ".jpg", ".jpeg", ".webp", ".ico", ".woff", ".woff2"}
SKIP_NAMES = {"package-lock.json", "audit_vendors.py"}

TOKENS = re.compile(
    r"(Meta Model API|META_[A-Z_]+|meta-models|Meta via Baseten|Meta AI|muse-[a-z0-9.\-]+|Muse [A-Z][a-z]+|\bBaseten\b|\bbaseten\b|facebook/mms-tts[a-z0-9.\-]*)",
)


def main() -> int:
    hits = 0
    files = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name in SKIP_NAMES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        file_hits = 0
        for number, line in enumerate(text.splitlines(), 1):
            for match in TOKENS.finditer(line):
                start = max(0, match.start() - 45)
                end = min(len(line), match.end() + 45)
                snippet = line[start:end].replace("\t", " ").strip()
                print(f"{path.relative_to(ROOT)}:{number}: [{match.group(0)}] {snippet}")
                file_hits += 1
                hits += 1
        if file_hits:
            files += 1
    print(f"\n{hits} hit(s) in {files} file(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())

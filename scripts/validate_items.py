"""Validate benchmark items.

Usage:
    python scripts/validate_items.py                 # public + private (if present)
    python scripts/validate_items.py path/to/file.jsonl [more.jsonl ...]
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mgeval.items import check_items, load_jsonl, load_split  # noqa: E402


def main(argv: list[str]) -> int:
    if argv:
        items = [it for p in argv for it in load_jsonl(Path(p))]
    else:
        items = load_split("all")
    errs = check_items(items)
    counts = Counter((it.get("split"), it.get("category")) for it in items)
    for (split, cat), n in sorted(counts.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        print(f"{split:8s} {cat:6s} {n}")
    print(f"total items: {len(items)}")
    for e in errs:
        print("ERROR", e)
    print("OK" if not errs else f"{len(errs)} problem(s)")
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

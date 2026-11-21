"""Load and check benchmark items."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .schema import validate_item

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT / "items" / "public"
PRIVATE_DIR = ROOT / "private" / "items"


def load_jsonl(path: Path) -> list[dict]:
    items = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{lineno}: bad JSON ({exc})") from exc
    return items


def load_dir(directory: Path) -> list[dict]:
    if not directory.exists():
        return []
    out: list[dict] = []
    for path in sorted(directory.glob("*.jsonl")):
        out.extend(load_jsonl(path))
    return out


def load_split(split: str) -> list[dict]:
    if split == "public":
        return load_dir(PUBLIC_DIR)
    if split == "private":
        return load_dir(PRIVATE_DIR)
    if split == "all":
        return load_dir(PUBLIC_DIR) + load_dir(PRIVATE_DIR)
    raise ValueError(f"unknown split {split}")


def _shingles(text: str, k: int = 5) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z]+", text.lower())
    return {tuple(words[i : i + k]) for i in range(max(0, len(words) - k + 1))}


def jaccard(a: str, b: str) -> float:
    sa, sb = _shingles(a), _shingles(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def check_items(items: list[dict], dup_threshold: float = 0.5) -> list[str]:
    """Validate every item, check unique ids, and flag near-duplicate prompts.

    The near-duplicate check compares word 5-gram overlap of prompts with the
    numbers stripped out, which catches parameter-swapped copies.
    """
    errs: list[str] = []
    ids: set[str] = set()
    for it in items:
        errs.extend(validate_item(it))
        iid = it.get("id")
        if iid in ids:
            errs.append(f"{iid}: duplicate id")
        ids.add(iid)
    prompts = [(it.get("id"), re.sub(r"[\d.,]+", " ", it.get("prompt", ""))) for it in items]
    for i in range(len(prompts)):
        for j in range(i + 1, len(prompts)):
            sim = jaccard(prompts[i][1], prompts[j][1])
            if sim >= dup_threshold:
                errs.append(f"{prompts[i][0]} ~ {prompts[j][0]}: near-duplicate prompts (5-gram Jaccard {sim:.2f})")
    return errs

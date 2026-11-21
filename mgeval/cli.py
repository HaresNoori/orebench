"""Command line entry point.

Examples
--------
Dry run (no keys, no network; mock candidates and mock judge):
    python -m mgeval --dry-run

Live run (keys from env vars ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY):
    python -m mgeval --split public \
        --model anthropic:<model-id> --model openai:<model-id> --model google:<model-id> \
        --judge openai:<judge-model-id>
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .items import ROOT, check_items, load_split
from .providers import available_keys, make_provider
from .runner import results_markdown, run
from .scoring import LLMJudge, MockJudge


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mgeval", description="Mining geoscience and mining finance LLM eval")
    ap.add_argument("--split", default="public", choices=["public", "private", "all"])
    ap.add_argument("--model", action="append", default=[], help="provider:model_id (repeatable)")
    ap.add_argument("--judge", default=None, help="provider:model_id for the rubric judge")
    ap.add_argument("--dry-run", action="store_true", help="offline: mock candidates and mock judge, no keys")
    ap.add_argument("--category", action="append", default=[], help="limit to category code(s)")
    ap.add_argument("--limit", type=int, default=0, help="max items (0 = all)")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--out", default=None, help="output directory (default results/<timestamp>)")
    ap.add_argument("--check-keys", action="store_true", help="report which API keys are set, then exit")
    args = ap.parse_args(argv)

    if args.check_keys:
        for prov, present in available_keys().items():
            print(f"{prov:10s} {'set' if present else 'not set'}")
        return 0

    items = load_split(args.split)
    if not items:
        print(f"no items found for split '{args.split}'", file=sys.stderr)
        return 2
    problems = check_items(items)
    if problems:
        print("item validation failed:", *problems[:20], sep="\n  ", file=sys.stderr)
        return 2
    if args.category:
        items = [it for it in items if it["category"] in set(args.category)]
    if args.limit:
        items = items[: args.limit]

    if args.dry_run:
        candidates = [make_provider("mock:reference"), make_provider("mock:garbage")]
        judge = MockJudge()
    else:
        if not args.model:
            ap.error("give at least one --model provider:model_id, or use --dry-run")
        if not args.judge:
            ap.error("give --judge provider:model_id (ideally a different vendor from the candidates)")
        candidates = [make_provider(m) for m in args.model]
        judge = LLMJudge(make_provider(args.judge))

    out = Path(args.out) if args.out else ROOT / "results" / time.strftime("%Y%m%d-%H%M%S")
    print(f"{len(items)} items, {len(candidates)} candidate(s), judge {judge.name}, writing {out}")
    summary = run(items, candidates, judge, out, max_tokens=args.max_tokens)
    print()
    print(results_markdown(summary))
    if summary["errors"]:
        print(f"\n{len(summary['errors'])} call(s) failed; see summary.json")
    if args.dry_run:
        ref = summary["models"]["mock:reference"]["overall_pct"]
        bad = summary["models"]["mock:garbage"]["overall_pct"]
        ok = ref >= 90.0 and bad <= 10.0
        print(f"\nDRY RUN {'PASSED' if ok else 'FAILED'}: reference mock {ref}%, garbage mock {bad}% "
              "(mock scores test the pipeline only; they are not model results)")
        return 0 if ok else 1
    return 0

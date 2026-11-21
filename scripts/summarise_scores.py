"""Re-summarise one or more scores.csv files: overall score, bootstrap 95% CI over items, and
run-to-run spread where the file has a `run` column.

Usage:
    python scripts/summarise_scores.py results_v0.1/scores_*.csv
"""
from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mgeval.runner import bootstrap_ci  # noqa: E402


def main(paths: list[str]) -> int:
    by_model_item: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    by_model_run: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                e, a = float(r["earned"]), float(r["available"])
                for bucket in (by_model_item[r["model"]][r["item_id"]], by_model_run[r["model"]][r.get("run", "1")]):
                    bucket[0] += e
                    bucket[1] += a
    print("| Model | Items | Runs | Overall | 95% CI (items) | Run SD |")
    print("|---|---|---|---|---|---|")
    for model, items in by_model_item.items():
        e = sum(v[0] for v in items.values())
        a = sum(v[1] for v in items.values())
        lo, hi = bootstrap_ci([tuple(v) for v in items.values()])
        runs = [100.0 * v[0] / v[1] for v in by_model_run[model].values() if v[1]]
        sd = f"{statistics.stdev(runs):.1f}" if len(runs) > 1 else "-"
        print(f"| {model} | {len(items)} | {len(runs)} | {100.0 * e / a:.1f}% | {lo:.1f}-{hi:.1f} | {sd} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

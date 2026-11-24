"""Run items against models, grade them and write results."""
from __future__ import annotations

import csv
import json
import random
import statistics
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .providers import ProviderError
from .schema import CATEGORIES
from .scoring import ItemScore, score_item

CANDIDATE_SYSTEM = (
    "You are being evaluated on mining geoscience and mining finance reasoning. Answer as a "
    "senior mining geologist and mining-finance analyst would: be specific, show working for "
    "any calculation, and state the single most important judgement clearly."
)


def build_prompt(item: dict) -> str:
    task = item["prompt"]
    if item.get("document_extract"):
        # Long-document items: the extract comes first, then the task.
        task = "DOCUMENT EXTRACT\n\n" + item["document_extract"] + "\n\nTASK\n\n" + task
    checks = item.get("numeric_checks", [])
    if not checks:
        return task
    keys = ", ".join(f'"{c["name"]}" ({c["unit"]})' for c in checks)
    return (
        task
        + "\n\nAfter your answer, finish with one final line in exactly this form, with plain numbers "
        + f"(no units or thousands separators) for these keys: {keys}\n"
        + "FINAL_JSON: {"
        + ", ".join(f'"{c["name"]}": <number>' for c in checks)
        + "}"
    )


def respond(cand, item: dict, max_tokens: int) -> str:
    """Get a candidate's answer. Mock and replay candidates answer per item without shared state."""
    if hasattr(cand, "respond_item"):
        return cand.respond_item(item)
    return cand.complete(CANDIDATE_SYSTEM, build_prompt(item), max_tokens)


def run(items: list[dict], candidates: list, judge, out_dir: Path, max_tokens: int = 4000, log=print,
        workers: int = 1, runs: int = 1) -> dict:
    """Score every candidate on every item, ``runs`` times. Each run re-queries the candidate."""
    from concurrent.futures import ThreadPoolExecutor

    out_dir.mkdir(parents=True, exist_ok=True)
    responses_path = out_dir / "responses.jsonl"
    all_scores: dict[str, list[ItemScore]] = {}
    errors: list[dict] = []

    def one(cand, item):
        t0 = time.time()
        try:
            resp = respond(cand, item, max_tokens)
            sc = score_item(item, resp, judge)
        except ProviderError as exc:
            return item, None, None, str(exc), 0.0
        return item, resp, sc, None, time.time() - t0

    with responses_path.open("w", encoding="utf-8") as rf:
        for cand in candidates:
            scores: list[ItemScore] = []
            for r in range(1, max(1, runs) + 1):
                with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                    results = list(pool.map(lambda it: one(cand, it), items))
                for item, resp, sc, err, secs in results:
                    if err:
                        errors.append({"model": cand.name, "run": r, "item": item["id"], "error": err})
                        log(f"  ! {cand.name} run {r} {item['id']}: {err}")
                        continue
                    sc.run = r
                    scores.append(sc)
                    rf.write(
                        json.dumps(
                            {
                                "model": cand.name,
                                "judge": judge.name,
                                "run": r,
                                "item_id": item["id"],
                                "response": resp,
                                "rubric_awarded": sc.rubric_awarded,
                                "numeric": [asdict(n) for n in sc.numeric],
                                "earned": sc.earned,
                                "available": sc.available,
                                "seconds": round(secs, 2),
                            }
                        )
                        + "\n"
                    )
                    log(f"  {cand.name:28s} run {r} {item['id']:12s} {sc.pct:5.1f}%")
            all_scores[cand.name] = scores
    summary = summarise(all_scores)
    summary["judge"] = judge.name
    summary["errors"] = errors
    write_reports(summary, all_scores, out_dir)
    return summary


def bootstrap_ci(pairs: list[tuple[float, float]], reps: int = 2000, seed: int = 0,
                 level: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap over items of sum(earned) / sum(available), in percent.

    ``pairs`` holds (earned, available) per item, pooled over runs. Resampling items (not runs)
    shows how much the score depends on which items happen to be in the set.
    """
    if not pairs:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(pairs)
    stats = []
    for _ in range(reps):
        e = a = 0.0
        for _ in range(n):
            pe, pa = pairs[rng.randrange(n)]
            e += pe
            a += pa
        stats.append(100.0 * e / a if a else 0.0)
    stats.sort()
    lo = stats[int(((1 - level) / 2) * reps)]
    hi = stats[min(reps - 1, int((1 - (1 - level) / 2) * reps))]
    return (round(lo, 1), round(hi, 1))


def summarise(all_scores: dict[str, list[ItemScore]]) -> dict:
    table: dict[str, dict] = {}
    for model, scores in all_scores.items():
        by_cat: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        by_item: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
        by_run: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        num_pass = num_total = 0
        for s in scores:
            for bucket in (by_cat[s.category], by_item[s.item_id], by_run[s.run]):
                bucket[0] += s.earned
                bucket[1] += s.available
            num_pass += sum(1 for n in s.numeric if n.passed)
            num_total += len(s.numeric)
        earned = sum(v[0] for v in by_cat.values())
        avail = sum(v[1] for v in by_cat.values())
        run_pcts = [round(100.0 * e / a, 1) if a else 0.0 for _, (e, a) in sorted(by_run.items())]
        table[model] = {
            "items": len(by_item),
            "runs": len(by_run),
            "overall_pct": round(100.0 * earned / avail, 1) if avail else 0.0,
            "ci95_items": list(bootstrap_ci([tuple(v) for v in by_item.values()])),
            "run_pcts": run_pcts,
            "run_sd": round(statistics.stdev(run_pcts), 1) if len(run_pcts) > 1 else None,
            "numeric_pass": f"{num_pass}/{num_total}",
            "by_category": {c: round(100.0 * e / a, 1) if a else None for c, (e, a) in sorted(by_cat.items())},
        }
    return {"models": table}


def results_markdown(summary: dict) -> str:
    cats = list(CATEGORIES)
    head = "| Model | Items | Runs | Overall | 95% CI (items) | Run SD | Numeric pass | " + " | ".join(cats) + " |"
    sep = "|" + "---|" * (7 + len(cats))
    rows = [head, sep]
    for model, row in summary["models"].items():
        cells = ["-" if row["by_category"].get(c) is None else f"{row['by_category'][c]:.0f}" for c in cats]
        lo, hi = row.get("ci95_items") or (None, None)
        ci = f"{lo:.1f}-{hi:.1f}" if lo is not None else "-"
        sd = "-" if row.get("run_sd") is None else f"{row['run_sd']:.1f}"
        rows.append(
            f"| {model} | {row['items']} | {row.get('runs', 1)} | **{row['overall_pct']:.1f}%** | {ci} | {sd} | "
            f"{row['numeric_pass']} | " + " | ".join(cells) + " |"
        )
    rows.append("")
    rows.append(
        f"Judge: `{summary.get('judge', '?')}`. Overall and category cells are % of available points, pooled "
        "over runs. 95% CI: percentile bootstrap over items (2,000 resamples, seed 0). Run SD: standard "
        "deviation of the overall score across runs."
    )
    return "\n".join(rows)


def write_reports(summary: dict, all_scores: dict[str, list[ItemScore]], out_dir: Path) -> None:
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "results.md").write_text(results_markdown(summary) + "\n", encoding="utf-8")
    with (out_dir / "scores.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "run", "item_id", "category", "difficulty", "earned", "available", "pct",
                    "numeric_passed", "numeric_total"])
        for model, scores in all_scores.items():
            for s in scores:
                w.writerow(
                    [model, s.run, s.item_id, s.category, s.difficulty, s.earned, s.available, f"{s.pct:.1f}",
                     sum(1 for n in s.numeric if n.passed), len(s.numeric)]
                )

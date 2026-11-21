"""Run items against models, grade them and write results."""
from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .providers import MockProvider, ProviderError
from .schema import CATEGORIES
from .scoring import ItemScore, score_item

CANDIDATE_SYSTEM = (
    "You are being evaluated on mining geoscience and mining finance reasoning. Answer as a "
    "senior mining geologist and mining-finance analyst would: be specific, show working for "
    "any calculation, and state the single most important judgement clearly."
)


def build_prompt(item: dict) -> str:
    checks = item.get("numeric_checks", [])
    if not checks:
        return item["prompt"]
    keys = ", ".join(f'"{c["name"]}" ({c["unit"]})' for c in checks)
    return (
        item["prompt"]
        + "\n\nAfter your answer, finish with one final line in exactly this form, with plain numbers "
        + f"(no units or thousands separators) for these keys: {keys}\n"
        + "FINAL_JSON: {"
        + ", ".join(f'"{c["name"]}": <number>' for c in checks)
        + "}"
    )


def run(items: list[dict], candidates: list, judge, out_dir: Path, max_tokens: int = 4000, log=print) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    responses_path = out_dir / "responses.jsonl"
    all_scores: dict[str, list[ItemScore]] = {}
    errors: list[dict] = []
    with responses_path.open("w", encoding="utf-8") as rf:
        for cand in candidates:
            scores: list[ItemScore] = []
            for item in items:
                if isinstance(cand, MockProvider):
                    cand.bind(item)
                t0 = time.time()
                try:
                    resp = cand.complete(CANDIDATE_SYSTEM, build_prompt(item), max_tokens)
                    sc = score_item(item, resp, judge)
                except ProviderError as exc:
                    errors.append({"model": cand.name, "item": item["id"], "error": str(exc)})
                    log(f"  ! {cand.name} {item['id']}: {exc}")
                    continue
                scores.append(sc)
                rf.write(
                    json.dumps(
                        {
                            "model": cand.name,
                            "judge": judge.name,
                            "item_id": item["id"],
                            "response": resp,
                            "rubric_awarded": sc.rubric_awarded,
                            "numeric": [asdict(n) for n in sc.numeric],
                            "earned": sc.earned,
                            "available": sc.available,
                            "seconds": round(time.time() - t0, 2),
                        }
                    )
                    + "\n"
                )
                log(f"  {cand.name:28s} {item['id']:12s} {sc.pct:5.1f}%")
            all_scores[cand.name] = scores
    summary = summarise(all_scores)
    summary["judge"] = judge.name
    summary["errors"] = errors
    write_reports(summary, all_scores, out_dir)
    return summary


def summarise(all_scores: dict[str, list[ItemScore]]) -> dict:
    table: dict[str, dict] = {}
    for model, scores in all_scores.items():
        by_cat: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        num_pass = num_total = 0
        for s in scores:
            by_cat[s.category][0] += s.earned
            by_cat[s.category][1] += s.available
            num_pass += sum(1 for n in s.numeric if n.passed)
            num_total += len(s.numeric)
        earned = sum(v[0] for v in by_cat.values())
        avail = sum(v[1] for v in by_cat.values())
        table[model] = {
            "items": len(scores),
            "overall_pct": round(100.0 * earned / avail, 1) if avail else 0.0,
            "numeric_pass": f"{num_pass}/{num_total}",
            "by_category": {c: round(100.0 * e / a, 1) if a else None for c, (e, a) in sorted(by_cat.items())},
        }
    return {"models": table}


def results_markdown(summary: dict) -> str:
    cats = list(CATEGORIES)
    head = "| Model | Items | Overall | Numeric pass | " + " | ".join(cats) + " |"
    sep = "|" + "---|" * (4 + len(cats))
    rows = [head, sep]
    for model, row in summary["models"].items():
        cells = [
            "-" if row["by_category"].get(c) is None else f"{row['by_category'][c]:.0f}" for c in cats
        ]
        rows.append(
            f"| {model} | {row['items']} | {row['overall_pct']:.1f}% | {row['numeric_pass']} | " + " | ".join(cells) + " |"
        )
    rows.append("")
    rows.append(f"Judge: `{summary.get('judge', '?')}`. Category cells are % of available points.")
    return "\n".join(rows)


def write_reports(summary: dict, all_scores: dict[str, list[ItemScore]], out_dir: Path) -> None:
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "results.md").write_text(results_markdown(summary) + "\n", encoding="utf-8")
    with (out_dir / "scores.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "item_id", "category", "difficulty", "earned", "available", "pct", "numeric_passed", "numeric_total"])
        for model, scores in all_scores.items():
            for s in scores:
                w.writerow(
                    [model, s.item_id, s.category, s.difficulty, s.earned, s.available, f"{s.pct:.1f}",
                     sum(1 for n in s.numeric if n.passed), len(s.numeric)]
                )

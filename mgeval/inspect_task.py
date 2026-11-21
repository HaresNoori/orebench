"""Optional backend for the Inspect evaluation framework (inspect_ai, MIT licence, UK AI
Security Institute). It reuses this package's item loader, prompt builder, judge prompt and
numeric checks, so results line up with the standalone harness.

    pip install inspect-ai
    inspect eval mgeval/inspect_task.py --model anthropic/<model-id> \
        -T split=public -T grader=openai/<grader-model-id>

Inspect then provides its log viewer, retries, concurrency and provider coverage.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):  # loaded by file path from the inspect CLI
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inspect_ai import Task, task  # noqa: E402
from inspect_ai.dataset import MemoryDataset, Sample  # noqa: E402
from inspect_ai.model import GenerateConfig, get_model  # noqa: E402
from inspect_ai.scorer import Score, Target, mean, scorer, stderr  # noqa: E402
from inspect_ai.solver import TaskState, generate, system_message  # noqa: E402

from mgeval.items import load_split  # noqa: E402
from mgeval.runner import CANDIDATE_SYSTEM, build_prompt  # noqa: E402
from mgeval.scoring import JUDGE_SYSTEM, judge_prompt, parse_judge, score_numeric  # noqa: E402


def _samples(split: str, category: str | None) -> list[Sample]:
    items = load_split(split)
    if category:
        items = [it for it in items if it["category"] == category]
    return [
        Sample(
            id=it["id"],
            input=build_prompt(it),
            target=it["reference_answer"],
            metadata={"item": it, "category": it["category"], "difficulty": it["difficulty"]},
        )
        for it in items
    ]


@scorer(metrics=[mean(), stderr()])
def rubric_scorer(grader: str | None = None):
    """Fraction of rubric points awarded by a grader model (different vendor recommended)."""

    async def score(state: TaskState, target: Target) -> Score:
        item = state.metadata["item"]
        model = get_model(grader, config=GenerateConfig(temperature=0)) if grader else get_model()
        out = await model.generate(JUDGE_SYSTEM + "\n\n" + judge_prompt(item, state.output.completion))
        awarded = parse_judge(out.completion, item)
        total = sum(r["points"] for r in item["rubric"])
        return Score(value=sum(awarded.values()) / total, answer=state.output.completion[:2000], metadata={"awarded": awarded})

    return score


@scorer(metrics=[mean(), stderr()])
def numeric_scorer():
    """Fraction of numeric-check points passed (exact, no model). Items without checks score 1."""

    async def score(state: TaskState, target: Target) -> Score:
        res = score_numeric(state.metadata["item"], state.output.completion)
        if not res:
            return Score(value=1.0, explanation="no numeric checks")
        got = sum(r.points for r in res if r.passed)
        return Score(
            value=got / sum(r.points for r in res),
            explanation="; ".join(f"{r.name}: got {r.got}, want {r.expected}" for r in res),
        )

    return score


@task
def mining_eval(split: str = "public", category: str | None = None, grader: str | None = None) -> Task:
    return Task(
        dataset=MemoryDataset(_samples(split, category)),
        solver=[system_message(CANDIDATE_SYSTEM), generate()],
        scorer=[rubric_scorer(grader), numeric_scorer()],
    )

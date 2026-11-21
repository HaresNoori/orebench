"""Scoring: exact numeric checks (no model involved) and rubric grading by an LLM judge."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .schema import close_enough

FINAL_RE = re.compile(r"FINAL_JSON\s*:?\s*(\{.*?\})", re.DOTALL)
NUM_RE = re.compile(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)?(?:\.\d+)?(?:[eE][-+]?\d+)?")


# --------------------------------------------------------------------------
# Numeric extraction
# --------------------------------------------------------------------------
def parse_number(raw) -> float | None:
    """Parse 538.2, "538.2 koz", "1,234.5", "12.5%", "1.2e3", "US$ 45.6M" -> float.

    Thousands separators are removed; units, currency symbols and a trailing % are ignored
    (the % sign is not divided out: items state their unit). Returns None if no number.
    """
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, str):
        return None
    s = raw.strip().replace("−", "-").replace(" ", " ")
    for m in NUM_RE.finditer(s):
        tok = m.group(0)
        if not tok or not any(ch.isdigit() for ch in tok):
            continue
        try:
            return float(tok.replace(",", ""))
        except ValueError:
            continue
    return None


def extract_final(response: str) -> dict:
    """Return the dict from the last FINAL_JSON line, or {} if none parses."""
    matches = FINAL_RE.findall(response or "")
    for blob in reversed(matches):
        try:
            obj = json.loads(blob)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            # tolerate single quotes / trailing commas from sloppy outputs
            fixed = re.sub(r",\s*}", "}", blob.replace("'", '"'))
            try:
                obj = json.loads(fixed)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    return {}


def extract_value(response: str, name: str) -> float | None:
    final = extract_final(response)
    if name in final:
        return parse_number(final[name])
    # fallback: "name = 123.4" or "name: 123.4" anywhere in the text (last occurrence)
    hits = re.findall(rf"\b{re.escape(name)}\b\s*[:=]\s*([^\n,;]+)", response or "")
    for h in reversed(hits):
        v = parse_number(h)
        if v is not None:
            return v
    return None


@dataclass
class NumericResult:
    name: str
    expected: float
    got: float | None
    passed: bool
    points: int


def score_numeric(item: dict, response: str) -> list[NumericResult]:
    out = []
    for c in item.get("numeric_checks", []):
        got = extract_value(response, c["name"])
        ok = got is not None and close_enough(got, float(c["value"]), c.get("rel_tol"), c.get("abs_tol"))
        out.append(NumericResult(c["name"], float(c["value"]), got, ok, int(c.get("points", 2))))
    return out


# --------------------------------------------------------------------------
# Rubric judging
# --------------------------------------------------------------------------
JUDGE_SYSTEM = (
    "You are a strict expert grader for a mining geoscience and mining finance benchmark. "
    "You grade a candidate answer against a reference answer and a rubric. Award a criterion's "
    "points only if the candidate clearly and correctly makes that point; partial credit is "
    "allowed in whole points. Do not reward length, confidence or general mining vocabulary. "
    "A correct point stated alongside a contradicting error earns nothing. Reply with JSON only."
)


def judge_prompt(item: dict, response: str) -> str:
    rubric = "\n".join(f"- {r['id']} ({r['points']} pts): {r['criterion']}" for r in item["rubric"])
    return (
        f"TASK GIVEN TO THE CANDIDATE:\n{item['prompt']}\n\n"
        f"REFERENCE ANSWER (expert):\n{item['reference_answer']}\n\n"
        f"RUBRIC:\n{rubric}\n\n"
        f"CANDIDATE ANSWER:\n<<<\n{response}\n>>>\n\n"
        'Return JSON of the form {"criteria": [{"id": "r1", "awarded": 0, "reason": "..."}]} '
        "with one entry per rubric criterion, awarded between 0 and that criterion's points."
    )


def parse_judge(text: str, item: dict) -> dict[str, int]:
    """Parse judge JSON into {criterion_id: awarded}, clamped to [0, points]. Missing = 0."""
    pts = {r["id"]: int(r["points"]) for r in item["rubric"]}
    awarded = {rid: 0 for rid in pts}
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return awarded
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return awarded
    for c in obj.get("criteria", []) if isinstance(obj, dict) else []:
        rid = c.get("id") if isinstance(c, dict) else None
        if rid in pts:
            v = parse_number(c.get("awarded"))
            if v is not None:
                awarded[rid] = int(max(0, min(pts[rid], round(v))))
    return awarded


_STOP = set(
    "a an the and or of to in on at for by with is are was were be been it its this that as from "
    "not no but if so than then which who into per can will would should may might has have had do "
    "does each both all any".split()
)


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 2}


class MockJudge:
    """Offline judge for dry runs: awards each criterion in proportion to how much of the
    reference answer's content vocabulary the candidate recalls. It exists only to exercise
    the pipeline without keys; it is not a substitute for an LLM or human grader."""

    name = "mock:overlap-judge"

    def grade(self, item: dict, response: str) -> dict[str, int]:
        ref = _content_words(item["reference_answer"])
        got = _content_words(response)
        recall = len(ref & got) / len(ref) if ref else 0.0
        frac = 1.0 if recall >= 0.9 else (0.0 if recall < 0.3 else (recall - 0.3) / 0.6)
        return {r["id"]: int(round(r["points"] * frac)) for r in item["rubric"]}


class ReplayJudge:
    """Grades from judge outputs recorded elsewhere: one file per item, <dir>/<item_id>.json,
    holding the judge's raw reply to judge_prompt(). Lets a judge run outside this harness
    (for example in an agent session) while parsing and scoring stay identical."""

    def __init__(self, directory: str, label: str = "replay-judge"):
        from pathlib import Path

        self.directory = Path(directory)
        self.label = label

    @property
    def name(self) -> str:
        return self.label

    def grade(self, item: dict, response: str) -> dict[str, int]:
        f = self.directory / f"{item['id']}.json"
        if not f.exists():
            from .providers import ProviderError

            raise ProviderError(f"no recorded judgement for {item['id']}")
        return parse_judge(f.read_text(encoding="utf-8"), item)


class LLMJudge:
    def __init__(self, provider, max_tokens: int = 1500):
        self.provider = provider
        self.max_tokens = max_tokens

    @property
    def name(self) -> str:
        return self.provider.name

    def grade(self, item: dict, response: str) -> dict[str, int]:
        text = self.provider.complete(JUDGE_SYSTEM, judge_prompt(item, response), self.max_tokens)
        return parse_judge(text, item)


@dataclass
class ItemScore:
    item_id: str
    category: str
    difficulty: int
    rubric_awarded: dict[str, int]
    rubric_max: int
    numeric: list[NumericResult] = field(default_factory=list)
    run: int = 1

    @property
    def earned(self) -> int:
        return sum(self.rubric_awarded.values()) + sum(n.points for n in self.numeric if n.passed)

    @property
    def available(self) -> int:
        return self.rubric_max + sum(n.points for n in self.numeric)

    @property
    def pct(self) -> float:
        return 100.0 * self.earned / self.available if self.available else 0.0


def score_item(item: dict, response: str, judge) -> ItemScore:
    return ItemScore(
        item_id=item["id"],
        category=item["category"],
        difficulty=item["difficulty"],
        rubric_awarded=judge.grade(item, response),
        rubric_max=sum(int(r["points"]) for r in item["rubric"]),
        numeric=score_numeric(item, response),
    )

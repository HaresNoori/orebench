"""Item schema, validation and a restricted arithmetic evaluator.

Every benchmark item is one JSON object per line in a ``.jsonl`` file.
``validate_item`` returns a list of human-readable problems (empty = valid).
"""
from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any

CATEGORIES = {
    "RES": "Resource and reserve statement reading",
    "FLAW": "Fatal flaws in scoping, PEA and PFS studies",
    "GTM": "Grade-tonnage and metal-content arithmetic",
    "COMP": "Comparable-deposit and analogue selection",
    "G2E": "Geology-to-economics links",
    "ESG": "Permitting, tenure and ESG red flags",
    "DRILL": "Drill-programme and QA/QC critique",
    "FIN": "Financing, offtake, streams and royalties",
}

SPLITS = ("public", "private")
STATUS_DRAFT = "DRAFT-FOR-HARES-REVIEW"
STATUSES = (STATUS_DRAFT, "REVIEWED")
SCENARIO_TYPES = ("hypothetical", "public-report")
ID_RE = re.compile(r"^(?P<cat>[A-Z0-9]+)-(?P<split>[PH])-(?P<num>\d{3})$")
NUMERIC_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

REQUIRED = {
    "id": str,
    "category": str,
    "split": str,
    "status": str,
    "difficulty": int,
    "scenario_type": str,
    "prompt": str,
    "reference_answer": str,
    "rubric": list,
    "numeric_checks": list,
    "sources": list,
    "review_notes": str,
}


# --------------------------------------------------------------------------
# Restricted arithmetic evaluator (no eval(); numbers and + - * / ** only,
# plus a small whitelist of math functions).
# --------------------------------------------------------------------------
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
}


def safe_eval(expr: str) -> float:
    """Evaluate a pure arithmetic expression safely."""

    def _ev(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left, right = _ev(node.left), _ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("exponent too large")
            return _BINOPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](_ev(node.operand))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS
            and not node.keywords
        ):
            return _FUNCS[node.func.id](*[_ev(a) for a in node.args])
        raise ValueError(f"disallowed expression element: {ast.dump(node)[:60]}")

    return float(_ev(ast.parse(expr, mode="eval")))


def close_enough(got: float, want: float, rel_tol: float | None, abs_tol: float | None) -> bool:
    return math.isclose(got, want, rel_tol=rel_tol or 0.0, abs_tol=abs_tol or 0.0)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def validate_item(item: Any) -> list[str]:
    errs: list[str] = []
    if not isinstance(item, dict):
        return ["item is not a JSON object"]
    iid = item.get("id", "<no id>")

    for key, typ in REQUIRED.items():
        if key not in item:
            errs.append(f"{iid}: missing field '{key}'")
        elif not isinstance(item[key], typ) or (typ is int and isinstance(item[key], bool)):
            errs.append(f"{iid}: field '{key}' must be {typ.__name__}")
    if errs:
        return errs

    m = ID_RE.match(item["id"])
    if not m:
        errs.append(f"{iid}: id must look like CAT-P-001 (public) or CAT-H-001 (held-out)")
    else:
        if m["cat"] != item["category"]:
            errs.append(f"{iid}: id prefix does not match category")
        if (m["split"] == "P") != (item["split"] == "public"):
            errs.append(f"{iid}: id split letter does not match split")

    if item["category"] not in CATEGORIES:
        errs.append(f"{iid}: unknown category {item['category']}")
    if item["split"] not in SPLITS:
        errs.append(f"{iid}: split must be one of {SPLITS}")
    if item["status"] not in STATUSES:
        errs.append(f"{iid}: status must be one of {STATUSES}")
    if not 1 <= item["difficulty"] <= 3:
        errs.append(f"{iid}: difficulty must be 1, 2 or 3")
    if item["scenario_type"] not in SCENARIO_TYPES:
        errs.append(f"{iid}: scenario_type must be one of {SCENARIO_TYPES}")
    if item["scenario_type"] == "hypothetical" and "hypothetical" not in item["prompt"].lower():
        errs.append(f"{iid}: hypothetical scenarios must say 'hypothetical' in the prompt")
    if len(item["prompt"]) < 80:
        errs.append(f"{iid}: prompt is too short")
    if len(item["reference_answer"]) < 80:
        errs.append(f"{iid}: reference_answer is too short")

    # Rubric
    if not 3 <= len(item["rubric"]) <= 8:
        errs.append(f"{iid}: rubric needs 3-8 criteria")
    seen: set[str] = set()
    for r in item["rubric"]:
        if not isinstance(r, dict) or not {"id", "criterion", "points"} <= set(r):
            errs.append(f"{iid}: rubric entries need id, criterion, points")
            continue
        if r["id"] in seen:
            errs.append(f"{iid}: duplicate rubric id {r['id']}")
        seen.add(r["id"])
        if not isinstance(r["points"], int) or isinstance(r["points"], bool) or not 1 <= r["points"] <= 5:
            errs.append(f"{iid}: rubric {r['id']} points must be an int 1-5")
        if not isinstance(r["criterion"], str) or len(r["criterion"]) < 15:
            errs.append(f"{iid}: rubric {r['id']} criterion too short")

    # Numeric checks
    names: set[str] = set()
    for n in item["numeric_checks"]:
        if not isinstance(n, dict) or not {"name", "value", "unit", "derivation"} <= set(n):
            errs.append(f"{iid}: numeric_checks need name, value, unit, derivation")
            continue
        if not NUMERIC_NAME_RE.match(str(n["name"])):
            errs.append(f"{iid}: numeric name '{n['name']}' must be snake_case")
        if n["name"] in names:
            errs.append(f"{iid}: duplicate numeric name {n['name']}")
        names.add(n["name"])
        if not isinstance(n["value"], (int, float)) or isinstance(n["value"], bool):
            errs.append(f"{iid}: numeric {n['name']} value must be a number")
            continue
        rel, absol = n.get("rel_tol"), n.get("abs_tol")
        if rel is None and absol is None:
            errs.append(f"{iid}: numeric {n['name']} needs rel_tol or abs_tol")
        try:
            got = safe_eval(n["derivation"])
        except Exception as exc:  # noqa: BLE001
            errs.append(f"{iid}: numeric {n['name']} derivation invalid ({exc})")
            continue
        if not close_enough(got, float(n["value"]), rel, absol):
            errs.append(f"{iid}: numeric {n['name']} derivation gives {got:.6g}, value is {n['value']}")
        pts = n.get("points", 2)
        if not isinstance(pts, int) or isinstance(pts, bool) or not 1 <= pts <= 5:
            errs.append(f"{iid}: numeric {n['name']} points must be an int 1-5")
    if item["category"] == "GTM" and not item["numeric_checks"]:
        errs.append(f"{iid}: GTM items need at least one numeric check")

    # Sources
    if not item["sources"]:
        errs.append(f"{iid}: at least one source is required")
    for s in item["sources"]:
        if not isinstance(s, dict) or "citation" not in s or "verified" not in s:
            errs.append(f"{iid}: sources need citation and verified")
        elif not isinstance(s["verified"], bool):
            errs.append(f"{iid}: source 'verified' must be true or false")
        elif s["verified"] and not s.get("url"):
            errs.append(f"{iid}: a verified source needs a url")
    return errs

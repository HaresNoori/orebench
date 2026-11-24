import json
from collections import Counter
from pathlib import Path

import pytest

from mgeval import providers
from mgeval.cli import main
from mgeval.items import PRIVATE_DIR, ROOT, check_items, jaccard, load_jsonl, load_split
from mgeval.runner import build_prompt
from mgeval.schema import CATEGORIES, STATUS_DRAFT, safe_eval, validate_item
from mgeval.scoring import MockJudge, extract_final, extract_value, parse_judge, parse_number, score_item

EXAMPLE = load_jsonl(ROOT / "docs" / "example_item.jsonl")[0]


# ---------------------------------------------------------------- numbers
@pytest.mark.parametrize(
    "raw,want",
    [
        (538.2, 538.2),
        ("538.2", 538.2),
        ("538.2 koz", 538.2),
        ("1,234.5", 1234.5),
        ("12,400,000 t", 12400000.0),
        ("12.5%", 12.5),
        ("1.2e3", 1200.0),
        ("US$ 45.6M", 45.6),
        ("-3.4", -3.4),
        ("−3.4", -3.4),
        ("n/a", None),
        (True, None),
        (None, None),
    ],
)
def test_parse_number(raw, want):
    assert parse_number(raw) == want


def test_extract_final_takes_last_block_and_tolerates_sloppy_json():
    text = 'draft FINAL_JSON: {"a": 1}\n...\nFINAL_JSON: {\'a\': 2, }'
    assert extract_final(text) == {"a": 2}
    assert extract_final("no block here") == {}


def test_extract_value_fallback_without_final_json():
    assert extract_value("so indicated_contained_koz = 538.2 koz overall", "indicated_contained_koz") == 538.2
    assert extract_value("nothing", "x") is None


def test_numeric_tolerance_edges():
    item = json.loads(json.dumps(EXAMPLE))
    target = item["numeric_checks"][0]  # 538.2, rel_tol 0.005
    inside = target["value"] * 1.0049
    outside = target["value"] * 1.0060
    for v, ok in ((inside, True), (outside, False)):
        resp = "FINAL_JSON: " + json.dumps({target["name"]: v})
        sc = score_item(item, resp, MockJudge())
        assert sc.numeric[0].passed is ok


# ---------------------------------------------------------------- safe eval
def test_safe_eval_arithmetic_and_whitelist():
    assert safe_eval("12.4e6 * 1.35 / 31.1035 / 1000") == pytest.approx(538.2, rel=1e-3)
    assert safe_eval("max(1, 2) + sqrt(16)") == 6.0
    for bad in ("__import__('os')", "open('x')", "a + 1", "[1][0]", "2 ** 1000"):
        with pytest.raises(Exception):
            safe_eval(bad)


# ---------------------------------------------------------------- schema
def test_example_item_is_valid():
    assert validate_item(EXAMPLE) == []


def test_validator_catches_wrong_derivation_and_missing_hypothetical():
    item = json.loads(json.dumps(EXAMPLE))
    item["numeric_checks"][0]["value"] = 600.0
    item["prompt"] = item["prompt"].replace("hypothetical", "notional")
    errs = " ".join(validate_item(item))
    assert "derivation gives" in errs
    assert "hypothetical" in errs


def test_near_duplicate_detection():
    a = json.loads(json.dumps(EXAMPLE))
    b = json.loads(json.dumps(EXAMPLE))
    b["id"] = "GTM-P-002"
    b["prompt"] = b["prompt"].replace("12.4", "15.0").replace("1.35", "2.10")
    assert any("near-duplicate" in e for e in check_items([a, b]))
    assert jaccard("one two three four five six", "seven eight nine ten eleven twelve") == 0.0


# ---------------------------------------------------------------- judge parsing
def test_parse_judge_clamps_and_defaults():
    text = 'Here: {"criteria": [{"id": "r1", "awarded": 9}, {"id": "r2", "awarded": -1}, {"id": "zz", "awarded": 3}]}'
    got = parse_judge(text, EXAMPLE)
    assert got == {"r1": 2, "r2": 0, "r3": 0, "r4": 0}
    assert parse_judge("not json", EXAMPLE) == {"r1": 0, "r2": 0, "r3": 0, "r4": 0}


def test_build_prompt_lists_numeric_keys():
    p = build_prompt(EXAMPLE)
    assert p.startswith(EXAMPLE["prompt"])
    for c in EXAMPLE["numeric_checks"]:
        assert f'"{c["name"]}"' in p
    assert "FINAL_JSON" in p


# ---------------------------------------------------------------- providers (no network)
def test_provider_request_shapes(monkeypatch):
    calls = []

    def fake_post(url, headers, body, **kw):
        calls.append((url, headers, body))
        if "anthropic" in url:
            return {"content": [{"type": "text", "text": "A"}]}
        if "openai" in url:
            return {"choices": [{"message": {"content": "O"}}]}
        return {"candidates": [{"content": {"parts": [{"text": "G"}]}}]}

    monkeypatch.setattr(providers, "_post_json", fake_post)
    for env in providers.KEY_ENV.values():
        monkeypatch.setenv(env, "test-key")
    assert providers.make_provider("anthropic:m1").complete("s", "p", 10) == "A"
    assert providers.make_provider("openai:m2").complete("s", "p", 10) == "O"
    assert providers.make_provider("google:m3").complete("s", "p", 10) == "G"
    assert calls[0][2]["model"] == "m1" and calls[0][2]["system"] == "s"
    assert calls[1][2]["messages"][0]["role"] == "system"
    assert "m3:generateContent" in calls[2][0]


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(providers.ProviderError):
        providers.make_provider("anthropic:m").complete("s", "p", 10)


def test_bad_model_spec():
    with pytest.raises(ValueError):
        providers.make_provider("no-colon")
    with pytest.raises(ValueError):
        providers.make_provider("acme:model")


# ---------------------------------------------------------------- item banks
def test_public_items_valid_and_draft():
    items = load_split("public")
    assert items, "public sample is empty"
    assert check_items(items) == []
    assert all(it["split"] == "public" for it in items)
    assert all(it["status"] == STATUS_DRAFT for it in items)
    assert {it["category"] for it in items} == set(CATEGORIES)


def test_public_sample_size():
    assert 28 <= len(load_split("public")) <= 34


@pytest.mark.skipif(not PRIVATE_DIR.exists() or not any(PRIVATE_DIR.glob("*.jsonl")), reason="held-out bank not present (public clone)")
def test_private_bank_valid_and_independent():
    private = load_split("private")
    assert 140 <= len(private) <= 160
    assert all(it["split"] == "private" for it in private)
    assert check_items(load_split("all")) == []  # includes cross-split near-duplicate check
    assert set(Counter(it["category"] for it in private)) == set(CATEGORIES)


def test_private_dir_is_gitignored():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "private/" in text.splitlines()


# ---------------------------------------------------------------- end to end
def test_dry_run_end_to_end(tmp_path, capsys):
    rc = main(["--dry-run", "--split", "public", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "DRY RUN PASSED" in out
    for f in ("responses.jsonl", "scores.csv", "summary.json", "results.md"):
        assert (tmp_path / f).exists()


def test_inspect_backend_builds_task():
    pytest.importorskip("inspect_ai")
    from mgeval.inspect_task import mining_eval

    t = mining_eval(split="public")
    assert len(t.dataset) == len(load_split("public"))


def test_replay_provider_and_parallel_run(tmp_path):
    items = load_split("public")[:4]
    rec = tmp_path / "answers.jsonl"
    with rec.open("w", encoding="utf-8") as fh:
        for it in items[:3]:
            final = {c["name"]: c["value"] for c in it["numeric_checks"]}
            fh.write(json.dumps({"item_id": it["id"], "response": it["reference_answer"] + "\nFINAL_JSON: " + json.dumps(final)}) + "\n")
    from mgeval.runner import run

    cand = providers.ReplayProvider(str(rec), "replayed")
    summary = run(items, [cand], MockJudge(), tmp_path / "out", workers=3, log=lambda *a: None)
    assert summary["models"]["replayed"]["items"] == 3
    assert summary["models"]["replayed"]["overall_pct"] == 100.0
    assert len(summary["errors"]) == 1  # the fourth item has no recorded answer


def test_cli_provider_specs():
    p = providers.make_provider("codex-cli:default@medium")
    assert isinstance(p, providers.CodexCLIProvider) and p.reasoning_effort == "medium"
    assert isinstance(providers.make_provider("claude-cli:default"), providers.ClaudeCLIProvider)


def test_replay_judge(tmp_path):
    from mgeval.scoring import ReplayJudge

    (tmp_path / f"{EXAMPLE['id']}.json").write_text('{"criteria": [{"id": "r1", "awarded": 2}, {"id": "r3", "awarded": 1}]}', encoding="utf-8")
    j = ReplayJudge(str(tmp_path), "j")
    assert j.grade(EXAMPLE, "x") == {"r1": 2, "r2": 0, "r3": 1, "r4": 0}
    other = dict(EXAMPLE, id="GTM-P-999")
    with pytest.raises(providers.ProviderError):
        j.grade(other, "x")


def test_multi_run_and_bootstrap_ci(tmp_path):
    from mgeval.runner import bootstrap_ci, run

    items = load_split("public")[:6]
    summary = run(items, [providers.make_provider("mock:reference")], MockJudge(), tmp_path, runs=3,
                  log=lambda *a: None)
    row = summary["models"]["mock:reference"]
    assert row["runs"] == 3 and row["items"] == 6
    assert row["run_pcts"] == [100.0, 100.0, 100.0] and row["run_sd"] == 0.0
    assert row["ci95_items"] == [100.0, 100.0]
    lo, hi = bootstrap_ci([(1, 2), (2, 2), (0, 2), (2, 2)], reps=500, seed=1)
    assert 0.0 <= lo <= 62.5 <= hi <= 100.0
    assert bootstrap_ci([(1, 2)] * 5) == (50.0, 50.0)
    assert "95% CI" in (tmp_path / "results.md").read_text(encoding="utf-8")


def test_build_prompt_includes_document_extract():
    from mgeval.runner import build_prompt
    item = {"prompt": "Task text here.", "document_extract": "Extract body.", "numeric_checks": []}
    p = build_prompt(item)
    assert p.index("Extract body.") < p.index("Task text here.")
    assert build_prompt({"prompt": "Plain.", "numeric_checks": []}) == "Plain."

# OreBench

**Can a frontier model sign off as a Competent Person?**

OreBench is an expert-written benchmark of mining geoscience and mining finance reasoning:
reading a JORC or NI 43-101 resource statement, finding the flaw in a scoping study, getting
contained metal right, judging a drill intercept, and naming the risk that actually stops a
project.

> **Status: v0.1, expert review in progress.** Items move from `EXPERT-REVIEW-PENDING` to
> `REVIEWED` as each is signed off. Preliminary results for three
> frontier models are in [Results](#results).

## What this benchmark tests

A fluent mining answer and a correct one often differ. Resource statements, technical reports
and feasibility studies decide where billions of dollars of capital go, and they are governed
by reporting codes whose meaning depends on practice, not vocabulary. OreBench is built so a
general-purpose answer loses points. Each item hides the mistake a generalist makes and a
Competent Person would not:

- adding Inferred to Indicated ounces and calling the total "recoverable gold";
- accepting a resource with no pit-shell or stope constraint as having "reasonable prospects";
- converting alluvial tonnes and grade with two different densities;
- applying recovery twice, or using avoirdupois instead of troy ounces;
- treating a spectacular intercept as meaningful without true width, core recovery or QA/QC;
- reading a gold stream as free capital rather than a sale of future revenue;
- listing ten generic ESG risks instead of the one tenure or water issue that stops the
  permit.

## Why a mining eval

Models are already being used to summarise technical reports, screen deals and support
exploration targeting. As far as a survey of public benchmarks shows (November 2026), none
tests this ground:

| Existing benchmark | Covers | Gap OreBench fills |
|---|---|---|
| GeoBench, from the K2 geoscience LLM work (arXiv 2306.05064) | Geoscience exam questions (NPEE, AP) | No resource reporting, mine economics or finance |
| EarthSE (arXiv 2505.17139) | Broad earth-science knowledge and reasoning | No mining codes, due diligence or deal reasoning |
| FormationEval (arXiv 2601.02158) | Petroleum geoscience questions | Hard-rock and alluvial mining not covered |
| MineBench, from the MineAgent work (arXiv 2412.17339) | Remote-sensing mineral exploration | No reporting codes, studies or finance |

A wider survey with full citations is in [`RELATED_WORK.md`](RELATED_WORK.md). It found no
open text benchmark for hard-rock mining, resource reporting or mining finance.

OreBench is, to the author's knowledge, the first public benchmark built on the JORC Code,
NI 43-101 / CIM and S-K 1300 practice, together with mining project finance (streams,
royalties, debt sizing, P/NAV).

## What is in the box

| | |
|---|---|
| **Taxonomy** | 8 categories: resource statements, study fatal flaws, grade-tonnage arithmetic, comparable deposits, geology-to-economics, permitting and ESG, drill-programme and QA/QC critique, financing and streams. See [`TAXONOMY.md`](TAXONOMY.md) |
| **Public sample** | 30 items in [`items/public/`](items/public/), each with a prompt, an expert reference answer, a weighted rubric and exact numeric checks |
| **Held-out bank** | About 150 further items kept private so scores can't be gamed by training on them. Available to evaluation teams on request |
| **Harness** | Dependency-free Python for Anthropic, OpenAI and Google models, plus an optional [Inspect](https://inspect.aisi.org.uk/) backend |

## Method

1. **Practitioner-written items.** Each item encodes a judgement made in real technical-report
   and due-diligence work. Projects are **hypothetical** by default, so no claim is made about
   any real company. Citations point to the public standards, and each one is flagged as
   checked against the primary document or not.
2. **Weighted expert rubrics.** Each item has 3-8 single, checkable criteria, with the points
   placed on the catch that matters. Long, confident answers that miss it score poorly.
3. **Exact numeric checks, no model involved.** The model reports its numbers on a fixed
   `FINAL_JSON` line, and each is compared to the reference within a stated tolerance. Every
   reference value has an arithmetic derivation that the validator re-evaluates with a
   restricted parser.
4. **Cross-vendor LLM judge.** The judge sees the task, the reference answer and the rubric,
   and should come from a different vendor than the model under test. A sample of its grades
   is meant to be audited by hand.
5. **Held-out discipline.** The private bank is never published. The validator rejects
   held-out items that are near-copies of public ones (word 5-gram Jaccard overlap).

Item score = points earned / points available. Results are reported overall, by category and
by numeric pass rate.

## Quick start

```bash
python -m pip install pytest      # the harness has no runtime dependencies
python -m pytest -q                # tests; pass without the private bank present
python -m mgeval --dry-run         # whole pipeline offline: no keys, no network
```

The dry run sends two mock "models" through the whole pipeline. One returns the reference
answers and the other returns fluent filler. The scorer must rate the first near 100% and the
second near 0%. **Dry-run scores are not model results.**

**Live run.** Keys are read from `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `GOOGLE_API_KEY` at
call time and never stored.

```bash
python -m mgeval --check-keys
python -m mgeval --split public \
  --model anthropic:<model-id> --model openai:<model-id> --model google:<model-id> \
  --judge openai:<judge-model-id>
```

Add `--runs 3` to repeat each model and report run-to-run spread; every table carries a
bootstrap 95% confidence interval over items. Each run writes `responses.jsonl`, `scores.csv`, `summary.json` and a `results.md` table to
`results/<timestamp>/`.

**With Inspect** (optional, `pip install inspect-ai`):

```bash
inspect eval mgeval/inspect_task.py --model anthropic/<model-id> \
  -T split=public -T grader=openai/<grader-model-id>
```

## Results

**v0.1 preliminary, via subscription CLIs, n=30, not API, settings not fully controlled.**
Full setup, judge pairing and limits are in [`RESULTS.md`](RESULTS.md).

| Model | Rubric judge (cross-vendor) | Overall | 95% CI (bootstrap over items) | Numeric pass |
|---|---|---|---|---|
| claude-opus-5-5 | gpt-6.1-sol | 96.1% | 94.3-97.9 | 96/97 |
| claude-sonnet-5-5 | gpt-6.1-sol | 95.4% | 93.4-97.3 | 96/97 |
| gpt-6.1-sol | claude-opus-5-5 | 91.3% | 89.1-93.4 | 97/97 |

Single run per model; intervals reflect item sampling only (computed from `results_v0.1/` with
`scripts/summarise_scores.py`). Run-to-run spread needs `--runs N`.

**Finding:** frontier models mostly pass the public sample. It works as a calibration tier:
textbook-level mining reasoning is largely solved. The points they do lose come from
judgement-heavy items: buried study flaws, risk ranking and drill-geometry remedies. Separating
frontier models needs harder, expert-written tasks; the planned held-out *OreBench Hard*
tier is specified in [`HARD_TIER_DESIGN.md`](HARD_TIER_DESIGN.md) (design only; no hard items are published).

## Repository layout

```
TAXONOMY.md               categories, difficulty scale, sources
RESULTS.md                v0.1 preliminary results, judge setup and limits
HARD_TIER_DESIGN.md       design of the held-out Hard tier (no items published)
RELATED_WORK.md           survey of geoscience and mining LLM benchmarks
results_v0.1/             per-item scores and full model answers
CASE_STUDY.md             one-page summary
docs/AUTHORING.md         item format and authoring rules
docs/example_item.jsonl   a complete worked item
items/public/*.jsonl      public sample, one file per category
mgeval/                   harness: schema, providers, scoring, runner, CLI, Inspect backend
scripts/validate_items.py item validator (schema, arithmetic, near-duplicates)
scripts/summarise_scores.py  overall, bootstrap CI and run spread from scores.csv
tests/
```

## Standards and sources

The items are built on public reporting standards and public geoscience: the JORC Code (2012),
NI 43-101 and Form 43-101F1, the CIM Definition Standards (2014), SEC Regulation S-K subpart
1300, the Global Industry Standard on Tailings Management, IFC Performance Standards, and USGS
mineral-deposit-model and assessment concepts.

## Acknowledgements

The optional backend uses [Inspect](https://github.com/UKGovernmentBEIS/inspect_ai) (MIT
licence) from the UK AI Security Institute. Positioning draws on the published benchmarks
cited above.

## Author

**Hares Noori** is a mining geologist and AI-operations practitioner. He works on technical due
diligence for gold, alluvial and diamond projects and builds multi-agent AI workflows. He
designs domain evaluations, rubric-graded expert datasets and model-behaviour assessments for
mining, geoscience and natural-resource finance.

He is open to contract and freelance work on domain evals, expert data and AI for mineral
exploration and mining investment: **hares.noori777@gmail.com**

## Licence

Code: MIT (see [`LICENSE`](LICENSE)). Public benchmark items and taxonomy: CC BY 4.0 (see
[`LICENSE-DATA.md`](LICENSE-DATA.md)). The held-out bank is not distributed.

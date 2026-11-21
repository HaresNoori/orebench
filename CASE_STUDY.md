# Case study: OreBench, a domain evaluation for mining geoscience and mining finance

**Author:** Hares Noori, mining geologist and AI-ops practitioner, hares.noori777@gmail.com

## The problem

Frontier models are being asked to read NI 43-101 technical reports, summarise JORC resource
statements, screen mining deals and support exploration decisions. In this field a plausible
answer can be expensively wrong. Generic benchmarks don't measure whether a model knows that
Inferred ounces can't be added to Indicated and called recoverable, that a 40 g/t intercept over
an unknown true width with 60% core recovery means little, or that a gold stream takes a share
of the operator's revenue rather than giving it free capital.

## What I built

OreBench, a benchmark of expert-written tasks across **8 categories** of practitioner judgement:
resource-statement reading, study fatal flaws, grade-tonnage arithmetic, comparable-deposit
selection, geology-to-economics links, permitting and ESG, drill-programme and QA/QC critique,
and financing and streams.

- **About 180 items in total**: a **30-item public sample** and a **held-out bank of about 150
  items**. The held-out bank stays private, so results can't be gamed by training on it.
- **Every item is a judgement with a trap**, the error a fluent generalist makes and a
  Competent Person would not. Difficulty runs from graduate level up to Competent or Qualified
  Person level.
- **Weighted expert rubrics** put the points on the catch that matters, not on vocabulary or
  length.
- **Exact numeric checks** grade arithmetic without a model, and every reference number has a
  derivation that the validator recomputes.
- **Hypothetical by default.** No claims are made about real companies, and every citation is
  flagged as verified against the primary source or not.

## How it is run

A dependency-free Python harness, with an optional backend on the UK AI Security Institute's
Inspect framework, sends each item to Anthropic, OpenAI and Google models, then
grades the answers with a cross-vendor LLM judge plus the numeric checks. It reports scores by
model, category and difficulty. An offline dry run shows the scorer separates a reference
answer (close to 100%) from fluent filler (close to 0%) before any money is spent on API calls.
Tests cover number parsing, tolerance edges, judge-output parsing, request formats and
near-duplicate detection between the public and private splits.

## Where it sits

Public earth-science benchmarks (GeoBench, EarthSE, FormationEval, MineBench) test general
geoscience, petroleum geoscience or remote-sensing exploration. None tests resource-reporting
codes, study critique or mining finance. That is the gap OreBench fills.

## What it shows

- **Domain depth.** The tasks encode the judgements a practitioner makes in technical
  due diligence on gold, alluvial and diamond projects, not textbook definitions. All scenarios
  are hypothetical or drawn from public sources.
- **Eval craft.** Rubric design, held-out splits, contamination checks, judge-bias controls and
  numeric grading separated from model grading.
- **Engineering.** A clean, tested harness that another team can run in minutes.

## Results (v0.1 preliminary)

On the 30-item public sample, run through subscription tools with cross-vendor judging, scores
were 96.1% for claude-opus-5-5, 95.4% for claude-sonnet-5-5 and 91.3% for gpt-6.1-sol. Frontier
models mostly pass the public tier. The points they lose come from judgement-heavy items:
buried study flaws, risk ranking and drill-geometry remedies. So the value lies in harder,
held-out, expert-written tasks, which is the work I offer. Details and limits are in RESULTS.md.

## What I can do for your team

- Write and review expert eval items and rubrics for mining, geoscience, exploration,
  natural-resource finance and adjacent earth-science fields.
- Design domain benchmarks end to end: taxonomy, items, held-out policy, grading and reporting.
- Red-team model answers on technical reports and investment cases, and turn the failures into
  training or evaluation data.
- Advise mining-AI teams on where model outputs need expert gates.

Contact **hares.noori777@gmail.com** for contract or freelance engagements.

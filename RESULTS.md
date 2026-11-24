# OreBench results

> **v0.1, first release: one run via subscription CLIs, cross-vendor judges, n=30, not API,
> settings not fully controlled.** Run on 21 November 2026 on the 30-item public sample. Read
> the limits below before quoting these numbers.

## Headline: the public sample is a calibration tier

Current frontier models mostly pass the public sample. All three models scored above 90%, and
every reference number was reproduced within tolerance, apart from one rounding case.

| Model (as reported) | Route | Rubric judge | Items | Overall | Numeric pass | RES | FLAW | GTM | COMP | G2E | ESG | DRILL | FIN |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | Claude Code agent | gpt-6.1-sol (Codex CLI) | 30 | **96.1%** | 96/97 | 96 | 93 | 100 | 98 | 96 | 93 | 96 | 97 |
| claude-sonnet-5-5 | Claude Code agent | gpt-6.1-sol (Codex CLI) | 30 | **95.4%** | 96/97 | 93 | 93 | 100 | 96 | 97 | 96 | 92 | 96 |
| gpt-6.1-sol | Codex CLI (`codex exec`), default reasoning | claude-opus-5-5 (Claude Code agent) | 30 | **91.3%** | 97/97 | 89 | 94 | 94 | 91 | 93 | 89 | 89 | 90 |

Category cells are percentages of available points (rubric points plus numeric-check points).

**95% confidence intervals (item sampling only).**

| Model | Overall | 95% CI (items) |
|---|---|---|
| claude-opus-5-5 | 96.1% | 94.3–97.9 |
| claude-sonnet-5-5 | 95.4% | 93.4–97.3 |
| gpt-6.1-sol | 91.3% | 89.1–93.4 |

Percentile bootstrap over the 30 items (2,000 resamples, seed 0), computed from `results_v0.1/`
with `scripts/summarise_scores.py`. This was a single run, so the intervals reflect item
sampling only. They do not capture run-to-run or judge variance.

**What this shows.** The public items test whether a model knows the practitioner's catch:
Inferred ounces aggregated as recoverable, unit and density conversions, an unconstrained
resource, a stream mistaken for free capital. Frontier models now catch most of these when the
data are laid out cleanly. That is a useful result in itself. Textbook-level mining reasoning is
largely solved, so a public, single-trap item set can't separate frontier models. The roughly
five points between the models here come almost entirely from the judgement-heavy items.

**Where points were lost.** Across models, the lowest-scoring items were judgement calls, not
arithmetic:
- a scoping-study extract with a buried, decisive flaw among plausible distractors (FLAW-P-001,
  about 79-84% across models);
- a resource-statement reading item (RES-P-002, 82-88%);
- ranking tenure risk against a governance red flag (ESG-P-003, 77-92%);
- equity-dilution and stream-economics framing (FIN-P-004, 86-95%);
- drill-geometry and QA/QC remedies (DRILL-P-001 and DRILL-P-004, 83-94%).

Only 5 of the 30 items were answered perfectly by all three models.

## Next: a hard tier (in design; not part of this release)

Separating frontier models on mining reasoning needs harder, expert-written tasks. The planned
**OreBench Hard** tier is designed around what made the public items discriminate at all. **No
hard-tier items exist in this repository, and none will be published.**

Design principles:
- **Realistic document extracts, not clean vignettes.** Multi-page excerpts in the style of
  technical reports, with tables, footnotes and inconsistencies spread across sections. The
  model has to find the issue, not just recognise it.
- **Several interacting flaws with a required ranking.** Credit goes for identifying which
  issue is decisive for value or permitting, not for listing issues.
- **Competent and Qualified Person-level sign-off decisions.** Would you sign this
  classification, accept this recovery basis, lend against this mine plan?
- **Quantitative chains.** Multi-step calculations, such as cut-off to grade-tonnage to cash
  flow to valuation, where one early convention error propagates. Graded with exact numeric
  checks at each step.
- **Held-out by default.** Kept private and versioned, for evaluation partners only.

## Method and judge setup

- **Items:** the 30 public items in `items/public/`, all still `EXPERT-REVIEW-PENDING`. One fixed
  prompt template per item (`mgeval/runner.py`, `build_prompt`) and one fixed system prompt
  (`CANDIDATE_SYSTEM`). Numbers come back on a `FINAL_JSON` line.
- **Candidates:** no API keys were used. GPT ran locally through the OpenAI Codex CLI
  (`codex exec`, read-only sandbox, empty working directory, the CLI's default reasoning
  effort), and the CLI reported the model as `gpt-6.1-sol`. Claude ran as Claude Code agents on
  the Opus 5.5 and Sonnet 5.5 models. Each agent got only the prompt file and was told to answer
  without code, tools or web access. Each agent answered 10 items in one session.
- **Numeric checks:** exact and model-free. The only numeric miss (both Claude models,
  DRILL-P-003) gave 0.15 against a reference of 0.146. That is a rounding difference at the edge
  of a tight tolerance, an item-calibration issue rather than a reasoning error.
- **Rubric judge, cross-vendor only.** No model graded its own vendor's answers. Claude answers
  were judged by gpt-6.1-sol through the Codex CLI at medium reasoning effort. GPT answers were
  judged by claude-opus-5-5. The judge prompt is `JUDGE_SYSTEM` and `judge_prompt()` in
  `mgeval/scoring.py`.
- **Self-preference check.** Before the cross-vendor rule was applied, GPT's answers had also
  been graded by GPT itself: 92.1%, against 91.3% under the Opus judge. That one comparison
  suggests a small self-preference effect. It is reported for transparency and not used in the
  table.

## Limits (please read)

1. **Not API runs, and settings not fully controlled.** Subscription tools add their own
   system prompts and user-level instructions. Reasoning effort and sampling settings are the
   tools' defaults, not fixed by the harness. Claude agents answered in batches of 10 per
   session, so later answers share context with earlier ones.
2. **Different judges for different vendors.** Avoiding self-judging means the Claude and GPT
   rows were graded by different judges. Compare rows with care. The numeric column is the only
   judge-free comparison.
3. **n = 30, single run, no repeats.** The intervals above cover item sampling only. The Opus
   and Sonnet intervals overlap. The Claude and GPT intervals do not, but those rows were graded
   by different judges, so part of that gap may reflect judge differences.
4. **Items are still under expert review.** Some public items were corrected after
   review. Scores may move as items are signed off.
5. **Gemini and Grok not included.** No Gemini command-line tool was available on the test
   machine, and Grok had no comparable verbatim route.

## Files

`results_v0.1/` holds the per-item scores (`scores_*.csv`) and the full model answers, with
per-criterion grades (`responses_*.jsonl`), for both judge pairings. To reproduce with API keys
instead of subscription tools, see the README Quick start.

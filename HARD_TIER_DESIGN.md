# OreBench Hard: design

**Status: design document. No Hard-tier items are published in this repository, and none will
be.** This document specifies how the tier is built, graded and protected, so evaluation
partners can judge the method before they see any items.

## Why a hard tier

The v0.1 public sample (see `RESULTS.md`) is a calibration tier. Current frontier models score
above 90% on it because each item lays the data out cleanly and contains a single trap. In
practice the difficulty is different. The relevant fact is buried in a long document, several
issues compete for attention, and the expert's job is to decide which one matters and whether to
sign. OreBench Hard targets that gap.

## What makes an item "hard"

An item qualifies for the Hard tier only if it meets **at least three** of these criteria, and the
reviewer records which ones:

| # | Criterion | Meaning |
|---|---|---|
| H1 | **Buried evidence** | The decisive fact sits in a table footnote, an appendix-style section or a cross-reference, not in the question stem |
| H2 | **Competing flaws** | Two to four genuine issues, of which exactly one is decisive for value, classification or permitting. Credit requires the right ranking, with a reason |
| H3 | **Plausible distractors** | At least one statement that looks like a red flag but is acceptable practice in context, and is penalised if flagged as fatal |
| H4 | **Quantitative chain** | Three or more dependent calculation steps, such as cut-off to grade-tonnage to schedule to cash flow to valuation, where an early convention error carries through. Each step has its own numeric check |
| H5 | **Sign-off decision** | The model must commit to a decision a Competent or Qualified Person, lender's engineer or investment committee would make (sign or not, lend or not, classify as what), and defend it |
| H6 | **Cross-domain link** | The decisive issue is only visible by linking two categories, for example mineralogy to recovery to reserve, or tenure terms to schedule to NPV |
| H7 | **Non-obvious convention** | The correct method depends on a reporting or industry convention that is easy to get wrong and is not stated in the prompt (for example in-situ versus recoverable, attributable versus 100%, real versus nominal) |

## Item specification

Each Hard item uses the public item schema (`docs/AUTHORING.md`) plus these fields:

- `hard_criteria`: the list of H-codes the item meets (at least three).
- `document_extract`: 1,500-6,000 words in the style of a technical report, study summary or
  data-room memo, with tables. It is written from scratch for the item. It is never copied from,
  and never close enough to identify, a real filing.
- `decisive_issue` and `distractors`: what the expert answer must rank first, and what it must
  not call fatal.
- `step_checks`: one numeric check per calculation step, each with its own derivation and
  tolerance. A later step is scored against the model's own earlier numbers where the method is
  right ("follow-through" credit), so one slip is not punished twice.
- `decision_key`: the expected decision and the acceptable range of defensible alternatives.
  Items with no defensible single decision are rejected.

### Judgement-heavy categories

The Hard tier keeps the eight public categories but weights them towards judgement:

| Focus | Example task shapes (described, not published) |
|---|---|
| Resource classification sign-off | Would you sign this classification as Competent Person, given spacing, QA/QC and geological continuity evidence spread across sections? |
| Study fatal-flaw ranking | A full study summary with four issues; rank them by impact on value and say which kills the project |
| Data-room red-flag triage | A mixed pack (tenure schedule, drill database summary, metallurgical memo, offtake term sheet); find what a buyer must resolve before signing |
| Lender's-engineer review | Debt sizing, completion test and reserve tail; is the facility bankable as structured? |
| Metallurgy-to-reserve chain | Mineralogy and testwork across domains; what recovery and cut-off should the reserve carry? |
| Valuation from comparables | A peer table with traps (different stages, by-products, attributable basis); build the defensible range |
| Permitting critical path | Licence terms, consultation steps and statutory clocks; what is the realistic first-production date? |
| Alluvial and diamond specifics | Sampling support, size-frequency and price-book reconciliation, recovery efficiency; is the grade claim supportable? |

## Grading

- **Exact numeric checks per step**, model-free, with follow-through credit.
- **A ranking check.** The decisive issue must be ranked first, scored deterministically from a
  required `RANKING:` line.
- **A distractor penalty.** Points are deducted for calling an acceptable-practice item fatal.
- **A rubric judged by two LLM judges from different vendors**, neither from the candidate's
  vendor where possible, with disagreements above a threshold sent to the human expert.
- **Human audit**: the expert re-grades a stratified 20% sample on every release. Judge-human
  agreement is reported as Cohen's kappa per category.
- **Reporting**: mean over at least 3 runs per model, with 95% confidence intervals from a
  bootstrap over items and the run-to-run spread (the harness supports `--runs` and bootstrap
  intervals).

## Held-out protocol

1. **Never public.** Hard items live only in a private store. The public repository holds this
   design, the harness and the schema, never items, reference answers or rubrics.
2. **Access by agreement.** Partners run the tier through one of two routes: the author runs
   their model, or the partner runs it in a sandboxed environment under a written no-training,
   no-retention agreement.
3. **Versioned and rotated.** Each release is frozen and hashed (item-level SHA-256 manifest).
   A share of items is retired and replaced each release, and retired items are never published.
4. **Minimal exposure.** Through API runs, items are sent only to providers whose terms exclude
   training on the content, with retention disabled where offered. Each exposure is logged by item
   hash, provider, model and date.

## Contamination controls

- **Written from scratch.** Every extract and number is authored for the item. Real filings are
  used only as style references and never paraphrased closely enough to identify.
- **Canary string.** Every private item file carries a unique canary GUID. Presence of the canary
  in a model's output or training-data disclosures signals leakage.
- **Exposure ledger.** Every run is recorded (item hash, model, provider, date, route), so any
  leak can be traced to a release and route.
- **Leakage probes.** Before scoring a new model, ask it to complete the opening of item
  extracts and to recall item-specific invented names. Anything above chance marks the release
  as compromised and triggers rotation.
- **Overlap checks.** Word 5-gram overlap against the public sample and against prior releases
  (already enforced by the validator), plus a check that no invented project name collides with
  a real one.
- **Parameter perturbation.** Each item has seeded numeric variants. A model that scores well on
  the canonical numbers but poorly on variants is flagged as possibly memorised.

## Quality bar and review

- Every Hard item is written or approved by a practising mining geologist acting as domain
  expert, then independently reviewed by a second practitioner before release.
- **Acceptance test.** On a pilot run, an item is kept only if it separates something: it is
  answered correctly by a strong practitioner and missed by at least one frontier model. Items
  every frontier model aces move to the calibration tier.
- **Target size per release:** 60-100 Hard items, balanced across the categories above.

## Relationship to the public tier

| | Public (calibration) | Hard (held-out) |
|---|---|---|
| Purpose | Show the method; sanity-check models | Separate frontier models; measure expert-level judgement |
| Item style | One clean vignette, one trap | Long extract, competing flaws, decision required |
| Availability | Open (CC BY 4.0) | Private, by agreement |
| Expected frontier score (v0.1) | Above 90% | Designed to be well below the public tier |

## Author

Designed by Hares Noori, mining geologist and AI-operations practitioner. For evaluation
partnerships or contract work on expert-written evaluations, write to
hares.noori777@gmail.com.

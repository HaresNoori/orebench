# Item authoring guide

Every item is one JSON object on one line of a `.jsonl` file. Public items live in
`items/public/`; held-out items live in `private/items/`, which is git-ignored and never
published. Run `python scripts/validate_items.py <file>` before committing any item.

## Fields

| Field | Type | Rule |
|---|---|---|
| `id` | str | `CAT-P-NNN` for public, `CAT-H-NNN` for held-out (e.g. `GTM-P-001`, `GTM-H-014`) |
| `category` | str | One of `RES FLAW GTM COMP G2E ESG DRILL FIN` (see `TAXONOMY.md`) |
| `split` | str | `public` or `private` |
| `status` | str | `EXPERT-REVIEW-PENDING` until the domain reviewer signs it off, then `REVIEWED` |
| `difficulty` | int | 1 = graduate geologist, 2 = practising professional, 3 = Competent/Qualified Person level |
| `scenario_type` | str | `hypothetical` (invented project; the prompt must say "hypothetical") or `public-report` |
| `prompt` | str | The full task shown to the model. Self-contained; all numbers it needs are in it |
| `reference_answer` | str | What an expert would write. Shows working for any number |
| `rubric` | list | 3-8 criteria: `{"id": "r1", "criterion": "...", "points": 1-5}`. Each criterion is a single checkable claim |
| `numeric_checks` | list | `{"name", "value", "unit", "rel_tol" or "abs_tol", "derivation", "points"}`. `derivation` is a pure arithmetic expression that reproduces `value`; the validator recomputes it |
| `sources` | list | `{"citation", "url", "verified"}`. `verified: true` only if the source was opened and the cited clause/page checked |
| `review_notes` | str | Notes for the reviewer: traps, judgement calls, anything uncertain |

## Rules

1. **Hypothetical by default.** Invented projects avoid any claim about a real company. A
   `public-report` item may only restate what the cited public filing says, with its URL.
2. **No citation from memory presented as verified.** Clause numbers, item numbers and report
   figures that were not checked against the primary document carry `verified: false`.
3. **Numbers must reproduce.** Every numeric check has a `derivation` the validator re-evaluates.
   This proves internal arithmetic consistency only; the reviewer still checks the numbers match
   the prompt and the method is right.
4. **One trap per item is plenty.** Good items test a judgement a practitioner makes (a mixed
   classification, an unconstrained resource, a recovery assumption that does not fit the
   mineralogy), not trivia.
5. **Held-out items are independent.** A private item must not be a number-swapped copy of a
   public one. The validator flags prompts with high word 5-gram overlap.

## Answer format the harness asks for

The harness appends an instruction asking the model to end with one line:

```
FINAL_JSON: {"indicated_contained_koz": 538.2, "inferred_contained_koz": 180.4}
```

using exactly the `name` keys of the item's numeric checks. Units are stated in the instruction.

## Example (abridged)

```json
{"id": "GTM-P-000", "category": "GTM", "split": "public", "status": "EXPERT-REVIEW-PENDING",
 "difficulty": 1, "scenario_type": "hypothetical",
 "prompt": "A hypothetical open-pit gold project reports an Indicated Mineral Resource of 12.4 Mt at 1.35 g/t Au and an Inferred Mineral Resource of 5.1 Mt at 1.10 g/t Au ...",
 "numeric_checks": [{"name": "indicated_contained_koz", "value": 538.2, "unit": "koz Au",
   "rel_tol": 0.005, "derivation": "12.4e6 * 1.35 / 31.1035 / 1000", "points": 2}],
 "...": "..."}
```

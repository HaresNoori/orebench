# Task taxonomy

Eight categories, each testing a judgement that a mining geologist, Competent Person or
mining-finance analyst makes in practice. Items are written so that a fluent but shallow answer
loses points: the rubric rewards the specific catch, not general mining vocabulary.

| Code | Category | What it tests | Typical failure the item is built to expose |
|---|---|---|---|
| `RES` | Resource and reserve statement reading | Reading a JORC Code (2012) or NI 43-101 / CIM statement: classification, cut-off grade, reasonable prospects for eventual economic extraction, the resource-to-reserve boundary, reporting conventions | Treating Inferred as bankable; missing an unconstrained resource; adding Measured, Indicated and Inferred without comment; confusing in-situ and recoverable metal |
| `FLAW` | Fatal flaws in scoping, PEA and PFS studies | Spotting the assumption that breaks a study: Inferred-heavy mine plans, recovery not supported by testwork, missing water or power, capital that ignores infrastructure, price decks out of line | Summarising the study instead of challenging it; accepting headline NPV/IRR at face value |
| `GTM` | Grade-tonnage and metal-content arithmetic | Contained and recoverable metal, unit conversions (g/t, oz, ppm, %, lb, carats), cut-off sensitivity, grade-tonnage curve reading, dilution and ore-loss maths, equivalent-grade formulas | Troy vs avoirdupois ounces; percent vs ppm; applying recovery twice; ignoring payability in metal-equivalent grades |
| `COMP` | Comparable-deposit and analogue selection | Choosing defensible analogues by deposit model, grade, size, depth, metallurgy and jurisdiction; using grade-tonnage models in the spirit of USGS mineral-deposit-model and assessment work | Picking famous deposits instead of comparable ones; comparing across deposit types; ignoring the size-grade trade-off |
| `G2E` | Geology-to-economics links | Translating geological facts into money: refractory vs free-milling ore, strip ratio, dilution, geotechnics, hydrogeology, ore variability, alluvial and diamond recovery issues | Treating grade as the only value driver; missing that mineralogy dictates process route and cost |
| `ESG` | Permitting, tenure and ESG red flags | Licence status and tenure risk, community and land access, water, tailings (GISTM), artisanal mining overlap, protected areas, fiscal regime changes, sanctions and governance | Listing generic ESG points rather than ranking the one that stops the project |
| `DRILL` | Drill-programme and QA/QC critique | Drill spacing versus classification, hole orientation versus structure, sampling and assaying (fire assay, screen fire, nugget effect), CRMs, blanks, duplicates, twinned holes, core recovery | Accepting a headline intercept without checking true width, recovery or QA/QC; ignoring coarse-gold nugget effect |
| `FIN` | Financing, offtake, streams and royalties | Stream and royalty economics, offtake terms, project-finance metrics (NPV, IRR, payback, debt sizing), dilution to equity holders, what a lender or stream buyer would ask | Ignoring that a stream reduces the operator's revenue share; confusing pre-tax and post-tax; mis-sizing debt against cash flow |

## Difficulty

- **1** - graduate geologist or analyst; one concept, mostly arithmetic or definitions.
- **2** - practising professional; two or three interacting factors, one judgement call.
- **3** - Competent Person / Qualified Person level; a realistic study extract with a buried flaw and
  several plausible distractors.

## Scoring

Each item has an expert rubric (3-8 criteria, 1-5 points each) graded by an LLM judge against the
reference answer, and, where numbers matter, exact numeric checks with stated tolerances that are
scored without any model. The item score is points earned over points available. See
`README.md` for the method and `docs/AUTHORING.md` for the item format.

## Sources

Items are hypothetical by default, built on the public reporting standards: the JORC Code (2012
edition), National Instrument 43-101 and Form 43-101F1, the CIM Definition Standards (2014), SEC
Regulation S-K subpart 1300, and the Global Industry Standard on Tailings Management. Grade-tonnage
and analogue items draw on public USGS mineral-deposit-model and assessment work. Any item marked
`public-report` restates only what the cited filing (SEDAR+, ASX, EDGAR) says.

# Related work

This survey was compiled in November 2026. Every entry is cited for positioning only. **No
questions, data or code from any of these works are included in OreBench.** Where a work's
redistribution terms are unclear, it is cited and nothing more.

## Geoscience and mining LLM benchmarks

| Work | What it covers | Relation to OreBench |
|---|---|---|
| **K2 and GeoBench**: Deng et al., *K2: A Foundation Language Model for Geoscience Knowledge Understanding and Utilization*, WSDM 2024, [arXiv:2306.05064](https://arxiv.org/abs/2306.05064); code [github.com/davendw49/k2](https://github.com/davendw49/k2) (Apache-2.0) | A geoscience LLM, and GeoBench, about 1.6k objective and 0.9k subjective questions from graduate-entrance (NPEE) and AP exams | General geoscience exam knowledge. No resource reporting, study critique or mining finance. GeoBench questions are not reused, because their redistribution rights are unclear |
| **GeoGalactica**: Lin et al., [arXiv:2401.00434](https://arxiv.org/abs/2401.00434); [github.com/geobrain-ai/geogalactica](https://github.com/geobrain-ai/geogalactica) (Apache-2.0) | A 30B Galactica model further trained on a geoscience corpus and evaluated on GeoBench | Open-weight geoscience models such as K2 and GeoGalactica are natural **candidate baselines** for a future OreBench run. They have not been run here |
| **GeoSignal**: K2 team, [huggingface.co/datasets/daven3/geosignal](https://huggingface.co/datasets/daven3/geosignal) (Apache-2.0) | A geoscience instruction-tuning set | Training data, not an evaluation. Cited for context |
| **EarthSE**: [arXiv:2505.17139](https://arxiv.org/abs/2505.17139) | Broad earth-science knowledge and reasoning | No mining codes, due diligence or deal reasoning |
| **FormationEval**: Ermilov, [arXiv:2601.02158](https://arxiv.org/abs/2601.02158) | 505 petroleum-geoscience multiple-choice questions across seven domains | Petroleum, not hard-rock or alluvial mining. The design is cited; the data are not used, because the dataset licence is not stated |
| **GR1 / GeoMC-10K**: ACL 2026 Findings, [github.com/xyl-alter/GR1](https://github.com/xyl-alter/GR1) | About 10k geology multiple-choice questions from school and professional exams | Exam-style geology. No licence is declared, so it is cited only |
| **MineAgent / MineBench**: Yu, Shen et al., [arXiv:2412.17339](https://arxiv.org/abs/2412.17339) | A multimodal benchmark for remote-sensing mineral exploration | Image-based exploration. No reporting codes, studies or finance |
| **MiningGPT** ([arXiv:2412.01189](https://arxiv.org/abs/2412.01189)) and a coal-mining QA study ([arXiv:2410.02959](https://arxiv.org/abs/2410.02959)) | A mining-domain LLM and a small coal-mining QA evaluation | No public, rubric-graded benchmark on resource reporting or mine finance was found |
| **PetroBench** ([arXiv:2605.28032](https://arxiv.org/abs/2605.28032)) and **GeoBenchLLM** ([arXiv:2608.07411](https://arxiv.org/abs/2608.07411)) | Petroleum-engineering questions; general geospatial tasks | Different domains |

**The gap.** We found no open, text-based benchmark for hard-rock or alluvial mining,
resource reporting under the JORC Code, NI 43-101 or S-K 1300, mining-study critique, or mining
finance. OreBench is built for that niche. This is a statement about what a survey found, not a
claim that nothing else exists. Corrections are welcome.

## Evaluation tooling

- **Inspect** (UK AI Security Institute), [github.com/UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai),
  MIT licence. OreBench ships an optional Inspect task (`mgeval/inspect_task.py`).
- The design follows common practice in expert-written evaluations: held-out splits,
  contamination checks, rubric grading with a cross-vendor model judge, exact numeric checks
  and bootstrap confidence intervals.

## Standards the items are built on

The JORC Code (2012), NI 43-101 and Form 43-101F1, the CIM Definition Standards (2014), SEC
Regulation S-K subpart 1300, the Global Industry Standard on Tailings Management, IFC
Performance Standards, and USGS mineral-deposit-model and assessment concepts. The items
interpret these standards in invented scenarios and do not reproduce their text.

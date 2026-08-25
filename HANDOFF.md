# Financial AI Assistant Handoff

Last revised: 2026-08-26

## Current boundary

M0–M5.1 are complete and their evidence is retained. The M6 feature/label engineering foundation is implemented locally; check Git status before any work because those changes may still be uncommitted. Do not jump to M7 downstream modeling yet.

The next minimum executable milestone is **M6.1 Taiwan Financial Annotation Protocol**. This is a protocol, data-audit and design milestone only. Do not train MacBERT, fabricate annotations, run downstream prediction, backtest, deploy, or modify working GAS code.

## Verified findings that must not change

English production baseline:

- `ProsusAI/finbert@4556d13015211d73dccd3fdd39d39232506f3e43`
- Stores positive, neutral and negative probabilities plus `positive - negative` score.
- The 12-item manual English set scored about 83.33%; this is sanity/pipeline evidence only, never a formal benchmark.

Taiwan/Chinese diagnostic macro-F1:

- Lexicon: 0.320
- yiyang Chinese FinBERT: 0.357
- bards.ai Chinese finance model: 0.442
- Chinese-to-English translation plus ProsusAI FinBERT: 0.592
- Kenpache multilingual-v2: 0.640

Acceptance gate: macro-F1 at least 0.70 and recall at least 0.60 for every required class. No candidate passed. Formal Chinese sentiment remains unsupported; unsupported text receives no neutral placeholder or fabricated probabilities. The frozen 30-item TWSE-derived set is diagnostic, singly annotated and insufficient for training or publication claims.

Primary evidence:

- `research/evaluation/chinese_sentiment_model_comparison.md`
- `research/evaluation/twse_announcement_sentiment_samples.json`
- `research/evaluation/finbert_manual_error_analysis.md`
- `docs/sentiment_language_strategy.md`

## Revised research contracts

Keep these signal groups distinct:

1. English financial sentiment from validated pinned FinBERT.
2. Taiwan financial event type and entity-specific impact.
3. Historical market reaction derived from future/abnormal returns as offline targets.
4. Price, volume and technical features.
5. Downstream short-horizon direction prediction.

Taiwan labels use a versioned event taxonomy and `POSITIVE`, `NEUTRAL`, `NEGATIVE`, `AMBIGUOUS` impact. Linguistic tone, financial impact and observed price reaction are not interchangeable. MacBERT is a candidate encoder only.

Future return is allowed as a historical reaction target, never as an input available at the event timestamp. A reaction-derived prediction feature may only use older events whose reaction windows completed before the current information cutoff.

## Next task: M6.1

Deliver only:

1. Annotation guideline and inclusion/exclusion rules.
2. Event taxonomy v1 and impact/ambiguous examples.
3. Reviewer, adjudication, agreement and QC procedure.
4. Label/source/taxonomy versioning schema.
5. Copyright, retention and provenance checklist.
6. Time-, event-group- and near-duplicate-safe train/validation/sealed-test protocol.
7. Audit plan for candidate public Traditional Chinese finance datasets.
8. Go/no-go recommendation and minimum reviewed-data requirement for M6.2.

Do not create fake labels. Keep external/full text and large model/data caches in ignored locations. Do not automatically commit or push.

## Architecture and safety

GAS remains a private transitional LINE adapter: receive/route events, call Python, and reply/push Flex messages. Python owns ingestion, deduplication, ticker matching, NLP, features, ML, backtesting, jobs and structured storage. Do not copy old GAS code or secrets into this repository.

Preserve secret management, LINE signature validation plans, ownership checks, private holdings separation, public-demo anonymisation, source traceability and legal short-text retention. The product is a Financial Intelligence Assistant, not an automatic trading or stock-picking system.

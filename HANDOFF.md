# Financial AI Assistant Handoff

Last revised: 2026-08-26

## Current boundary

M0–M5.5 are complete and their evidence is retained. M6 is the active Taiwan dataset/corpus-audit
milestone under a hard zero-human-label constraint: no manual annotation, label review or human
adjudication. The taxonomy, automated-signal protocol, market-reaction protocol, logical schema,
dataset-governance register, dataset-audit CLI, calibration exporter, agreement CLI and tests are
implemented locally. A 60-item Gemini-versus-Codex diagnostic is retained under ignored local
directories as model-stability evidence only. Check Git status because these changes are
uncommitted. Do not start M7 training until an active corpus receives purpose-specific approval.

There is no human gold-set objective. Eland is a **historical candidate — HOLD / excluded from the
active modeling pipeline** because official raw downloads returned HTTP 401, a later live check
returned 404, and the earlier public viewer showed domain contamination. Preserve the rejection
record only: do not rescue, re-audit, train, adapt, vote, evaluate, merge or construct features from
Eland. Do not train a model against AI labels and present agreement with the same label process as
semantic accuracy. Do not deploy, modify working GAS code or make investment-performance claims
before the automated signal experiments pass leakage-safe out-of-sample evaluation.

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

## Historical diagnostic tooling delivered locally

Implemented:

1. `docs/taiwan_financial_annotation_protocol.md`
2. `research/configs/taiwan_event_taxonomy.v1.json`
3. `research/annotation/schema.py`
4. `research/evaluation/taiwan_dataset_audit.py`
5. `research/evaluation/eland_dataset_preliminary_audit.md`
6. `research/evaluation/taiwan_data_source_decisions.md`
7. `research/evaluation/twse_calibration_batch_preparation.md`
8. `jobs/annotation_batch.py` and calibration-selection tests.
9. `jobs/annotation_agreement.py` and Cohen's-kappa tests.
10. Unit tests for schema invariants, taxonomy parity, leakage checks and raw-text omission.
11. `research/evaluation/twse_calibration_round_1_result.md` and protocol v1.1 boundary clarifications.
12. `docs/automated_chinese_text_signal_protocol.md` as the operative zero-human research contract.

## M6 metadata-first source audit completed

Round 1 is complete as an AI-to-AI diagnostic: Gemini 3.1 Pro Reviewer A versus Codex Reviewer B.
Impact raw agreement was 0.766667 with kappa 0.640411; event raw agreement was 0.650000 with kappa
0.533679. Preserve these as stability evidence without human adjudication.

The metadata-first source audit is recorded in
`research/evaluation/taiwan_active_source_metadata_audit.md`. It established:

1. TWSE OpenAPI is accepted for official ingestion/metadata; text training remains conditional.
2. `tw-finance-159M` remains HOLD because gated access, original-publisher rights, temporal lineage,
   duplicates and share-alike model implications remain unresolved.
3. FinMind news is conditional for source/link metadata but HOLD as a reaction-event source until
   timestamp timezone/semantics, duplicates and publisher rights pass.
4. FinMind `TaiwanStockTotalReturnIndex` with `data_id=TAIEX` is accepted as the non-commercial
   research benchmark.
5. FSC official text requires a bounded source manifest; the derived `tw-fsc` OCR corpus remains
   HOLD and was not downloaded.

The metadata-only source manifest and automated gate are now implemented in
`research/configs/taiwan_active_sources.v1.json` and
`research/evaluation/source_manifest.py`. The 2026-08-26 live run passed TWSE (101 records) and
FinMind TAIEX (5 sessions); its raw-free report is ignored under `artifacts/`.

The next minimum executable unit is a bounded official FSC text-source manifest and metadata-only
coverage audit. Do not start M7 domain adaptation until at least one unlabelled domain corpus is
purpose-specifically accepted. Do not download a large corpus or generate active model features.
Eland is not part of this work queue.

Do not create fake labels. Keep external/full text and large model/data caches in ignored locations.
Do not automatically commit or push.

## Architecture and safety

GAS remains a private transitional LINE adapter: receive/route events, call Python, and reply/push Flex messages. Python owns ingestion, deduplication, ticker matching, NLP, features, ML, backtesting, jobs and structured storage. Do not copy old GAS code or secrets into this repository.

Preserve secret management, LINE signature validation plans, ownership checks, private holdings separation, public-demo anonymisation, source traceability and legal short-text retention. The product is a Financial Intelligence Assistant, not an automatic trading or stock-picking system.

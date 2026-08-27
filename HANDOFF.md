# Financial AI Assistant Handoff

Last revised: 2026-08-27

## Core research direction migration — authoritative handoff

This repository has deliberately reduced and redirected its core research scope. This is not a
restart and does not invalidate any prior result.

New project title:

> Financial AI Assistant: Stock Volatility Risk Prediction with Financial NLP Intelligence

Chinese working title:

> Financial AI Assistant：股票異常波動風險預警 × 金融 NLP 情報系統

The primary research question is now:

> Can historical price, volume, volatility, technical and market-context features predict
> next-session abnormal volatility / large-move risk under strict leakage-safe temporal
> evaluation?

The previous blocking question—whether automatically generated Chinese financial-text signals
improve short-horizon direction prediction—is now secondary, exploratory Track B work. It is not a
completion requirement.

Three tracks govern all new work:

1. **Track A — Core Research:** leakage-safe next-session `NORMAL` versus `HIGH_RISK` volatility /
   large-move prediction.
2. **Track B — NLP Intelligence:** pinned English FinBERT plus preserved exploratory Taiwan
   announcement/NLP research.
3. **Track C — Product:** a Financial Intelligence Assistant combining risk, market data, news,
   announcements and traceable summaries through Python APIs and a slim LINE/GAS adapter.

Track A must complete independently of validated Chinese sentiment. The risk target threshold,
preprocessing, model selection, probability threshold and calibration are train-fit only. Use
chronological train/validation/sealed-test splits and walk-forward evaluation; never random split.
Report HIGH_RISK recall and false negatives, Balanced Accuracy, F1, MCC, PR-AUC, ROC-AUC when
valid, Brier/calibration and confusion matrices. The primary validation compares predicted
HIGH_RISK and NORMAL sessions on subsequent realized absolute return, high-low range and a fixed
realized-volatility proxy. It does not require a buy/sell strategy.

The milestone sequence is now M0–M15: existing-work freeze/migration, market dataset, risk-label
protocol, feature pipeline, baselines, tree models, temporal validation, sealed test, robustness,
NLP intelligence, optional NLP ablation, risk validation, API, LINE/GAS slimming, public demo and
portfolio finalization. `docs/research_direction_migration.md` maps the legacy milestones without
deleting their evidence.

M1 Market Dataset was completed on 2026-08-27 after explicit user approval. The fixed ten-ticker
universe, chronological split contract, immutable local OHLCV/TAIEX snapshots, integrity tests and
raw-free audit summary are now present. The audit passed with 40,691 stock rows and 4,080 benchmark
sessions. Generated provider rows remain Git-ignored because redistribution rights are not assumed.
No risk label was generated, no model was trained, and no sealed-test outcome or performance was
opened. The next minimum unit is **M2 — Risk Label Protocol**. Continue to avoid GAS changes,
deployment, commit and push unless the user separately authorizes them.

M2 Risk Label Protocol was then completed on 2026-08-27. The primary target is next-session
absolute adjusted-close log return normalized by the 20-session trailing volatility known at `t`.
The candidate threshold is the training-only linear 90th percentile (`1.807988011793`), fit on
25,990 rows; training prevalence is 10%. M2 materialized 25,990 training and 4,800 validation rows.
It did not summarize validation labels, materialize sealed-test outcomes/labels, or train a model.
Mutation tests prove a changed `t+1` affects outcome/label but not the `t` state hash or numeric
train threshold. The next unit is **M3 — Feature Pipeline**.

M3 Market-Only Risk Feature Pipeline was completed on 2026-08-27. It materialized 23,890 training
and 4,800 validation rows with 23 fixed finite features and no imputation, preprocessing fit, NLP,
or model training. A strict 35-session window caused 2,100 explicit abstentions rather than gap
bridging. Stock and benchmark `t+1` mutation tests leave `t` features unchanged. Validation labels
were not summarized and sealed-test features remain unmaterialized. The next unit is
**M4 — Baselines**.

M4 Baselines was completed on 2026-08-27. It fit `StandardScaler`, balanced class weights, and
Logistic Regression on 23,890 training rows only, then evaluated historical-risk-rate,
previous-period persistence, and Logistic Regression on 4,800 validation rows. The Logistic
baseline reached HIGH_RISK recall 0.582, PR-AUC 0.172, ROC-AUC 0.645, MCC 0.122, and Brier 0.224.
Its class-balanced 0.5 threshold also generated 1,657 false positives, so it is a comparison
baseline rather than a selected final model. No validation row was used for fitting or threshold
tuning; no prediction rows were persisted; the sealed test remains unopened. The next unit is
**M5 — Tree Models**.

M5 Tree Models was completed on 2026-08-27 using the identical 23,890 training and 4,800 validation
rows. Fixed Random Forest and HistGradientBoosting candidates were trained without preprocessing,
early stopping, search, resampling, or threshold tuning. Neither tree model exceeded the M4
Logistic baseline: Random Forest PR-AUC/ROC-AUC/recall were 0.156/0.613/0.307 and HGB were
0.151/0.614/0.338, versus Logistic 0.172/0.645/0.582. The negative result is preserved; no final
model was selected. A first parallel Random Forest run produced tiny nondeterministic training
probability hashes on repeat. Diagnostic manifests were retained locally, and the frozen config
was changed to single-thread Random Forest; two immutable rebuilds then matched. The sealed test
remains unopened. The next unit is **M6 — Temporal Validation**.

M6 Temporal Validation was completed on 2026-08-27 using five expanding windows covering
2017–2024. Logistic Regression had the highest mean fold PR-AUC (0.180 versus RF 0.170 and HGB
0.167) and was selected by the predeclared rule. Leakage-safe prequential Platt calibration reduced
pooled Brier from 0.224 to 0.089. Because calibrated probabilities are prevalence-scaled, the
predeclared recall-constrained threshold procedure selected 0.10 rather than 0.50; pooled
prequential recall is 0.586, MCC 0.139 and PR-AUC 0.184 at that threshold. The final recipe was fit
through 2024 on 28,690 pre-test rows and frozen in candidate manifest SHA-256
`951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81`. Two full immutable runs
matched. Sealed-test evaluation count remains zero. The next unit is the controlled one-time
**M7 — Sealed Test**; do not execute it accidentally or use it for further selection.

The user explicitly authorized M7, and the one-time sealed test completed on 2026-08-27. Opening
intent, immutable evaluation and completion records establish evaluation sequence 1 and permanently
refuse repeats. On 3,647 eligible 2025-01-01–2026-08-26 rows, the frozen Logistic+Platt+0.10 recipe
achieved HIGH_RISK recall 0.508, precision 0.180, PR-AUC 0.189, ROC-AUC 0.686, MCC 0.155, Balanced
Accuracy 0.615 and Brier 0.0926. Predicted HIGH_RISK rows had higher normalized risk outcome
(mean 1.087 versus 0.766; median 0.876 versus 0.574), but lower raw absolute return and intraday
range. Therefore evidence supports modest normalized-risk separation, not general absolute-
volatility separation, direction prediction or investment utility. Do not rerun M7 or alter the
candidate based on test. The next unit is **M8 — Risk Error Analysis & Robustness**, using the one
existing immutable evaluation only.

M8 Risk Error Analysis & Robustness was completed on 2026-08-27 without reopening M7. The runner
verified the complete M6/M7 hash chain and retained evaluation sequence 1. A 1,000-sample
feature-session cluster bootstrap gave 95% intervals of 0.441–0.576 for recall, 0.109–0.202 for
MCC, 0.151–0.242 for PR-AUC, 0.650–0.724 for ROC-AUC and 0.0792–0.1067 for Brier. Performance is
heterogeneous: quarterly recall ranges from 0.310 to 0.656, ticker recall from 0.326 to 0.794, and
the low-stock-volatility regime exchanges high recall for very low specificity. Normalized-risk
separation remains positive, but raw outcome separation changes with conditioning. This supports
only modest normalized surprise-risk discrimination. No M7 rerun, refit, threshold change or
test-based selection occurred. The next unit is **M9 — Financial NLP Intelligence**; it must not
use M8 subgroup evidence to alter Track A.

## Preserved one-week TEJ/NLP context — secondary Track B

The user has a hard delivery deadline of **one week**. Do not wait months for prospective text
data. TEJ and historical announcement work below is preserved as Track B context and optional
acceleration; it must no longer block Track A.

The former blocking question was:

> Under the available historical sources, study period and timestamp limitations, do automatically
> generated Chinese financial-text signals add out-of-sample predictive value beyond price, volume
> and technical features alone?

It is now an optional Track B/M10 question rather than the definition of done. The zero-manual-label constraint remains absolute: no manual annotation, manual label review,
human adjudication or manually constructed sentiment truth. Eland remains a historical rejected
candidate only and must not re-enter any active experiment.

### TEJ findings verified on 2026-08-27

A newly rotated TEJ trial API key is configured only in the ignored local `.env`. Never print,
copy, commit, log or ask the user to paste it into chat. The prior exposed credential was treated as
compromised and replaced. `.env` is ignored and untracked.

The TEJ API audit established:

- Authentication succeeds.
- Trial validity: 2026-08-27 through 2026-11-27.
- Trial quotas: 500 requests/day and 50,000 rows/day.
- The key exposes 28 `TRAIL/*` trial tables.
- TEJ table search finds `TWN/AP11 — MOPS-重大訊息（含主旨／內容）`.
- Search metadata identifies `發言時間`, `重大訊息主旨 (newstxt_1)` and
  `重大訊息內容 (newstxt_2)`.
- Direct `TWN/AP11` access fails with HTTP 400, TEJ error `PDB003`: no permission for the table.

Therefore TEJ API itself works, but the current subscription cannot download AP11. Do not spend
more calls trying alternate query syntax or attempt to bypass the entitlement. The user should ask
TEJ or the university library for academic access to the exact table code `TWN/AP11`; treat access
as optional acceleration rather than a prerequisite for the one-week MVP.

Official references:

- TEJ REST API: <https://api.tej.com.tw/document_rest.html>
- TEJ EVENT system: <https://www.tejwin.com/news/event-%E4%BA%8B%E4%BB%B6%E7%A0%94%E7%A9%B6%E7%B3%BB%E7%B5%B1/>
- TEJ EVENT manual: <https://www.tej.com.tw/TEJPLUS/EventStudy-UsersManual.pdf>

### Local TEJ export already audited

The user exported the TEJ `特殊事件日期資料庫` to a local Excel workbook outside the repository.
Do not copy or commit the raw workbook until TEJ redistribution and project-use rights are
confirmed. Read-only inspection found:

- 412,150 records and 11 columns.
- 104 event categories.
- Fields include security code, event date, announcement date, shareholder-meeting date, capital
  change information and notes.
- Announcement dates are present for 377,078 records and missing for 35,072 records.
- The sheet contains date-only `YYYYMMDD` values, not `HH:MM:SS` publication timestamps.
- It contains structured event dates rather than the AP11 material-announcement title/full-text
  corpus.

This export is useful only as a licensed, private, structured historical-event supplement. It is
not a replacement for historical announcement text, must not become sentiment ground truth and
must not be publicly redistributed. If used for price alignment, apply the predeclared conservative
next-session rule for date-only records and report the limitation.

### Free official forward-ingestion route

Do not scrape or reverse-engineer MOPS historical pages. Use the documented, keyless official
OpenAPI endpoints for forward collection:

- TWSE listed-company daily material information:
  `https://openapi.twse.com.tw/v1/opendata/t187ap04_L`
- TPEx OTC daily material information: endpoint `mopsfin_t187ap04_O` documented at
  <https://www.tpex.org.tw/openapi/>.

These feeds expose announcement date, announcement time, company code/name, subject, applicable
paragraph, event date and description. They can support precise prospective collection without a
TEJ subscription. They are daily feeds, not a verified historical-backfill interface. Preserve
daily immutable snapshots, retrieval timestamps, hashes, source identifiers and licensing
metadata. Use them as a forward validation set and pipeline demonstration within the one-week
deliverable; do not imply that one week of observations provides robust market-regime evidence.

### How TEJ EVENT should be used

TEJ EVENT is a separate Windows event-study application, not the `特殊事件日期資料庫` and not an
AP11 API entitlement. It can:

- select built-in news or structured events;
- import user event dates from CSV/TXT;
- retrieve security and benchmark returns;
- estimate mean-adjusted, market-adjusted, OLS, GARCH or Scholes-Williams models;
- calculate AR/CAR and statistical tests; and
- export detailed result tables.

For the one-week deadline, test the university's TEJ EVENT entitlement immediately. In its
`事件日選擇` screen, inspect `新聞檢索` and `特定事件日檢索`. Determine whether historical Taiwan
company/industry news can be selected and whether export contains company code, event date,
publication time, title, text/summary and category. Keep the raw export private and license-gated.

- If time and text are exportable under the academic licence, audit the export and use it as the
  historical text candidate.
- If only event dates are exportable, use TEJ EVENT to produce AR/CAR reference results and validate
  the Python market-reaction engine; it cannot supply the NLP input.
- TEJ EVENT does not replace Chinese text features, baseline-versus-augmented ML comparison,
  leakage-safe temporal evaluation or the reproducible Python pipeline.

### Historical Track B fallback sequence — not the core critical path

1. **Day 1 — freeze and audit sources.** Confirm the TEJ EVENT export capability. Freeze a
   historical text candidate already legally available; otherwise retain the existing historical
   news source as explicitly limited exploratory evidence. Do not hold the schedule open for AP11.
2. **Day 2 — normalise and align.** Deduplicate text, resolve issuers, preserve source lineage and
   map timestamps to trading sessions. Unknown intraday publication times use conservative
   next-session alignment.
3. **Day 3 — automated Chinese signals.** Run the versioned weak-supervision/encoder signal path
   with abstention and ambiguity preserved. Do not fabricate neutral values for unsupported text.
4. **Day 4 — paired models.** Train an identical price/volume/technical baseline and an augmented
   model adding only pre-event text signals. Keep features, splits and tuning budget otherwise
   identical.
5. **Day 5 — leakage-safe evaluation.** Use temporal or walk-forward splits, embargo reaction
   windows, trading costs and benchmark-adjusted targets. TEJ EVENT AR/CAR may be a private
   cross-check if available.
6. **Day 6 — robustness and reporting.** Report Balanced Accuracy, macro-F1 where applicable, MCC,
   ROC-AUC/PR-AUC where valid, calibration, return, Sharpe and maximum drawdown. Include source,
   timestamp, licensing and sample-size limitations.
7. **Day 7 — package the MVP.** Run tests/lint/secret scan, freeze configurations and evidence,
   update README/architecture/experiment docs and prepare an anonymised public demonstration. No
   raw TEJ data, personal data, secret, model overclaim, automatic commit or push.

### Historical NLP-pilot boundary — superseded by Track A definition of done

If the optional NLP experiment is run, it is complete when the repository can reproducibly compare the same out-of-sample periods
for:

1. price/volume/technical features only; and
2. the same features plus timestamp-safe automated Chinese text signals.

This optional conclusion must distinguish `no demonstrated incremental value`, `inconclusive` and
`positive exploratory evidence`. It must not claim human-validated Chinese sentiment truth,
causality, production trading readiness or generalisation across unseen market regimes. A paid TEJ
AP11 subscription is not part of either Track A or M10 completion.

## Preserved legacy NLP boundary

M0–M7 bounded pilot are complete and their evidence is retained under a hard zero-human-label constraint: no
manual annotation, label review or human adjudication. The taxonomy, automated-signal protocol,
market-reaction protocol, logical schema, dataset-governance register, source/archive audit CLIs,
calibration exporter, agreement CLI and tests are implemented locally. A 60-item
Gemini-versus-Codex diagnostic is retained under ignored local directories as model-stability
evidence only. The filtered official FSC corpus produced a 6,021-record family-isolated snapshot.
Pinned MacBERT-base and BERT-base-Chinese passed feasibility and an approved 200-step bounded pilot
without reading sealed test. Both weights are preserved only under ignored storage. The
predeclared identical-vocabulary/final-MLM-loss rule recommends BERT-base-Chinese as the frozen
representation candidate, not as sentiment truth. The M8 `market-reaction-v1` engine and bounded
snapshot are also complete: 108 deduplicated TWSE events produced 324 horizon rows from 599 stock
prices and eight benchmark sessions. Every event is in the sealed test period, so train and
validation are empty; test return/class distributions remain unread and withheld. The current
legacy Track B status is implementation complete, historical backfill required—not training-ready.
This no longer blocks new Track A. Check Git status because changes are uncommitted.

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

## Preserved legacy NLP research contracts

Keep these signal groups distinct:

1. English financial sentiment from validated pinned FinBERT.
2. Taiwan financial event type and entity-specific impact.
3. Historical market reaction derived from future/abnormal returns as offline targets.
4. Price, volume and technical features.
5. Optional downstream short-horizon direction or new M10 risk-prediction ablation.

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
5. FSC official text passed a bounded, approved automated archive audit for a filtered
   non-commercial unlabelled adaptation feasibility corpus; the derived `tw-fsc` OCR corpus remains
   HOLD and was not downloaded.

The metadata-only source manifest and automated gate are now implemented in
`research/configs/taiwan_active_sources.v1.json` and
`research/evaluation/source_manifest.py`. The 2026-08-26 live run passed TWSE (101 records) and
FinMind TAIEX (5 sessions); its raw-free report is ignored under `artifacts/`.

The bounded FSC official-source manifest and HEAD-only coverage gate passed. The user then approved
the 7,224,679-byte download into ignored `.tools/datasets/fsc-official/`. Sizes and SHA-256 values
are pinned in `research/configs/fsc_official_archive_snapshot.v1.json`; the raw-free automated audit
passed all five archives and 6,047 XML records. There were no exact or cross-agency content
duplicates; 14 within-agency duplicate-content extra rows, ten unparseable publication dates and
one empty content record require deterministic filtering. The purpose-specific decision is ACCEPT
only for filtered, deduplicated, non-commercial unlabelled domain-adaptation feasibility. It is not
sentiment truth, redistribution approval or a completed training run. See
`research/evaluation/fsc_official_archive_audit.md`.

M6 source/corpus audit, the approved M7 bounded pilot and the M8 calculation/lineage engine are
complete. Under the legacy plan, the next unit would have been an audit and backfill of a historical
official event source with reliable publication timestamps; this is now optional Track B work, not
the new project critical path. The first metadata audit found that official
`t187ap04_L` is documented as a daily feed only; the MOPS historical browser query has no verified
bulk API contract and may return a security block. Preserve it as HOLD rather than reverse
engineering or bypassing controls. Forward daily collection remains accepted; historical backfill
requires an official/licensed export that passes a new manifest audit. A bounded FinMind historical
news audit then returned 34 rows across three dates but failed schema consistency, produced only
timezone-naive timestamps and contained duplicate links; it remains discovery metadata only and
HOLD for reaction events. Do not use the all-test M8
snapshot for threshold selection or downstream training. Keep the selected representation frozen,
do not read the FSC or market-reaction sealed tests, and do not release weights or claim sentiment
quality. Eland is not part of this work queue.

The independent M9 minimal aggregation core is now implemented under
`research/weak_supervision/`. It requires at least two versioned sources, preserves official and
inferred categories separately, records model/prompt/input/vote hashes, and maps conflict to
`AMBIGUOUS` or abstention without human adjudication. Only synthetic tests have run; real-source
adapters, external/local-model execution and adoption experiments remain pending. Do not imply M9
signal quality from the passing engineering tests.

Do not create fake labels. Keep external/full text and large model/data caches in ignored locations.
Do not automatically commit or push.

## Architecture and safety

GAS remains a private transitional LINE adapter: receive/route events, call Python, and reply/push Flex messages. Python owns ingestion, deduplication, ticker matching, NLP, features, ML, backtesting, jobs and structured storage. Do not copy old GAS code or secrets into this repository.

Preserve secret management, LINE signature validation plans, ownership checks, private holdings separation, public-demo anonymisation, source traceability and legal short-text retention. The product is a Financial Intelligence Assistant, not an automatic trading or stock-picking system.

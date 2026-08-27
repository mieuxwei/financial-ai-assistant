# Research Direction Migration Note

Migration date: 2026-08-27  
Migration version: `core-direction-migration-v2`

## Purpose

This note records a deliberate scope reduction, not a restart. The previous core study asked
whether automated Chinese financial-text signals improved short-horizon stock-direction
prediction beyond market features. The new core study predicts next-session abnormal-volatility /
large-move risk using leakage-safe market features. The former NLP question remains optional
exploratory research.

No existing result, source decision, failure, code path, audit or sealed-test boundary is deleted or
invalidated by this migration.

## Research-question mapping

### Previous core question

> Do automatically generated Chinese financial-text signals improve stock direction prediction
> beyond price, volume and technical features?

### New core question

> Can historical price, volume, volatility, technical and market-context features predict
> next-session abnormal volatility / large-move risk under strict leakage-safe temporal
> evaluation?

### New status of the previous question

The previous question becomes Track B exploratory research and new M15 optional incremental-value
ablation. Chinese sentiment quality or NLP incremental value is not part of the main definition of
done.

## Track mapping

| New track | Scope | Independence rule |
| --- | --- | --- |
| Track A — Core Research | Next-session `NORMAL` / `HIGH_RISK` abnormal-volatility or large-move prediction | Must complete without validated Chinese sentiment |
| Track B — NLP Intelligence | English FinBERT, Taiwan announcement intelligence and all preserved Taiwan NLP experiments | May add value but cannot block Track A |
| Track C — Product | FastAPI + LINE/GAS Financial Intelligence Assistant | Presents risk/research signals, never buy/sell advice |

## Legacy-to-new milestone mapping

Legacy milestone numbers below refer to the plan that existed before 2026-08-27. New milestone
numbers refer to `PROJECT_PLAN.md` version `post-m8-risk-extension-v3`.

| Legacy milestone / work | Preserved status | New destination |
| --- | --- | --- |
| Legacy M0 security and repository initialization | Complete foundation; unchanged | New M0 evidence freeze; Track C security baseline |
| Legacy M1 FastAPI/database foundation | Complete foundation; unchanged | New M17 API and Track C foundation |
| Legacy M2 multi-user portfolio service | Complete foundation; unchanged | New M17/M18 product integration |
| Legacy M3 historical market-data pipeline | Reusable core engineering | New M1 Market Dataset |
| Legacy M4 news/announcement pipeline | Preserved product/NLP ingestion | New M14 NLP Intelligence and M17 API |
| Legacy M5 English FinBERT | Preserved pipeline sanity evidence | New M14 NLP Intelligence |
| Legacy M5.5 Chinese-model diagnostic | Preserved failed-gate evidence; not formal benchmark | New M14 Exploratory Taiwan Financial NLP |
| Legacy M6 source/corpus audit and zero-manual-label governance | Preserved in full | New M0 evidence freeze and M14 NLP Intelligence |
| Legacy M6 direction feature/label dataset (`features-v1`, `label_up`) | Preserved legacy foundation; direction label no longer core | Market features/cutoff/hash/tests reused in new M1/M3; label replaced by new M2 |
| Legacy M7 FSC domain adaptation feasibility and 200-step pilot | Preserved; no further training authorized by migration | New M14 exploratory representation evidence |
| Legacy M8 automatic market-reaction engine | Preserved target/lineage engine; bounded snapshot remains all-test and sealed | New M14 exploratory evidence; possible M15 feature research only if eligible |
| Legacy M9 weak-supervision aggregation core | Preserved synthetic-tested core | New M14 exploratory announcement intelligence |
| Legacy M10 integrated direction feature pipeline plan | Market feature pieces reused; Taiwan signal expansion optional | New M3 Feature Pipeline and optional M15 NLP ablation |
| Legacy M11 direction-prediction experiment matrix | No longer mandatory | Replaced by new M4–M7 risk-model sequence; text comparison moves to optional M15 |
| Legacy M12 trading-oriented backtest/conclusions | Reframed away from mandatory strategy | New M16 HIGH_RISK-vs-NORMAL realized-risk validation; exposure reduction optional |
| Legacy M13 Prediction & Research API | Preserved product intent | New M17 Prediction / Intelligence API |
| Legacy M14 LINE integration and GAS slimming | Preserved unchanged | New M18 LINE Integration & GAS Slimming |
| Legacy M15 public demo and controlled beta | Preserved, risk-focused UX | New M19 Public Demo |
| Legacy M16 error analysis and robustness | Reframed around risk errors/calibration | New M8 Risk Error Analysis & Robustness |
| Legacy M17 final report/deployment | Preserved finalization intent | New M20 Portfolio Finalization |

## Preserved NLP and source-governance evidence

The following remains valid historical/exploratory evidence:

- pinned English `ProsusAI/finbert` pipeline and 12-example sanity result;
- Chinese lexicon, yiyang, bards.ai, multilingual and translation diagnostic results;
- frozen 30-item TWSE-derived diagnostic and its rejection boundary;
- zero-manual-label Taiwan financial-learning protocol;
- AI-to-AI calibration stability evidence without human adjudication;
- official FSC archive audit and 6,021-record family-isolated corpus;
- MacBERT/BERT-base-Chinese feasibility and bounded 200-step pilot;
- frozen BERT-base-Chinese representation candidate decision;
- weak-supervision schema, deterministic rules and aggregation core;
- automatic market-reaction protocol, code and sealed bounded snapshot;
- TWSE, FinMind, TEJ and other source-governance decisions;
- Eland historical HOLD/exclusion evidence.

These do not establish validated Taiwan sentiment truth. Eland remains excluded from training,
adaptation, weak supervision, evaluation, features, corpus merging and active re-audit.

## Data and sealed-test preservation

- Do not read, relabel or summarize the sealed FSC test.
- Do not inspect the withheld reaction-return/class distribution from the legacy all-test snapshot.
- Do not reuse future reaction values as contemporaneous risk features.
- Do not fit the new risk threshold, preprocessing or model on validation/test.
- Raw restricted corpora, TEJ exports, model weights and generated datasets remain in ignored local
  storage and are not public artifacts.
- A new risk dataset receives a new schema/config/snapshot version; it must not overwrite
  `features-v1` or legacy research evidence.

## Product-language migration

Replace direction/trading-oriented product wording with:

- next-session volatility risk;
- `NORMAL` / `HIGH_RISK`;
- risk probability;
- top contributing factors;
- research signal / risk signal;
- financial announcement/news intelligence.

Do not use automatic trading, stock-picking oracle, buy/sell recommendation or guaranteed-return
claims.

## New completion rule

The project completes when a reproducible market dataset, train-only risk target, leakage-safe
market features, interpretable and nonlinear models, chronological validation, frozen sealed test,
HIGH_RISK error/calibration reporting, and realized-risk separation analysis are complete, while
NLP remains available as an intelligence layer and all privacy/licensing boundaries hold.

Chinese sentiment performance and NLP incremental value are explicitly not mandatory.

## Immediate next unit

M1 was executed after explicit user approval on 2026-08-27:

1. freeze a bounded ticker universe and historical period;
2. predeclare warm-up, train, validation and sealed-test date coverage;
3. build immutable OHLCV and FinMind TAIEX snapshots;
4. audit duplicate sessions, OHLC invariants, missing sessions, volumes, adjusted-price revisions
   and benchmark alignment;
5. add tests and a raw-free quality report.

The immutable M1 audit passed. M2 then produced a training-only 90th-percentile candidate threshold
and train/validation risk labels with temporal mutation tests. M3 produced 23 fixed market-only
features with strict `t` cutoffs. M4 then fit training-only scaling and historical-risk,
persistence, and Logistic Regression baselines and evaluated them on validation without tuning. M5
compared fixed Random Forest and HistGradientBoosting candidates; neither exceeded Logistic on
recall or ranking metrics. M6 then completed five expanding-window folds, selected Logistic plus
Platt calibration and threshold 0.10 under predeclared rules, and froze the pre-test candidate
manifest. M7 then opened the sealed test once under explicit approval and preserved the final mixed
result: modest normalized-risk discrimination but no raw absolute-volatility separation. The test
is permanently closed to further evaluation or selection. M8 then completed read-only robustness,
error, drift and bootstrap-uncertainty analysis of that immutable evaluation. M9 then confirmed a
descriptive raw-outcome aggregate/within-regime composition reversal without refit or threshold
change. M10 then selected three development-only global operating candidates using reconstructed
M6 OOF evidence and no post-M6 outcomes. The next unit is M11 one-model regime-aware thresholding;
none of these policies is holdout-validated or product-ready.

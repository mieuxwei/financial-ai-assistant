# Experiment Protocol

## Active final-study contract

The active study forecasts a continuous next-session stock-normalized volatility-surprise outcome.
Its target, folds, allowed models, model-selection rule, metrics, ranking analysis and claim boundary
are frozen in `research/configs/final_volatility_surprise_study.v1.json` and documented in
`docs/final_volatility_surprise_study_protocol.md`. The study is retrospective, leakage-aware and
hypothesis-informed; it does not claim a new untouched sealed test or prospective validation.

The primary outcome is the next-session absolute adjusted-close log return divided by the
population standard deviation of the 20 adjusted-close log-return transitions ending at feature
session `t`. The denominator uses only information available at `t`; rows with a denominator less
than or equal to `1e-8` are excluded and counted. Evaluation uses expanding-window outer folds and
three annual inner temporal validation blocks contained entirely within each outer training
history. The allowed core models are normalized persistence, Ridge Regression and
HistGradientBoostingRegressor.

Primary reporting includes MAE, RMSE, R-squared, Spearman rank correlation, frozen ratio-based
top-decile/top-quintile lift and predicted-score decile tables. NLP incremental value is optional.

F4 implementation status: normalized-move persistence, Ridge and HistGradientBoostingRegressor
candidate interfaces are complete. Ridge scaling is training-only; HGB internal early stopping is
disabled. Hyperparameters are restricted to the frozen F1 grids. F4 used synthetic tests only. See
`research/evaluation/f4_regression_candidates_result.md`.

F5 implementation status: seven nested rolling-origin outer folds are complete. Inner selection
used only each outer training history and produced 61,911 immutable OOF predictions for 20,637
unique evaluation rows. Ridge and HGB mean Spearman values are within the frozen practical-tie
margin; F5 selected no final model. See
`research/evaluation/f5_nested_temporal_evaluation_result.md`.

F6 implementation status: ranking, within-outer-fold deciles, top-decile/quintile lift,
ticker/time/training-defined-regime robustness and 1,000-replicate feature-session cluster
bootstrap are complete on immutable F5 OOF predictions. Ridge/HGB remain inside the practical-tie
boundary and no final model was selected. See
`research/evaluation/f6_ranking_robustness_result.md`.

F7 implementation status: the frozen practical-tie rule selected Ridge by lower mean outer MAE;
2023–2025 expanding temporal validation selected alpha 100. A full-history 32,357-row research fit
was exported as verified safe JSON with empirical OOF percentile and 50/80/95 communication bands.
No deployment or prospective accuracy claim was made. See
`research/evaluation/f7_final_research_model_result.md`.

## Exploratory binary-risk contract (historical M1–M11; frozen)

The mandatory experiment predicts next-session `NORMAL` versus `HIGH_RISK` abnormal-volatility /
large-move risk from price, volume, volatility, a compact technical set and market context. The
continuous outcome and risk threshold are fit under a versioned train-only protocol. Model,
preprocessing, calibration and decision-threshold selection use chronological validation only;
the final test remains sealed until the candidate manifest is frozen. Required reporting includes
HIGH_RISK recall and false negatives, Balanced Accuracy, F1, MCC, PR-AUC, ROC-AUC when valid,
Brier/calibration and confusion matrices.

M2 implementation status: the primary normalized outcome, train-only 90th-percentile candidate
threshold, train/validation-only labels and leakage tests are complete. Sealed-test outcomes and
labels remain unmaterialized. See `docs/risk_label_protocol.md`.

M3 implementation status: 23 finite market-only features are complete for train/validation with a
fixed 35-session `t`-only window. No preprocessing is fit and sealed-test features remain
unmaterialized. See `docs/risk_feature_protocol.md`.

M4 implementation status: training-only scaling and three fixed baselines are complete. Validation
metrics and uniform calibration bins are reported without model or threshold selection. The
class-balanced Logistic Regression is explicitly a baseline; its probabilities are not claimed to
be calibrated. Sealed test remains unopened. See `docs/risk_baseline_protocol.md`.

M5 implementation status: fixed Random Forest and HistGradientBoosting candidates are evaluated on
the identical validation rows. Neither exceeded the Logistic baseline's recall or ranking metrics;
the negative comparison remains part of the record and no model was selected. Feature importance
is validation permutation importance scored by PR-AUC and is not used for fitting. Repeated
single-thread reconstruction passes; sealed test remains unopened. See
`docs/risk_tree_model_protocol.md`.

M6 implementation status: five expanding windows cover 2017–2024 with target-overlap purging.
Logistic Regression wins the frozen mean-fold PR-AUC rule. Prequential Platt calibration is fit only
from earlier fold predictions, and threshold 0.10 is selected by maximum MCC subject to at least
0.50 HIGH_RISK recall. The final pre-test recipe is frozen after fitting through 2024; sealed-test
evaluation count remains zero. See `docs/risk_temporal_validation_protocol.md`.

M7 implementation status: the user-authorized sealed test was opened exactly once. The frozen
Logistic+Platt+0.10 recipe was reconstructed byte-for-byte and evaluated on 3,647 eligible
2025–2026 rows. Test recall is 0.508, PR-AUC 0.189, ROC-AUC 0.686, MCC 0.155 and Brier 0.0926.
Normalized-risk separation is positive, while raw absolute-move/range separation is negative; both
facts are retained. Evaluation sequence is permanently 1 and M7 cannot be rerun. See
`docs/risk_sealed_test_protocol.md`.

M8 implementation status: the existing M7 evaluation was analyzed without rerun or selection.
Ticker, quarter, pre-test-fit stock/market volatility regimes, fixed probability buckets and error
types expose material heterogeneity. Feature-session cluster bootstrap intervals quantify overall
uncertainty. Positive normalized-risk separation coexists with conditioning-dependent raw outcome
separation, so no general absolute-volatility claim is made. See
`docs/risk_robustness_protocol.md`.

M9 implementation status: analysis-only composition, common-regime standardization, ticker/quarter
stratification and OLS/HC3 diagnostics are complete. All raw outcomes reverse direction between the
aggregate and every stock-volatility regime; normalized/additive surprise evidence remains
positive, while ticker raw directions are mixed. This is documented as a descriptive Simpson-type
composition effect, not causal proof. M7/M8/M9 evidence cannot enter M10/M11 selection. See
`docs/post_m8_risk_research_extension_protocol.md`.

M10 implementation status: 13,550 M6 prequential development rows were deterministically
reconstructed with matching fold/model/calibration evidence. The predeclared grid selected 0.09,
0.11 and 0.13 for Screening, Balanced and Precision objectives. Results are development-only and
historical 0.10 remains frozen. No post-M6 labels/outcomes entered selection. See
`research/evaluation/m10_operating_point_result.md`.

M11 implementation status: fold-specific volatility tertiles were fitted only from earlier
training history, then 125,000 LOW/MIDDLE/HIGH threshold triplets were compared on the same 13,550
development OOF rows. The selected 0.12/0.10/0.08 policy sharply reduces cross-regime recall and
specificity ranges, with lower overall MCC than global 0.10 and M10 Balanced. It is development-only;
no separate model or post-M6 outcome entered selection. See
`research/evaluation/m11_regime_threshold_result.md`.

The historical NLP contracts below remain valid Track B evidence. Comparing otherwise matched
market-only and market+NLP models is optional F9 work and is not part of the main definition of
done. See `PROJECT_PLAN.md` and `docs/final_study_migration.md`.

## M5 sentiment reproducibility contract

- Model: `ProsusAI/finbert` at revision `4556d13015211d73dccd3fdd39d39232506f3e43`.
- Runtime inference uses evaluation mode, inference mode, a fixed PyTorch seed and deterministic algorithms.
- Each stored output includes a model version and SHA-256 of the exact normalized input text plus model version.
- Probabilities are stored to eight decimal places; the continuous score is `positive_prob - negative_prob`.
- English is supported. Chinese input is excluded rather than translated or assigned neutral.
- Calendar-day sentiment uses Asia/Taipei dates. Trading-session cutoffs are deferred to M6.
- The pre-existing 12-item manual sample is a pipeline sanity check only, not a performance benchmark.

## M5.5 historical Chinese adoption gate

Chinese model selection uses both a balanced synthetic regression set and a separate TWSE announcement-derived context set. A candidate must reach macro-F1 ≥ 0.70 and recall ≥ 0.60 for positive, neutral and negative on the TWSE set. Timing is diagnostic only and excluded from reproducibility hashes.

No tested historical M5.5 candidate passed. Chinese results remain missing-by-design rather than
neutral. The current TWSE sample remains historical model-rejection evidence only and must not be
used as formal ground truth or to tune lexicons, thresholds or model weights.

The explicit rejection evidence is retained: lexicon macro-F1 0.320, yiyang 0.357, bards.ai 0.442, translation plus English FinBERT 0.592, and Kenpache multilingual-v2 0.640. The gate remains macro-F1 ≥ 0.70 and recall ≥ 0.60 for every required class.

## M6 Taiwan data/corpus and automated-signal contract

- The target concepts are a versioned event type and entity-specific financial impact: positive, neutral, negative or ambiguous.
- Linguistic tone, financial impact and observed future price reaction must not be treated as interchangeable labels.
- The project performs no human annotation or human label review. AI outputs are versioned silver signals, never expert truth.
- Model agreement, confidence and abstention are features and diagnostics; disagreements are not manually adjudicated.
- Near-duplicate disclosures and their rewrites belong to the same split. Train is earlier, validation is used for selection, and final test remains sealed.
- The 30-item TWSE-derived set stays a frozen diagnostic artifact and is not sufficient for training or a publishable benchmark.
- Candidate public data must pass provenance, licence, label, duplicate and split-leakage audits before use.

## M7 domain-adaptation feasibility contract

- Only the filtered official FSC train split may update encoder weights; validation is evaluation-only and test remains sealed.
- Corpus, split files, tokenizer and model revisions, seed, masking parameters, compute time and peak memory are pinned.
- The first feasibility run is deliberately tiny and tests operational reproducibility only; MLM loss movement is not a sentiment or downstream-quality claim.
- Adapted weights were saved only after the bounded pilot configuration and ignored-storage policy were approved; they remain local and uncommitted.
- Candidate comparison must use predeclared budgets and cannot select a winner from the two-step smoke result.
- The approved 200-step pilot used the predeclared identical-vocabulary/final-validation-MLM-loss rule; BERT-base-Chinese is the frozen representation candidate, while MacBERT remains preserved comparison evidence.
- This selection is domain-representation-only and must be re-tested through later downstream chronological ablation before any usefulness claim.

## M9 Taiwan weak-signal adoption contract

- Frozen embeddings and structured AI event/impact proxies are candidates; none is a preselected winner.
- No model is fine-tuned on AI labels and then evaluated against the same label-generation process as proof of semantic accuracy.
- Adoption depends on incremental chronological out-of-sample prediction value, coverage, abstention and regime stability.
- Failed candidates and negative findings remain in the report. Unsupported or invalid text never receives fabricated probabilities or a neutral placeholder.

## M8 historical market-reaction contract

- Candidate targets include next-session, 1-day and 3-day returns, preferably adjusted by a benchmark or market return.
- The publication timestamp and market cutoff determine the reaction window; same-session article collections are treated as one information set when causal attribution is not identifiable.
- Future return is allowed only as an offline target/label. It is forbidden as an input available at the event time.
- Any reaction-derived input at prediction time must use only events whose reaction windows finished before that prediction cutoff.
- Target thresholds, beta estimates and normalisation are fit on train only and then frozen.
- The v1 engine is implemented, but the first bounded snapshot contains only sealed-test events.
  Train/validation backfill is mandatory before target selection or downstream training; test
  reaction distributions stay withheld.

## M11 downstream comparison contract

The comparison matrix includes Baseline 0 majority/previous-direction, Baseline 1 market-only,
Model 2 news count/metadata, Model 3 English FinBERT, Model 4 Taiwan frozen representation,
Model 5 official/inferred event metadata plus weak supervision, Model 6 eligible past-completed
reaction features, and Model 7 combined signals. Signal-group ablations remove each group
independently. Model selection uses chronological validation, the final test stays sealed, and
walk-forward analysis checks regime stability.

## M6 feature and label contract

- One row represents information available at the Asia/Taipei 13:30 close of trading session `t`.
- The target is the next observed session, not `t + 1` calendar day. `label_up = 1` only when adjusted-close return is strictly positive; zero return belongs to class 0.
- Every return, moving average, volume statistic, volatility, RSI and MACD value ends at `t`. A leakage test mutates `t+1` and requires `t` features to remain byte-equivalent while its label changes.
- News at or before the cutoff enters session `t`; news after the cutoff or on a non-trading day enters the next observed session.
- Sentiment rolling windows use 1, 3 and 5 observed trading sessions. No-article probability and score fields are null, not zero or neutral; article counts are zero.
- The modeling dataset records exact configuration, pipeline version, market snapshot hash, sentiment snapshot hash and dataset hash. Rebuilding identical database inputs must reproduce the hash.
- M11 preprocessing, imputation, scaling, feature selection and threshold selection must fit on the training period only. The feature builder intentionally performs none of those steps.

M3 market snapshots are ordered by ticker and trading date and include a deterministic SHA-256. Research configurations must record the snapshot checksum, provider, requested range, and canonical universe. `ingested_at` is intentionally excluded from the checksum because it is operational metadata rather than market information.

Yahoo raw OHLC values are normalized to six decimal places and its derived adjusted close to three decimal places. Existing adjusted-close changes of `0.005` or less retain the stored value; larger changes create a new dataset revision. This rule is part of snapshot schema `market-prices-v1`.

Potential weekday gaps must not automatically be forward-filled. They require exchange-calendar verification before feature or label generation.

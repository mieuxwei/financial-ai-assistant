# F7 Final Research Model Freeze Result

Date: 2026-08-28

Status: **COMPLETE — Ridge research model selected, fitted and frozen; not deployed**

## 1. Scope and claim boundary

F7 applied the model-selection order frozen before F5/F6, selected one final research model,
selected its hyperparameter using training-history-only temporal validation, fitted all eligible
historical rows and persisted a safe JSON inference artifact.

F7 did not reopen F5/F6 tuning, use ticker/regime subgroups for selection, rerun M7, claim
prospective accuracy, modify GAS, deploy, commit or push. The artifact predicts next-session
stock-normalized volatility surprise, not price direction, return or investment value.

## 2. Frozen lineage

| Object | Canonical SHA-256 |
| --- | --- |
| F1 protocol config | `4ce3b49dc1c353788645e1f0eb7a549a9082e412bb45e7b75468791781d5de66` |
| F4 model config | `88ff58b4510cec94c0f0b5a1c895cad3bafc126bf61048d01facdfb1dbfae726` |
| F2 final dataset | `2db2b0e52ddca85b1578ef0e1438b12e2df5c3617b573d014e5bfe736aaae88c` |
| F5 OOF predictions | `b693476dba45c2aefcbf556d1ba79a21602c34da2321808d3ec0512d7c65b4a7` |
| F6 aggregate analysis | `8fd2fdc84f65fb47b6bc87df4b662c4bbd5a9ec8c82d41de4cdd3825b6364e70` |
| F7 freeze config | `d87b335e3a03382ca7f0e45bb80fdb862e9017b93756a40171d61936410dc167` |
| Final research artifact | `279472ab0794d093cbff0ab5a171b43be16abc3a7abed56d938938235505d4de` |

## 3. Final model selection

F1 froze this order:

1. highest mean outer-fold Spearman;
2. differences `<= 0.01` are a practical tie;
3. within a tie, lower mean outer MAE;
4. then higher worst-fold Spearman;
5. then lower implementation complexity.

| Candidate | Mean outer Spearman | Mean outer MAE | Worst-fold Spearman | Mean top-10% lift |
| --- | ---: | ---: | ---: | ---: |
| Persistence | 0.0608 | 0.7274 | 0.0080 | 1.1766 |
| Ridge | **0.1940** | **0.5473** | 0.1091 | 1.3542 |
| HGB | 0.1863 | 0.5480 | **0.1349** | **1.3611** |

Ridge and HGB differ by `0.0078` mean Spearman and therefore form the practical-tie set. Ridge is
selected because its mean outer MAE is lower, the first applicable frozen tie-break. HGB's better
worst-period Spearman and slightly higher top-decile lift remain visible but occur later in the
predeclared decision order. No single year, ticker, regime or bootstrap subgroup selected the
model.

Final selected family: **Ridge Regression**.

## 4. Final hyperparameter selection

The full-history artifact did not choose alpha from F6 subgroups. It reran the same expanding
temporal selection pattern over the latest three complete years—2023, 2024 and 2025—using only
earlier history for each validation year.

| Alpha | Mean inner Spearman | Mean inner MAE | Worst inner Spearman |
| ---: | ---: | ---: | ---: |
| 0.1 | 0.202774 | **0.538051** | **0.112760** |
| 1 | 0.202785 | 0.538052 | 0.112667 |
| 10 | 0.202841 | 0.538055 | 0.112129 |
| 100 | **0.203085** | 0.538078 | 0.109127 |

Primary mean inner Spearman selects **alpha 100**. The advantage is small; it is reported as a
deterministic protocol outcome, not evidence that strong regularization is universally superior.

## 5. Full historical research fit

- Eligible training rows: 32,357.
- Feature dates: 2011-01-03–2026-08-25.
- Latest training target session: 2026-08-26.
- Previously evaluated outer-period source rows are included as ordinary historical training rows,
  as allowed after retrospective evaluation; OOF predictions and evaluation metrics are not model
  inputs.
- Features: frozen 23-field `risk-features-v1` order.
- Target transform: `log1p`.
- Inverse: `max(0, expm1(prediction))`.
- StandardScaler: fitted on these final training rows only.
- Training-row SHA-256:
  `d1a3e99c73dcc51251f7ae10f1e2a63731bcb9e49c2279259a2b368c42472822`.
- Learned-state SHA-256:
  `981b71e619f59d48d76c42b4cce2fb2ef77ad1d0b9147559ab0776342168b015`.
- Fit-manifest SHA-256:
  `7f24e42c278b94754729df8de7c0b69e46246637511d69e2da1f606e5f9e7988`.

Repeated fitting produced the same learned-state hash. Safe-JSON inference matched the fitted
sklearn Ridge predictions with maximum absolute difference `5.01e-13`.

No training-set metric is presented as generalization evidence. Historical OOS evidence remains
the F5/F6 result.

## 6. Artifact and inference contract

Artifact version: `final-ridge-research-model-v1`.

Format: **safe JSON, no pickle**. It stores:

- ordered feature contract;
- scaler mean/scale;
- Ridge coefficients/intercept;
- alpha and target transform;
- exact dataset/config/fit lineage;
- sorted Ridge historical OOF prediction reference;
- percentile and communication-band policy.

Required inference output:

```json
{
  "ticker": "2330",
  "as_of_date": "YYYY-MM-DD",
  "information_cutoff": "YYYY-MM-DDT13:30:00+08:00",
  "predicted_volatility_surprise": "X.XXXXXXXXXXXX",
  "historical_percentile": 0.0,
  "risk_band": "LOW | MODERATE | HIGH | VERY_HIGH",
  "model_version": "final-ridge-research-model-v1",
  "feature_pipeline_version": "risk-features-v1"
}
```

The inference loader verifies artifact SHA, exact feature names/order, finite scaler/model state,
timezone-aware cutoff, nonnegative score and historical-reference ordering before returning a
result.

## 7. Historical percentile and communication bands

Reference: 20,637 pooled Ridge historical outer OOF predictions. Percentile uses the right-inclusive
empirical CDF. Quantile cutoffs use NumPy's linear method frozen in F7.

| Band | Score boundary |
| --- | --- |
| LOW | `< 0.688396320725` |
| MODERATE | `>= 0.688396320725` and `< 0.767969705037` |
| HIGH | `>= 0.767969705037` and `< 0.859820943336` |
| VERY HIGH | `>= 0.859820943336` |

These are presentation/ranking bands, not classifier labels. A VERY HIGH result does not predict
up/down direction or guarantee an unusually volatile next session.

## 8. Limitations

- The problem formulation was informed by earlier historical analysis.
- F5/F6 are retrospective historical OOS evidence, not prospective validation.
- Average point-forecast R² remained near zero; the defensible value is ranking, not exact magnitude.
- The universe contains ten instruments and inherits F3 temporal coverage concentration.
- Ridge/HGB bootstrap intervals overlapped; Ridge was selected by the frozen practical-tie rule,
  not a claim of universal superiority.
- The artifact has not been exposed through FastAPI, LINE or a dashboard.
- Naturally future data remains required for genuine prospective external validation.

## 9. Stop boundary

F7 is complete. The model and artifact are frozen, but `deployed=false`. The next minimum executable
unit, only after user review/approval, is **F8 — Financial NLP Intelligence**. F8 must preserve the
existing English FinBERT evidence, Taiwan abstention boundaries and all historical NLP diagnostics;
it must not make Track A completion depend on validated Chinese polarity.

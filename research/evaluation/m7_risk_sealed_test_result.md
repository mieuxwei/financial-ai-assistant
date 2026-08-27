# M7 Sealed Test — Final Raw-Free Result

Evaluation date: 2026-08-27  
Protocol: `risk-sealed-test-v1`  
Evaluation sequence: **1 — complete; repeats prohibited**

## Frozen setup

- Test period: 2025-01-01–2026-08-26.
- Candidate: Logistic Regression + StandardScaler.
- Calibration: frozen Platt.
- Decision threshold: frozen 0.10.
- Eligible rows: 3,647 across 10 tickers.
- Actual HIGH_RISK rows: 390 (10.69%).
- Model/calibration/threshold selection using test: **false**.
- Final model state reconstructed from M6: **true**.

## Final test metrics

| Metric | Result |
|---|---:|
| Balanced Accuracy | 0.615 |
| HIGH_RISK precision | 0.180 |
| HIGH_RISK recall | 0.508 |
| HIGH_RISK F1 | 0.265 |
| Macro-F1 | 0.538 |
| MCC | 0.155 |
| PR-AUC | 0.189 |
| ROC-AUC | 0.686 |
| Brier score | 0.0926 |
| Supplemental accuracy | 0.699 |

Confusion matrix: TN 2,352; FP 905; FN 192; TP 198. False-negative rate is 0.492 and specificity
is 0.722. Test recall is lower than the pooled prequential M6 estimate (0.586) but remains just above
the predeclared 0.50 constraint. PR-AUC, ROC-AUC, MCC and Brier remain broadly consistent with modest
discrimination and usable aggregate calibration, not strong classification.

## Realized-risk separation

| Predicted group | Rows | Mean normalized outcome | Median normalized outcome | Mean abs log return | Mean high-low range |
|---|---:|---:|---:|---:|---:|
| NORMAL | 2,544 | 0.766 | 0.574 | 0.0190 | 0.0279 |
| HIGH_RISK | 1,103 | 1.087 | 0.876 | 0.0171 | 0.0249 |

The selected signal separates the primary normalized target: predicted HIGH_RISK mean is about 42%
higher and median about 53% higher. However raw absolute return, high-low range and Parkinson proxy
are lower in the predicted HIGH_RISK group. The likely interpretation is regime-relative surprise:
the model flags moves large relative to trailing volatility, often in quieter regimes, rather than
the sessions with the largest raw price range. M8 must test this interpretation by ticker, period
and trailing-volatility regime. No stronger claim is justified.

## Coverage and exclusions

Per-ticker eligible counts range from 361 to 396. During label construction, 207 candidate rows
lacked the exact consecutive market bars required by the target protocol. Another 126 labeled rows
lacked the complete 35-session feature history and abstained. No value was forward-filled or
fabricated.

## Immutable evidence

- M7 config SHA-256:
  `fd4d55aeb2e85aa7f01d4c8c60484a192a4fa9463bb0fd13c8135ed803136ca7`.
- Candidate manifest SHA-256:
  `951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81`.
- Opening intent SHA-256:
  `0efdd3881b75358005f983c9eb1b47f8321992b9cf5144d9c00713dbc6abd861`.
- Sealed evaluation SHA-256:
  `4598e92edd7e441c7d8138c8228f1cb5cac77626241d3b668f6ab8f29a925bfe`.
- Completion record SHA-256:
  `3e2fa2f717a22ccb348d47e3c0575c8cc9a5e11940f0d5bff953e3c08d6a01fc`.

The row-level evaluation remains under Git-ignored `.tools/`. It must not be regenerated or used
for selection. This public result contains no credential, private holding, personal information or
raw provider dataset and is not investment advice.

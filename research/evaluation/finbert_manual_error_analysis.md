# FinBERT Manual Error Analysis — M5

Run date: 2026-08-25  
Model: `ProsusAI/finbert@4556d13015211d73dccd3fdd39d39232506f3e43`  
Runtime: CPU, PyTorch 2.13.0, Transformers 4.57.6

## Result

- Synthetic manually labelled English samples: 12
- Correct: 10
- Accuracy: 83.33%
- Positive: 4/4 correct
- Negative: 4/4 correct
- Neutral: 2/4 correct

This is a **pipeline sanity check only** and qualitative error-analysis sample, not a
representative benchmark and not evidence of investment performance.

## Errors

| ID | Expected | Predicted | Neutral probability | Negative probability | Observation |
|---|---|---|---:|---:|---|
| `u03` | neutral | negative | 0.15539204 | 0.83264029 | A director resignation was treated as strongly negative even though the sample annotation treats the administrative change as neutral. |
| `u04` | neutral | negative | 0.40598041 | 0.57010633 | A registered-office address change was weakly negative rather than neutral. |

The small sample suggests that governance or administrative event wording needs targeted review. Downstream features should retain probabilities and source type instead of trusting only the argmax label.

## Reproducibility

Two local runs using the pinned cached checkpoint produced byte-identical JSON reports:

```text
SHA-256 06b486f43df6506cbfaa252bdd8c37071779b20adc1c47a4e264d360f784bb6b
```

The labelled inputs are versioned in `research/evaluation/finbert_manual_samples.json`. Generated full reports belong under ignored `artifacts/` or a temporary directory.

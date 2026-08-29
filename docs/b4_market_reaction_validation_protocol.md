# B4 Market Impact / Reaction Validation Protocol

Status: **FROZEN / B4 corrected five-year evaluation complete**  
Protocol: `b4-market-reaction-validation-v1`  
Date: 2026-08-29

## Research question and task boundary

B4 asks whether Taiwan/Chinese financial text and event representations available at publication
time add predictive information for subsequent market reaction. It is an observational prediction
task, not linguistic-sentiment classification and not a causal-impact design.

The concepts remain separate:

- `LINGUISTIC_SENTIMENT`: `ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED`;
- `EVENT_CLASS`: existing inferred taxonomy status only;
- `MARKET_REACTION`: realized post-publication market-relative movement;
- `FINANCIAL_IMPACT_SIGNAL`: automated hypothesis, not causal impact;
- `MEDIA_TONE`: proxy only.

Market returns are never mapped to positive/neutral/negative sentiment labels. B4 does not reopen
B3.1, reuse its sentiment gate, retrain sentiment models or fabricate sentiment probabilities.

## Frozen targets

The primary continuous target is
`next_eligible_session_signed_abnormal_return`:

```text
stock_return     = stock_close(reaction_session) / stock_close(anchor_session) - 1
benchmark_return = TAIEX(reaction_session) / TAIEX(anchor_session) - 1
target           = stock_return - benchmark_return
```

The secondary target is the absolute value of the primary target. The benchmark is the existing
FinMind `TaiwanStockTotalReturnIndex:TAIEX` snapshot. Raw next-day direction is not a primary target;
the optional directional diagnostic is disabled when the continuous dataset fails sufficiency.

These are associated realized reactions, not proof that an event caused a return.

## Publication-time alignment

All timestamps are converted to `Asia/Taipei`. Accepted timestamp bases are an observed UTC offset
or a previously frozen source-contract assumption. Unknown/naive timestamps abstain.

Using the official exchange-session calendar and daily-close market data:

| Publication case | Anchor | Reaction session |
| --- | --- | --- |
| Before 09:00 on an exchange session | prior exchange close | same-session close |
| 09:00–13:30 on an exchange session | **abstain** | daily data cannot isolate only post-publication movement |
| After 13:30 on an exchange session | same-session close | next exchange-session close |
| Weekend/holiday | prior exchange close | next exchange-session close |
| Unknown timezone | **abstain** | none |

The intraday abstention is deliberately stricter than using prior close, which would contaminate
the target with price movement that occurred before an intraday publication. Calendar date `+1`
is never used as a substitute for the next observed exchange session.

## Inputs and representation

Only B2/B2.1-approved sources may enter. TWMD remains secondary and uses only the frozen B2.1
private metadata fields. Its `event_class` is not sentiment. GDELT requires a safe working access
path; publisher bodies remain forbidden. eLAND is prohibited.

The text candidate is the existing FSC-adapted BERT-base-Chinese representation:

- upstream revision: `8f23c25b06e129b6c986331a13d8d025a92cf0ea`;
- adapted weight SHA-256:
  `eaacc66a4993a448e9e9dd7d6aab0fc33290d1f4e4e4e8d209efc1d7a17fd3b9`;
- encoder is frozen and not retrained in B4;
- only text available by publication cutoff is eligible.

## Deduplication and multi-event aggregation

Exact family identity is the SHA-256 of ticker, normalized subject and local publication date.
Within a family, keep the earliest publication; source priority and source record ID break exact
ties. Duplicate-family members never cross chronological splits.

Distinct events mapping to the same ticker/anchor/reaction window become one modeling row so one
realized market reaction is not counted repeatedly. If a model is later permitted, unique event
embeddings are averaged and metadata uses event counts plus category multi-hot fields.

## Chronological design and compact models

Random splits are forbidden. The intended design is expanding-window rolling origin with at least
three outer evaluation folds and at least 50 aggregated event windows per evaluation fold. Any
inner selection remains inside outer training history, and duplicate families are isolated.

The only frozen candidates are:

1. market context and ticker identity → Ridge;
2. market + event metadata → Ridge;
3. market + metadata + frozen B3 representation → Ridge.

No deep model is stacked on BERT and no classifier is required. The main comparison is whether
text improves over the metadata-only baseline.

## Predeclared gates

The data gate must pass before any model training:

- at least 300 aggregated usable event windows;
- at least 5 tickers and 3 calendar years;
- at least 3 outer folds with at least 50 evaluation windows each;
- reliable timestamp ratio at least 95%;
- market-match ratio at least 90%;
- complete admitted-source dedup coverage.

If it passes, `VALIDATED_RESEARCH_SIGNAL` additionally requires all leakage checks, median outer
Spearman above zero, mean text-minus-metadata Spearman at least `0.02`, positive text increment in
at least two-thirds of folds, text MAE no more than 1% worse, and worst-fold Spearman at least
`-0.05`. Thresholds are frozen before evaluation and cannot be relaxed after results.

Failure of the data gate returns `ABSTAIN_INSUFFICIENT_MARKET_REACTION_DATA`; it does not authorize
training on a tiny sample.

## Final B4 decision

The initial four-row assessment used bounded `limit=2` source probes and was corrected before B4
finalization. The approved private 2021–2025 monthly backfill contains 7,582 events and produces
3,433 modeling windows across nine represented tickers and five years, so the data gate passes.
Three rolling-origin folds evaluate 2023, 2024 and 2025 with fixed Ridge `alpha=100` and fold-local
preprocessing.

Event metadata provides a modest, temporally positive absolute-reaction ranking signal, but frozen
BERT title embeddings do not add robust value beyond metadata. Final maturity is
`AUTOMATED_SIGNAL_ONLY`, not `VALIDATED_RESEARCH_SIGNAL`. Chinese linguistic sentiment remains
`ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED`.

Private source rows, embeddings and OOF predictions remain in ignored storage. Track A, GAS, LINE,
FastAPI deployment and Streamlit remain unchanged. B5 is not started.

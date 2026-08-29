# B4 Market Impact / Reaction Validation Result

Date: 2026-08-29  
Decision: **B4 COMPLETE — corrected full TWMD five-year backfill evaluated**  
`MARKET_REACTION_MODEL`: **AUTOMATED_SIGNAL_ONLY**  
Next executable unit: **B5 — NLP Intelligence Integration; not started**

## Correction record

The first B4 pass incorrectly treated two `limit=2` entitlement/schema probes from 2018 and 2024
as the available TWMD dataset. Those four rows were bounded audit samples, not a historical
coverage claim. After the user identified TWMD's five-year MOPS-derived coverage, B4 acquired the
frozen ten-ticker universe for 2021–2025 under the B2.1 monthly/private contract and reran the
study. The superseded four-row insufficiency decision is not the final B4 result.

## Dataset audit

- 600 bounded ticker-month requests; 7,582 source events; zero provider duplicates;
- 7,424 deterministic subject/date families;
- 7,351 timestamp-eligible events, 53 intraday abstentions and 20 market-match failures;
- 3,433 unique ticker/reaction modeling windows;
- 9 represented tickers; 0050 had zero events;
- five complete publication years, 2021–2025;
- private licensed subjects and predictions remain in Git-ignored `.tools` storage.

Usable windows by year: 585 (2021), 717 (2022), 730 (2023), 713 (2024), 688 (2025).

Usable windows by ticker: 1301 146; 1303 129; 2308 318; 2317 504; 2330 650; 2412 159;
2454 218; 2881 714; 2882 595.

## Target, alignment and deduplication

Primary target is next-eligible-session signed abnormal simple return: stock return minus TAIEX
total-return-index return. Secondary target is absolute abnormal return. Before-open events map
prior close to same-session close; intraday events abstain because daily data cannot isolate the
post-publication interval; after-close events map same close to next exchange close; non-session
events map prior close to next exchange close. Unknown-timezone events abstain.

Family identity hashes ticker, normalized subject and publication-local date; the earliest event
survives within a family. Distinct families sharing a ticker/anchor/reaction window are aggregated,
with mean text embeddings and event-count/category metadata. Future returns never enter inputs.

## Chronological evaluation

Fixed Ridge `alpha=100` models use training-only scaling and training-only category encoding.
There is no random split or outer-fold tuning:

| Fold | Training | Evaluation | Evaluation rows |
| --- | --- | --- | ---: |
| 1 | 2021–2022 | 2023 | 730 |
| 2 | 2021–2023 | 2024 | 713 |
| 3 | 2021–2024 | 2025 | 688 |

## Signed abnormal-return results

Aggregate historical OOF metrics:

| Candidate | MAE | RMSE | R² | Spearman |
| --- | ---: | ---: | ---: | ---: |
| Market only | 0.01040 | 0.01473 | -0.0053 | 0.0349 |
| Market + event metadata | 0.01039 | 0.01478 | -0.0113 | **0.0784** |
| Market + metadata + frozen BERT text | 0.01119 | 0.01561 | -0.1286 | 0.0408 |

Text-model Spearman was 0.0211, 0.0534 and 0.0436 across 2023–2025. Metadata-only Spearman was
0.0373, 0.1144 and 0.0847. Text-minus-metadata Spearman was negative in every fold; mean increment
was -0.0394. Text MAE was also more than 1% worse. The frozen text-increment gate therefore failed.

## Absolute-reaction secondary analysis

| Candidate | MAE | RMSE | R² | Spearman | Top-decile lift |
| --- | ---: | ---: | ---: | ---: | ---: |
| Market only | 0.00681 | 0.01017 | 0.0468 | 0.1892 | 1.453 |
| Market + event metadata | **0.00667** | **0.00999** | **0.0789** | **0.2504** | **1.623** |
| Market + metadata + frozen BERT text | 0.00713 | 0.01062 | -0.0392 | 0.1769 | 1.428 |

Metadata-only magnitude Spearman remained positive in every fold: 0.1434, 0.1960 and 0.3418.
This supports a modest automated event-metadata reaction-magnitude signal, but not a validated
Chinese text contribution.

## Robustness and maturity

The BERT signed model's ticker Spearman ranged from -0.0668 to 0.1298, showing weak and mixed
cross-ticker robustness. The metadata magnitude result is more stable temporally, but this is one
provider, nine represented tickers and a retrospective observational study. No direction model
was trained, no causal claim is made, and no prospective validity is claimed.

Final capability states:

- `LINGUISTIC_SENTIMENT`: `ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED`;
- `MARKET_REACTION_MODEL`: `AUTOMATED_SIGNAL_ONLY`;
- text incremental value: **not supported**;
- `EVENT_CLASS`: inferred TWMD taxonomy, not sentiment truth;
- `MEDIA_TONE`: unchanged proxy status.

## Lineage and boundaries

- TWMD private manifest SHA-256:
  `aa78324c80d12872c8a4023e26184673cdff90552fb8b41bb5b2a635e1f7149d`;
- market snapshot SHA-256:
  `c257f24d2fab6d2e35a73ef36831776b935a943bafcdbb331e559bfd07564f81`;
- frozen encoder weight SHA-256:
  `eaacc66a4993a448e9e9dd7d6aab0fc33290d1f4e4e4e8d209efc1d7a17fd3b9`.
- ignored aggregate result SHA-256:
  `956d19eb2ccd5f37b65bb2f5a8654c576e583c569f20944d71e47b54c9eab731`.

Licensed TWMD subjects are not published. Chinese sentiment was not retrained or inferred from
returns. eLAND, Track A, GAS, LINE, FastAPI, Streamlit and deployment were unchanged. B5 was not
started automatically.

# M5.1 Traditional Chinese Sentiment Model Comparison

Run date: 2026-08-25  
Runtime: CPU, PyTorch 2.13.0, Transformers 4.57.6  
Decision: **No Chinese model is approved for M6 features yet.**

## Evaluation contract

Two pre-existing labelled diagnostic sets are versioned with this historical report. They are
retained as rejection evidence; the project will not create, extend or manually review labels:

1. `chinese_financial_sentiment_samples.json`: 36 balanced synthetic Traditional Chinese finance sentences, 12 per class. This is a regression set with explicit language and is intentionally easy.
2. `twse_announcement_sentiment_samples.json`: 30 public TWSE announcement-derived title/context samples, labelled for event-aware market sentiment: 8 positive, 17 neutral and 5 negative. Text is shortened and excludes personal names.

The second set is closer to the retained M4 input contract but remains small and singly annotated. It is not a publishable benchmark.

Adoption gate:

- Macro-F1 ≥ 0.70 on the TWSE-derived set.
- Recall ≥ 0.60 for every class on the TWSE-derived set.
- Pinned revision, local inference, acceptable licence and traceable input policy.

## Candidates

| Profile | Pinned model | Licence | Local cache | Important limitation |
|---|---|---:|---:|---|
| Lexicon | `chinese-financial-lexicon@v1` | project code | none | Transparent but has very limited coverage and no learned context. |
| Yiyang | `yiyanghkust/finbert-tone-chinese@e91b1a3…` | Apache-2.0 | 390 MB | Training data is a private set of about 8,000 analyst-report sentences. |
| bards.ai | `bardsai/finance-sentiment-zh-base@33595d1…` | Apache-2.0 | 391 MB | Trained on a translated Financial PhraseBank, creating translation/domain risk. |
| Multilingual v2 | `Kenpache/finbert-multilingual-v2@d6a74c2…` | Apache-2.0 | 1.2 GB | Largest footprint; tokenizer metadata targets a newer Transformers runtime. |
| Translation + FinBERT | `opus-mt-zh-en@cf10909…` → `ProsusAI/finbert@4556d13…` | CC-BY-4.0 / FinBERT model terms | 598 MB + existing FinBERT | Two-model latency and observable translation errors. |

## Results

### Balanced synthetic set

| Profile | Accuracy | Macro-F1 |
|---|---:|---:|
| Lexicon | 0.861 | 0.865 |
| Yiyang | 1.000 | 1.000 |
| bards.ai | 0.944 | 0.944 |
| Multilingual v2 | 1.000 | 1.000 |
| Translation + FinBERT | 0.889 | 0.888 |

These high scores show that explicit synthetic finance wording is not a sufficient selection test.

### TWSE-derived context set

| Profile | Accuracy | Macro-F1 | Positive recall | Neutral recall | Negative recall | Gate |
|---|---:|---:|---:|---:|---:|---|
| Lexicon | 0.600 | 0.320 | 0.125 | 1.000 | 0.000 | Fail |
| Yiyang | 0.600 | 0.357 | 0.000 | 1.000 | 0.200 | Fail |
| bards.ai | 0.633 | 0.442 | 0.000 | 1.000 | 0.400 | Fail |
| Multilingual v2 | 0.733 | 0.640 | 0.125 | 1.000 | 0.800 | Fail |
| Translation + FinBERT | 0.633 | 0.592 | 0.250 | 0.824 | 0.600 | Fail |

The direct classifiers collapse many short corporate-disclosure statements to neutral. Multilingual v2 recognizes negative events best but misses seven of eight positive events. Translation + FinBERT has the best positive recall but mistranslated `庫藏股` as “vault” and interpreted `增資` as “raise the loan”.

## Reproducibility

Two cached runs of all five profiles on the TWSE-derived set produced byte-identical labels, probabilities, metrics and errors after excluding timing fields:

```text
SHA-256 fa1d793fe2395aee9fa6ba4efa5ce324ec64446e6aad5ceb8fee60940014772c
```

## Decision and zero-manual-label research direction

M5 continues to score English only. `zh-TW` records remain explicitly skipped and receive no neutral placeholder.

The failed candidates remain rejected. The Taiwan track now proceeds without manual annotation,
manual label review or human adjudication:

1. Learn text representations from accepted, audited, unlabelled Taiwan financial corpora.
2. Use structured official metadata, deterministic event rules and versioned weak-supervision sources.
3. Generate market-reaction targets mechanically under the temporal protocol.
4. Evaluate event-type and representation features with chronological, sealed out-of-sample
   downstream experiments; do not force every disclosure into one latent sentiment concept.

This decision preserves the core experiment: the recorded gate remains failed, formal Chinese
sentiment remains unsupported, and any future Taiwan text signal must be described as automated
weak/reaction supervision rather than human-validated sentiment ground truth.

## Primary model documentation

- [yiyanghkust Chinese FinBERT](https://huggingface.co/yiyanghkust/finbert-tone-chinese)
- [bards.ai Chinese finance sentiment](https://huggingface.co/bardsai/finance-sentiment-zh-base)
- [Kenpache multilingual financial sentiment](https://huggingface.co/Kenpache/finbert-multilingual-v2)
- [Helsinki OPUS Chinese-to-English](https://huggingface.co/Helsinki-NLP/opus-mt-zh-en)
- [ProsusAI FinBERT](https://huggingface.co/ProsusAI/finbert)

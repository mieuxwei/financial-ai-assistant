# Sentiment Language Strategy

## M5 decision

The pinned `ProsusAI/finbert` model is tagged English by its official model card and was fine-tuned for financial sentiment with English Financial PhraseBank text. M5 therefore supports language codes `en` and `en-*` only.

Chinese TWSE records (`zh-TW`) are counted as `skipped_language_pairs`. They do not receive zeroes, neutral labels, translated text, or synthetic probabilities. This prevents a technically valid pipeline from creating scientifically invalid Chinese sentiment features.

## Why automatic translation is deferred

Automatic translation would introduce another model, version, latency, cost and potential semantic distortion. It could also send retained text to an external provider. No Gemini, Perplexity or other LLM is used in M5 sentiment ingestion.

## Historical M5.5 Chinese diagnostic

The completed historical M5.5 diagnostic compared these controlled options on a small pre-existing Traditional Chinese diagnostic set:

1. A documented Chinese or multilingual financial sentiment classifier.
2. A pinned local translation model followed by the same FinBERT revision.
3. A transparent lexicon or classical baseline.

The recorded macro-F1, per-class recall, calibration, inference cost, model licence, input retention policy and error categories remain rejection evidence for formal Chinese sentiment and must never overwrite the English result.

## M5.5 outcome

The controlled comparison is complete. Five profiles were evaluated on both an easy balanced synthetic set and a small TWSE announcement-derived context set. None passed the TWSE adoption gate of macro-F1 ≥ 0.70 and recall ≥ 0.60 for every class.

The best TWSE macro-F1 was 0.640 from `Kenpache/finbert-multilingual-v2`, but its positive recall was only 0.125. Translation followed by English FinBERT reached macro-F1 0.592 and exposed material financial-term translation errors. Chinese sentiment therefore remains disabled. Full results and pinned revisions are recorded in `research/evaluation/chinese_sentiment_model_comparison.md`.

## Revised Taiwan-domain direction

The next track is not a generic Chinese sentiment substitution. The project uses no human annotation or human review. Taiwan disclosures produce automated, versioned event/impact proxies, model-consensus metadata and `AMBIGUOUS`／`ABSTAIN` states. These are silver research signals, not semantic ground truth. Linguistic tone, event impact and historical market reaction remain separate in storage and experiments.

M6 audits active corpora and sources. M7 evaluates domain-adaptive frozen representations, M8
builds automatic market-reaction targets, and M9 aggregates versioned weak signals. M11 compares
their downstream out-of-sample value rather than human-label accuracy. Historical future/abnormal
returns can never be an event-time feature.

The active audit queue is `tw-finance-159M`, MOPS/TWSE, FinMind, optional FSC/regulatory text and
historical stock/benchmark prices. Eland is excluded and retained only as a historical HOLD record.

References:

- [ProsusAI/finbert model card](https://huggingface.co/ProsusAI/finbert)
- [Pinned model metadata](https://huggingface.co/api/models/ProsusAI/finbert)
- [Hugging Face text classification guide](https://huggingface.co/docs/transformers/main/tasks/sequence_classification)

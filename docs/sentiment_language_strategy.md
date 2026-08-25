# Sentiment Language Strategy

## M5 decision

The pinned `ProsusAI/finbert` model is tagged English by its official model card and was fine-tuned for financial sentiment with English Financial PhraseBank text. M5 therefore supports language codes `en` and `en-*` only.

Chinese TWSE records (`zh-TW`) are counted as `skipped_language_pairs`. They do not receive zeroes, neutral labels, translated text, or synthetic probabilities. This prevents a technically valid pipeline from creating scientifically invalid Chinese sentiment features.

## Why automatic translation is deferred

Automatic translation would introduce another model, version, latency, cost and potential semantic distortion. It could also send retained text to an external provider. No Gemini, Perplexity or other LLM is used in M5 sentiment ingestion.

## Required Chinese experiment before M6 research use

Before Chinese sentiment enters model features, compare at least these controlled options on a manually labelled Traditional Chinese financial sample:

1. A documented Chinese or multilingual financial sentiment classifier.
2. A pinned local translation model followed by the same FinBERT revision.
3. A transparent lexicon or classical baseline.

Record macro-F1, per-class recall, calibration, inference cost, model licence, input retention policy and error categories. The chosen path must be versioned separately from the English result and must never overwrite it.

## M5.1 outcome

The controlled comparison is complete. Five profiles were evaluated on both an easy balanced synthetic set and a small TWSE announcement-derived context set. None passed the TWSE adoption gate of macro-F1 ≥ 0.70 and recall ≥ 0.60 for every class.

The best TWSE macro-F1 was 0.640 from `Kenpache/finbert-multilingual-v2`, but its positive recall was only 0.125. Translation followed by English FinBERT reached macro-F1 0.592 and exposed material financial-term translation errors. Chinese sentiment therefore remains disabled. Full results and pinned revisions are recorded in `research/evaluation/chinese_sentiment_model_comparison.md`.

References:

- [ProsusAI/finbert model card](https://huggingface.co/ProsusAI/finbert)
- [Pinned model metadata](https://huggingface.co/api/models/ProsusAI/finbert)
- [Hugging Face text classification guide](https://huggingface.co/docs/transformers/main/tasks/sequence_classification)

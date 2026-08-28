# Taiwan Financial NLP Data Source Decisions

Last reviewed: 2026-08-28

## Decision summary

No inspected public candidate provides a reproducible human gold set. The project has explicitly
chosen a zero-human-annotation and zero-human-review route. The authoritative, field-complete
source decisions are maintained in `research/evaluation/taiwan_dataset_governance.md`.

| Candidate | Intended use | Decision | Reason |
| --- | --- | --- | --- |
| `p988744/eland-sentiment-zh` | Historical rejection evidence only | HOLD / excluded from active modeling | Mixed-domain and non-financial contamination; raw splits, distribution, duplicates, leakage, provenance and domain purity could not be fully audited. No rescue or re-audit is planned. |
| [`lianghsun/tw-finance-159M`](https://huggingface.co/datasets/lianghsun/tw-finance-159M) | Domain-adaptive pretraining | Active audit target; currently HOLD | Unlabelled, gated, non-commercial share-alike licence, and underlying article rights still require audit. It cannot provide event/impact gold labels. |
| [Taiwan Financial Sentiment Dictionary](https://github.com/RemiMFB/Taiwan-Financial-Sentiment-Dictionary) | Interpretable lexicon baseline | Auxiliary only | A lexicon is not an entity/event-labelled corpus. The historical M5.5 lexicon diagnostic also failed the project adoption gate. |
| Fin-SoMe academic annotations | Historical/social-media comparison | HOLD | Task/domain differ from official company-event impact and the non-commercial research licence remains unaudited. |
| Official MOPS/TWSE announcements sampled by time/event group | Structured metadata and automated text signals | ACCEPT for ingestion/metadata; training CONDITIONAL | Live OpenAPI and official fields verified; retention/licence, duplicate and leakage gates still apply to corpus use. |
| FinMind `TaiwanStockNews` | Deduplicated title-level discovery/intelligence | CONDITIONAL; reaction events and rich-text use HOLD | A 2018–2024 ten-ticker stratified audit retrieved 1,547 rows, but 2018–2019 samples were empty, descriptions were absent, exact-link duplicates were 25.21%, and all timestamps were timezone-naive with undocumented semantics. |
| Official FSC law archives | Optional domain adaptation | ACCEPT for filtered non-commercial unlabelled adaptation feasibility | Five checksummed archives passed automated ZIP/schema/XML audit: 6,047 records, no exact or cross-agency content duplicates, 14 within-agency duplicate-content extra rows, ten unparseable publication dates and one empty content record. Mandatory filtering/deduplication applies; never sentiment truth. |
| FinMind `TaiwanStockTotalReturnIndex` / `TAIEX` | Automatic market-reaction benchmark | ACCEPT for non-commercial research | Live anonymous bounded request and documented total-return schema verified; snapshot/calendar and deployment re-audit still apply. |
| Historical individual stock prices | Automatic stock-return targets | CONDITIONAL | Must pass provider licence, calendar, corporate-action, missing-data and sealed-test leakage controls. |

## Minimum automated-data contract for M6

These are project entry gates, not claims of semantic label correctness. Before experimentation:

1. Keep the 60-item Gemini-versus-Codex round as an AI stability diagnostic only.
2. Build a deduplicated chronological corpus with traceable timestamps, tickers and text hashes.
3. Generate deterministic metadata, frozen embeddings and versioned AI event/impact proxies.
4. Record model/prompt provenance, agreement, confidence, coverage and abstention for every run.
5. Keep the frozen 30-item historical M5.5 diagnostic outside model and threshold selection.
6. Evaluate signal adoption using chronological validation, sealed market-prediction test and
   walk-forward periods; fit all thresholds and preprocessing on training/validation only.
7. Preserve negative results and report bootstrap uncertainty before any predictive-value claim.

If provenance, leakage controls or out-of-sample evaluation cannot be satisfied, the affected
source remains `HOLD` or `CONDITIONAL` and cannot enter active modeling.

## Automated responsibility

No person labels or reviews records. Low-confidence, invalid and model-disagreement cases remain
`AMBIGUOUS`, `ABSTAIN` or missing under a versioned rule. Historical returns are computed separately
as market-reaction or downstream prediction targets and are never exposed to event-time labelers.

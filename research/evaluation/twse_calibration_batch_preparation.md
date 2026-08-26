# TWSE Calibration Batch Preparation

Prepared: 2026-08-26  
Status: **unlabeled calibration input — not training data**

## Local preparation result

- Public source: TWSE material-announcement OpenAPI
- Fetched announcements: 114
- Article/ticker matches: 115
- Selected calibration records: 60
- Distinct selected tickers: 60
- Event labels present: no
- Impact labels present: no
- Future price/return fields present: no
- `include_for_training`: false for every record
- Local output: `artifacts/twse-calibration-batch.jsonl` (Git ignored)

The exporter excludes exact matches from the frozen M5.1 diagnostic text, removes repeated
content/title fingerprints and round-robins across tickers. It retains the official source URL,
publication timestamp, ticker/entity, short publication-time context and hashes.

Two blinded Excel workbooks were generated under the ignored
`outputs/m6_1_calibration_20260826/` directory. Each contains Instructions, Annotation and
Taxonomy sheets, four input validations, 60 blank event/impact rows and formula-driven QC status.
Reviewer A and Reviewer B must receive only their own workbook.

## Interpretation

This batch is not a gold dataset and provides no model result. It is the first double-annotation
calibration input defined by the M6.1 protocol. Reviewers must work only from the retained text,
without future returns or later market commentary. After both reviewers finish, agreement and
conflicts must be computed with `financial-ai-taiwan-annotation-agreement` before any record is
admitted to training.

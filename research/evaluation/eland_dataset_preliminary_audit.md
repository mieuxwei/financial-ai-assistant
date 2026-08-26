# Eland Sentiment ZH Preliminary Dataset Audit

Audit date: 2026-08-26  
Historical candidate: `p988744/eland-sentiment-zh`
Decision: **HOLD / EXCLUDED FROM ACTIVE MODELING PIPELINE**

## Scope and evidence boundary

This is a preliminary metadata and public-viewer review, not a full raw-data audit. The raw
split files could not be downloaded from the available environment because the official
download endpoints returned HTTP 401. A live browser check on 2026-08-26 subsequently returned
HTTP 404 for both the dataset root and file tree. The repository may have been removed, renamed
or made private. No alternate mirror was used and no dataset text was committed.

The [official dataset card](https://huggingface.co/datasets/p988744/eland-sentiment-zh)
declares Apache-2.0 and describes:

- a `raw` configuration with 999 train, 300 validation and 300 test rows;
- a `chat` configuration with 1,887 train, 360 validation and 360 test rows;
- overall, entity and opinion sentiment tasks;
- positive, neutral and negative labels;
- raw examples containing `text`, `overall`, `task`, `source`, and optional entity fields.

These are publisher claims and public metadata. They do not independently establish the
licence or redistribution rights of every underlying source text.

## Preliminary findings

The public `chat` viewer visibly mixes Taiwan company announcements and finance material with
non-financial or off-domain content such as astrology, games, general social discussion and
malformed markup. It also shows both Traditional and Simplified Chinese. This is sufficient to
reject an assumption that every row is Taiwan financial text, but not sufficient to estimate
the full contamination rate.

The published raw-format examples expose a generic `source` field but do not document the
per-record `source_url` and `published_at` fields required by the project protocol. Without the
raw splits, the following remain unverified:

- actual schema and missing-value rates;
- label and task distributions;
- exact and near-duplicate leakage across splits;
- conflicting labels for duplicated text;
- full finance-domain and Traditional-Chinese coverage;
- per-record source provenance and retention rights.

## Final project decision

**Historical candidate — HOLD / excluded from active modeling.** The dataset is not an active
candidate and will not be rescued or re-audited during this milestone. It is retained only as
historical dataset-audit and rejection evidence. Cached search results, unknown mirrors and the
`chat` configuration are not acceptable substitutes for the unavailable raw source.

Eland is prohibited from all active project uses, including:

- model training or MacBERT fine-tuning;
- domain-adaptive pretraining or corpus merging;
- weak-supervision voting or feature construction;
- formal evaluation, ground-truth labels or future active dataset experiments.

The preserved rejection rationale is: mixed-domain public samples, non-financial contamination,
abnormal or inconsistent markup, unavailable full raw splits, and unverified full label
distribution, duplicate rate, cross-split leakage, provenance and financial-domain purity. This
record does not authorize any future active use.

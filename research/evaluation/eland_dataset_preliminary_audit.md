# Eland Sentiment ZH Preliminary Dataset Audit

Audit date: 2026-08-26  
Candidate: `p988744/eland-sentiment-zh`  
Decision: **HOLD — not approved for M6.2 training**

## Scope and evidence boundary

This is a preliminary metadata and public-viewer review, not the required full raw-data
audit. The official Hugging Face page was inspected, but the raw split files could not be
downloaded from the available environment because the official download endpoints returned
HTTP 401. No alternate mirror was used and no dataset text was committed.

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

## Go/no-go decision

**No-go for training; hold for full audit.** The dataset may be reconsidered only after all
official raw splits are available locally, their immutable revision/hash is recorded, and the
automated report plus manual provenance/domain review pass. The `chat` configuration must not
be used as a shortcut because it expands and reformats the data without solving traceability or
domain-quality concerns.

If the raw files become available, keep them under the ignored
`.tools/datasets/eland-sentiment-zh/` path and run:

```bash
python -m pip install -e ".[audit]"
financial-ai-taiwan-dataset-audit \
  --split train=.tools/datasets/eland-sentiment-zh/raw/train.parquet \
  --split validation=.tools/datasets/eland-sentiment-zh/raw/validation.parquet \
  --split test=.tools/datasets/eland-sentiment-zh/raw/test.parquet \
  --dataset-id p988744/eland-sentiment-zh \
  --dataset-revision "<immutable-revision>" \
  --declared-license apache-2.0 \
  --output artifacts/eland-sentiment-zh-audit.json
```

The output contains aggregate counts and hashes, not raw text. An automated pass is necessary
but never replaces manual source, copyright and domain review.

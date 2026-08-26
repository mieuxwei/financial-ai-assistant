# FSC Official Archive Automated Audit — M6

Audit date: 2026-08-26  
Scope: five user-approved official FSC Open Data ZIP snapshots  
Method: deterministic archive/schema/XML/date/hash statistics only  
Excluded: manual review, manual labels, raw-text reporting, training, redistribution and deployment

## Purpose-specific decision

**`ACCEPT` for an unlabelled, non-commercial Taiwan financial/regulatory domain-adaptation
feasibility corpus, only after the automated filters below are applied.**

This is not an acceptance as sentiment ground truth, impact labels, event-reaction truth or a
redistributable public dataset. It does not approve a model-training run by itself. Public or
commercial deployment requires a new rights review.

## Snapshot and integrity result

The approved archives were downloaded only to Git-ignored
`.tools/datasets/fsc-official/`. Their byte sizes matched the prior HEAD observations and their
SHA-256 values are pinned in
`research/configs/fsc_official_archive_snapshot.v1.json`. All five passed ZIP CRC, safe-member-path,
member-count, uncompressed-size, UTF-8 CSV, XML-root and 15-field schema checks.

| Official archive | ZIP bytes | XML records | Exact duplicate rows | Duplicate content extra rows |
| --- | ---: | ---: | ---: | ---: |
| FSC commission | 224,273 | 116 | 0 | 0 |
| Banking Bureau | 2,217,525 | 1,557 | 0 | 1 |
| Securities and Futures Bureau | 2,661,534 | 2,431 | 0 | 8 |
| Insurance Bureau | 2,054,245 | 1,843 | 0 | 4 |
| Financial Examination Bureau | 67,102 | 100 | 0 | 1 |
| **Total** | **7,224,679** | **6,047** | **0** | **14** |

No exact-record or content-hash duplicate crossed agency archives. No audited text field contained
the tested control characters or HTML-like markup. One Insurance Bureau record had an empty
`法規內容` field.

## Date and missing-field findings

- `公發布日` was present on all 6,047 records; 6,037 parsed and 10 require deterministic exclusion
  from time-aligned experiments.
- `修正日期` was present on all records; 6,046 parsed and one requires exclusion from date-dependent
  use.
- `生效日期` is legitimately optional: 2,559 values were present and two did not parse.
- `系統異動時間` is optional and contains a `1900-01-01` sentinel in two agency archives. It must
  not replace publication time or be used as an event timestamp.
- `法規名稱`, `主旨`, `法規沿革`, `生效日期`, `立法理由` and attachments are record-type-dependent
  optional fields. High missingness in these fields is therefore retained as an aggregate quality
  fact rather than imputed.

## Mandatory automated corpus filters

Before an M7 feasibility run:

1. use only the official XML text and exclude `圖表附件` plus any special/third-party work;
2. require non-empty normalized `法規內容` and a parseable `公發布日`;
3. deduplicate by normalized `法規內容` hash before chronological splitting;
4. group document revisions using agency, document number and available identity fields;
5. keep revision/document families in one split and fit all preprocessing on training data only;
6. preserve snapshot SHA-256, source agency, publication/revision dates and transformation version;
7. emit only statistics, configuration and hashes outside ignored storage;
8. retain the source attribution, integrity and non-commercial restrictions;
9. treat all official categories as metadata, never human-validated sentiment labels.

## Reproducibility

Run from the repository root after the ignored archives are present:

```bash
financial-ai-fsc-archive-audit \
  --snapshot research/configs/fsc_official_archive_snapshot.v1.json \
  --archive-dir .tools/datasets/fsc-official \
  --output artifacts/fsc-official-archive-audit.json
```

The ignored JSON report records aggregate counts and hashes only and explicitly records
`raw_content_stored=false`, `manual_labels_used=false` and `manual_review_used=false`.

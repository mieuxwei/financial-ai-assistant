# B2.1 TWMD Secondary-Source Amendment

Status: **COMPLETE — contract/provider ready; no dataset ingestion; B3 not started**  
Date: 2026-08-29  
Source decision: **ACCEPT_SECONDARY**

## Purpose and immutability boundary

B2.1 adds a versioned contract and fail-closed provider for TWMD major-event metadata. It does not
modify the frozen B2 v1 source list, normalized snapshot, hashes or results. It also does not make
TWMD a primary source, download a historical corpus or authorize B3 automatically.

Accepted scope:

- MOPS-derived major-event title/subject;
- ticker and market identity;
- disclosure date and second-resolution local clock;
- derived event class, classifier confidence and rule version;
- current issuer classification as a separate mapping helper.

The derived class/confidence are automated TWMD metadata. They are not official MOPS fields,
human-reviewed labels, sentiment truth or impact ground truth.

## Frozen runtime request contract

Endpoint:
`GET https://api.twmarketdata.com/v2/datasets/major-event-taxonomy`

The live contract uses exactly:

- `ticker`;
- `date_from`;
- `date_to`;
- `limit`.

The public documentation's `symbol`, `start_date` and `end_date` examples are rejected because the
bounded re-audit showed that the live endpoint ignored those names. Every response must echo the
four requested filters through `request_context.filters`. A missing or mismatched echo fails the
batch before any row is normalized.

Safety bounds:

- explicit single ticker only;
- maximum 31 calendar days per request;
- maximum 100 requested rows;
- response larger than 1 MB is rejected;
- any row outside the requested ticker/date window is rejected;
- a page whose row count reaches `limit` is treated as potentially truncated and rejected; the
  caller must split the window rather than silently accept incomplete coverage.

These are ingestion-safety bounds, not a completeness claim.

## Timestamp contract

TWMD returns `event_date` and `event_time` without an offset. B2.1 preserves the original fields
and constructs an aware timestamp under the frozen `Asia/Taipei` source-contract assumption.
Every normalized row records:

- `timezone=Asia/Taipei`;
- `timezone_basis=SOURCE_CONTRACT_ASSUMPTION_NO_OFFSET_IN_API`;
- timestamp semantics stating that the value is a MOPS-derived disclosure clock, not a market
  session timestamp.

If TWMD later adds an offset or changes semantics, the current parser must fail review rather than
silently reinterpret historical rows.

## Identity, versions and duplicates

Document identity:

```text
sha256(ticker + event_date + event_time + normalized subject + rule_version)
```

Version identity:

```text
sha256(document_id + content_hash)
```

Exact duplicate identities inside one response are collapsed and counted. Changed subject,
classification, confidence or rule version produces a new immutable version. Cross-run storage
must never overwrite an existing version with different bytes.

## Rights and storage

Rights tier: `LICENSED_EVENT_METADATA_PRIVATE`.

- The API key is read from an injected runtime secret and never placed in URLs, logs, reports or
  Git.
- Raw responses may exist only in ignored/private storage.
- Normalized subjects and event metadata remain private by default.
- Public output is limited to code, schemas, counts, hashes, aggregate metrics and separately
  permitted attributed excerpts.
- Bulk mirroring, redistribution, full-text republication and trial/quota circumvention are
  prohibited.
- Loss of Pro entitlement stops new acquisition; it must not silently fall back to scraping.

## Collection and recovery design

No scheduler is deployed in B2.1. If later approved, the forward design uses 22:30 Asia/Taipei and
08:00 next-day reconciliation runs. Historical acquisition requires separately approved bounded
ticker/month windows. Retry is limited to three attempts for transient failures.

A batch is rejected and writes no normalized rows when authentication fails, entitlement is lost,
the filter echo changes, required fields disappear, a row escapes the requested window, the
response reaches its limit, timestamps fail parsing or response size exceeds the cap.

## B3 gate

The provider and contract are ready, but **no TWMD dataset snapshot was constructed**. Therefore:

- B2 v1 remains the active B3 dataset;
- TWMD rows cannot enter B3 merely because the connector exists;
- a future private B2.1/B2-v2 snapshot must record ticker/date coverage, zero-row windows,
  duplicates, response hashes, rejected batches and dataset hash before TWMD features are enabled;
- any future event-class feature must be labelled automated metadata and compared without claiming
  human-validated sentiment.

This amendment completes the TWMD source-contract gate only. It does not train or evaluate a
model, modify GAS, alter Track A, deploy a collector, commit or push.

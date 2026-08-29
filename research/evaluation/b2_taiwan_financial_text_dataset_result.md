# B2 Taiwan Financial Text Dataset Result

Run date: 2026-08-29  
Decision: **PASS — normalized v1 snapshot and long-term update contract frozen**  
Training/manual labels: **none**

Post-freeze addendum (2026-08-29): a bounded Pro re-audit reclassifies TWMD as
`ACCEPT_SECONDARY` for major-event taxonomy and issuer-mapping metadata only. B2 v1 remains
unchanged and contains no TWMD rows. The B2.1 source-contract/provider amendment has now passed,
but no TWMD dataset snapshot was constructed; company news and private-beta MOPS remain HOLD. See
`research/evaluation/twmd_pro_reaudit_result.md` and
`research/evaluation/b2_1_twmd_secondary_source_result.md`.

## Frozen artifacts

- Contract/config: `research/configs/b2_taiwan_financial_text.v1.json`
- Config SHA-256: `e4f89eacd3b4e101ee9584e155990a917e4c892828d03e29a8389f7ba1568c80`
- Schema/builder/immutable collection primitives: `pipelines/news/b2_dataset.py`
- TPEx official CSV provider: `pipelines/news/tpex_material.py`
- CLI: `jobs/b2_dataset.py` / `financial-ai-b2-dataset`
- Long-term contract: `docs/b2_data_acquisition_and_update_contract.md`
- Tests: `tests/unit/test_b2_dataset.py` and provider tests

## Historical normalized snapshot

B2 reused the previously audited, ignored `fsc-domain-corpus-v1`; it did not download or rebuild
the FSC source archives. The normalized private dataset is stored only under ignored
`.tools/datasets/b2-taiwan-financial-text-v1/` and occupies approximately 27 MB.

| Split | Records | Publication range in the inherited family-isolated split | SHA-256 |
| --- | ---: | --- | --- |
| train | 5,117 | 1928-10-26–2022-12-30 | `4be7219a6ff80cf5b61e61f1a6905ebaace25cba7340c6af2d1215d68e6f068b` |
| validation | 482 | 2004-11-24–2024-12-31 | `d6bb49c7e22f0ff62980ae9b9cb340234d3e315af982a0b1d1e5f2f223d1997a` |
| test | 422 | 2010-10-25–2026-08-24 | `cf3875ba2cc0241003e3451ffd55fe7b21cd2de7fa8de13d3db2d3e775a03e21` |
| total | **6,021** | inherited family-isolated assignment | — |

The apparent overlapping calendar ranges are expected: the prior FSC builder assigns an entire
document family using its latest publication date, preventing family leakage across splits. B2 did
not redefine or optimize those boundaries.

- Source FSC corpus SHA-256:
  `389640a2f3232cb95bc8c47032673ba8f90a8d5eb23affc1f01a03971d20366c`
- B2 normalized semantic dataset SHA-256:
  `26489f31ca27e2541c09da5dda86af0cb597c989efeb138a14f66a9f18bdab11`
- Private manifest file SHA-256:
  `3f839a5b5cfebc7b2246acb680261a189746ef093b2f416c17429bbf5d615ddf`

The snapshot contains no sentiment/impact labels and no invented ticker mapping. It is approved
for Taiwan financial-domain representation work under existing non-commercial/rights boundaries,
not sentiment truth.

## Forward-source baseline

| Source | B2 v1 normalized rows | Result |
| --- | ---: | --- |
| TWSE current daily official source | 0 | Existing provider/schema audit preserved; collector contract frozen; no raw response added to B2 snapshot |
| TPEx current daily official source | 0 | Bounded schema probe passed: 65/65 logical rows parsed, nine required fields present, all timestamps timezone-aware; raw temp file not retained in repo |
| GDELT metadata | 0 | Max-25 metadata probe stopped on expired server TLS certificate; verification was not bypassed and no data was accepted |

Zero forward rows are explicit baseline counts, not missing records silently interpreted as no
news. TWSE/TPEx are forward streams and do not imply historical backfill. GDELT stays an approved
secondary architecture component, but B2 v1 uses the frozen fallback stack until a bounded,
certificate-valid metadata query is reproducible. Publisher article bodies remain prohibited.

## Research and operational safety

- B2 source list exactly equals the B1 whitelist.
- Official announcements, media news and domain corpus remain separate.
- All normalized timestamps are timezone-aware and include declared semantics/precision.
- Exact retries are no-ops; changed content creates a second immutable version.
- Synthetic tests cover whitelist rejection, no-wait rule, media-body rejection, cross-source
  rejection, idempotency, revision preservation and reproducible FSC construction.
- Daily collection and model refresh are separate; automatic retraining is forbidden.
- No deployment, paid service, model training, pseudo-labeling, manual labeling, GAS/LINE change,
  commit or push occurred.

## Completion decision

B2 passes with the **official-and-domain fallback dataset** plus the complete long-term acquisition
contract. Waiting for future announcement accumulation is not required. The next and only
executable unit is **B3 — Domain Adaptation & Candidate Signals**; do not begin it automatically.

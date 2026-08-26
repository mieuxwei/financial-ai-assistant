# Taiwan Dataset Governance Register

Last reviewed: 2026-08-26  
Status: metadata-level governance; no corpus download or training authorized by this document

Decision vocabulary is restricted to `ACCEPT`, `CONDITIONAL`, `HOLD` and `REJECT`. An `ACCEPT`
decision applies only to the stated purpose; it does not automatically authorize redistribution,
model training or a different use. `Unverified` means the project has not obtained sufficient
evidence in the current environment.

| Source / dataset | Purpose type | Language | Taiwan relevance | Labels | Provenance | Licence | Accessible in current environment | Duplicate audit | Split leakage | Domain purity | Recommended use | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MOPS / TWSE official disclosures | Official disclosure ingestion; structured event metadata | Primarily zh-TW | High | Official disclosure categories and company codes; no sentiment or impact truth | Official URLs, timestamps, external IDs and company identifiers are retained by the existing M4 contract | Public access confirmed; retention and redistribution terms require source-specific audit before corpus use | Yes for the existing official providers and local 114-record ingestion evidence | Existing exact/fuzzy article deduplication; corpus-wide near-duplicate and correction grouping pending | Event-group chronological isolation designed; full historical audit pending | High for official company disclosures; category and period coverage still require measurement | Active source for traceable disclosure text, timestamps and structured metadata; training text only after retention/licence audit | CONDITIONAL |
| FinMind | Taiwan news/market data candidate; timestamp alignment and reaction construction | zh-TW and structured market data | High | No human sentiment truth; market fields can support mechanical reaction targets | Provider/source lineage must be retained per record and reconciled with original publishers | API/dataset and underlying news rights require audit for each endpoint and intended retention | Unverified in the current environment | Unverified; must deduplicate against MOPS/TWSE and within provider | Chronological and event-group leakage audit pending | Likely mixed by endpoint; unverified | Active audit target for Taiwan news, market alignment and automatic reaction targets | CONDITIONAL |
| `lianghsun/tw-finance-159M` | Taiwan financial-domain language adaptation | Chinese; exact Traditional/Simplified ratio unverified | Claimed high; must be measured | Unlabelled | Dataset publisher metadata available; record-level source lineage and underlying rights unverified | Declared non-commercial/share-alike constraints and underlying text rights require legal-purpose audit | Gated/not imported; raw corpus not audited in the current environment | Unverified | No supervised split claimed; temporal/near-duplicate contamination remains unverified | Claimed financial; full automated purity statistics unavailable | Active audit target for domain-adaptive language modeling only; never sentiment ground truth | HOLD |
| Taiwan FSC / regulatory corpus | Optional Taiwan financial/regulatory language adaptation | Primarily zh-TW | High for regulation; narrower than company news | Unlabelled or official document taxonomy only | Must preserve official document URL, publication time, agency and document identifier | Source-specific reuse, retention and redistribution terms unverified | Not assembled or audited in the current environment | Unverified | Chronological/document-family isolation pending | Expected high regulatory purity; unverified across proposed collection | Active audit target; use only after a bounded corpus manifest and rights review pass | HOLD |
| Historical stock and benchmark prices | Automatic market-reaction targets | Structured numeric data | High | Mechanically computed returns/reaction classes, not sentiment labels | Provider, ticker mapping, session calendar and immutable snapshot hash required | Provider licence and redistribution restrictions must be audited | Existing Yahoo-backed market pipeline is available; benchmark series selection remains pending | Primary-key/upsert controls exist; revision audit required | Strictly target-side; threshold/beta/test leakage controls specified in protocol | Not text; market coverage/quality governed separately | Active source for automatic raw, benchmark and abnormal-return targets under the market-reaction protocol | CONDITIONAL |
| Taiwan Financial Sentiment Dictionary | Interpretable weak-supervision labeling function | zh-TW | Medium to high, coverage-dependent | Lexicon polarity | Public repository; term-level origin and revision must be pinned | Exact reuse and redistribution terms require verification | Existing diagnostic implementation is available; source snapshot governance pending | Not applicable to article splits; duplicate terms/conflicts must be audited | Must freeze lexicon before sealed test | Financial vocabulary, but sparse/context-free; diagnostic macro-F1 was 0.320 | Optional weak source only; never ground truth or sole voter | CONDITIONAL |
| Fin-SoMe | Historical/social-finance benchmark candidate | Chinese social media | Medium; task/domain differ from official disclosures | Existing publisher annotations | Academic dataset lineage requires record-level audit | Non-commercial research constraints and public-release compatibility require audit | Not audited in the current environment | Unverified | Unverified | Social-media rather than official disclosure domain | Historical comparison only if provenance, licence and leakage gates later pass; not an active M6 corpus | HOLD |
| Frozen 30-item TWSE-derived M5.5 diagnostic | Historical model-rejection evidence only | zh-TW | High but extremely small | Pre-existing single-review diagnostic labels; no new review permitted | Shortened public TWSE-derived samples are versioned in repository | Public-short-text research evidence; not a reusable corpus claim | Yes | Frozen IDs/text hashes; not used for training or threshold selection | Kept outside all model and threshold selection | Narrow diagnostic coverage | Preserve failed-model results only; not training, formal evaluation or publication benchmark | ACCEPT |
| `p988744/eland-sentiment-zh` | Historical dataset-audit/rejection evidence only | Mixed Traditional/Simplified Chinese | Unestablished | Publisher labels could not be fully audited | Public viewer history only; raw record-level provenance unavailable | Publisher-level claim did not establish underlying-source rights | No; raw splits unavailable and official page later returned 404 | Unverified | Unverified | Failed: visible mixed-domain and non-financial contamination with abnormal/inconsistent markup | Preserve Eland HOLD/exclusion record only; no training, adaptation, weak supervision, evaluation, features, merging or re-audit | HOLD |

## Active-source priority

The active Taiwan research path is limited to purpose-specific audits of:

1. `tw-finance-159M` for unlabelled Taiwan financial-domain language adaptation;
2. MOPS/TWSE for official disclosure text, timestamps and structured event metadata;
3. FinMind for appropriately licensed Taiwan news/market data and timestamp alignment;
4. Taiwan FSC/regulatory text as an optional adaptation corpus;
5. audited historical stock and benchmark prices for automatic market-reaction targets.

None of these sources is human-validated sentiment ground truth. A source moves from `HOLD` or
`CONDITIONAL` only through a versioned, automated provenance/licence/access/duplicate/leakage/domain
audit; no record-level human annotation, label review or adjudication is introduced.

## Eland exclusion

Eland is not an active candidate. Its `HOLD` row is permanent historical rejection evidence for
the current plan and must not be reinterpreted as `ACCEPT`, `CONDITIONAL` or a future rescue task.

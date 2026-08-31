# Financial AI Assistant v1.0 Final Release Audit

Audit date: 2026-08-31

Release target: `v1.0.0-portfolio`

Audit state: **V1_0_RELEASE_READY_WITH_NONBLOCKING_NOTES**

This audit verifies the research, product, engineering, privacy and repository boundaries required
for the public portfolio release. Historical milestone labels do not override this document or the
root README.

## Final checklist

| area | status | evidence / note |
|---|---|---|
| A. Research integrity | PASS | Track A is stock-normalized next-session volatility surprise; retrospective, leakage-aware and hypothesis-informed |
| B. Model/result consistency | PASS | Ridge `alpha=100`; 32,357 eligible rows; 20,637 OOS rows; mean Spearman 0.1940; lift 1.3542; R² near zero |
| C. Demo consistency | PASS | Production uses ten ticker-specific controlled historical snapshots; nine full event summaries and 0050 fail closed |
| D. NLP claim consistency | PASS | Chinese sentiment abstains; BERT is representation-only; reaction magnitude remains an automated association signal |
| E. Source/licensing boundary | PASS | licensed raw rows and article bodies are excluded; public events use permitted derived metadata only |
| F. Privacy/security | PASS | no credentials, holdings, raw LINE identity, private GAS source or local absolute paths are tracked |
| G. Repository hygiene | PASS | public root is reduced to product/build entry files; workflow history is archived under `docs/internal/` |
| H. Documentation quality | PASS | README is the portfolio entry point and separates results, engineering, limitations and future validation |
| I. Reproducibility | PASS_WITH_NOTE | 384 tests passed; Ruff, import/CLI, diff and secret checks passed; existing dependency warnings are non-blocking |
| J. Deployment | PASS | production Streamlit sanity verified at the documented HTTPS URL |
| K. Forward validation infrastructure | PASS | GitHub Actions + private R2, three schedules, raw-first lineage and idempotency smoke verified; no auto retraining |
| L. Portfolio presentation | PASS | Web-first product story; LINE is experimental integration evidence rather than primary CTA |
| M. Git/release state | PASS | release-prep changes reviewed; normal main push and annotated tag are authorized after this document is committed |

No research or security blocker was identified. The only non-blocking notes are an existing
Starlette/httpx deprecation warning, an environment-only physical-core warning in one deterministic
HGB test, and the owner's still-open choice of a repository-wide source-code license.

## Validation record

- Full pytest: **384 passed**.
- Ruff: **PASS**.
- Repository secret scan: **PASS**.
- `git diff --check`: **PASS**.
- FastAPI import: **PASS**.
- Streamlit entrypoint import: **PASS** (expected bare-mode Streamlit warnings only).
- Forward-runner CLI `--help`: **PASS** for local and R2 entry points.
- Production browser sanity: **PASS**.

## Authoritative research facts

### Track A

- Task: continuous next-session volatility surprise relative to each stock's own trailing
  20-session volatility context.
- Historical source coverage: 40,691 stock rows across ten tickers and 4,080 TAIEX sessions.
- Final eligible dataset: 32,357 rows.
- Historical OOS evidence: 20,637 unique rows across seven rolling-origin outer periods.
- Final model: Ridge Regression, `alpha=100`.
- Mean outer Spearman: Persistence 0.0608, Ridge 0.1940, HGB 0.1863.
- Top-decile lift: Ridge 1.3542, HGB 1.3611.
- Interpretation: modest historical ranking signal; point-magnitude R² is near zero/slightly
  negative. No direction, return, trading or prospective-validity claim is made.

### Track B

- Corrected private 2021–2025 source evidence: 7,582 events, 3,433 aggregated windows and nine
  represented tickers.
- Metadata-only absolute-reaction OOF Spearman: 0.2504; top-decile lift: 1.623.
- Signed direction is weak/unsupported; BERT text did not add supported incremental signed value.
- FSC-adapted BERT is a financial-domain representation artifact, not a validated Chinese
  sentiment model.
- Chinese Positive/Neutral/Negative output remains unavailable because no acceptable independent
  ground truth passed the frozen gate.
- Event class, reaction magnitude, media tone and linguistic sentiment remain separate concepts.

## Product and deployment verification

Production URL: <https://mieuxwei-f6rbk4pvtvxs3rsh3k2zmn.streamlit.app/>

Bounded browser verification covered:

- Home and the primary Web Demo CTA;
- 2330 and 2308 ticker-specific score/event views;
- 0050 score with explicit missing-event fail-closed behavior;
- three-holding browser-session portfolio and delete behavior;
- financial-intelligence event content;
- Technical Notes separation of 6/9 serving readiness, 5/23 feature parity, NLP limitations,
  experimental LINE integration and forward collection;
- 390 × 844 viewport with no horizontal overflow;
- no traceback, raw exception, local path or secret in user-facing states.

Current-market model serving remains disabled. The public application performs no request-time
provider call and does not load the private final-model artifact.

## Documentation and file classification

| category | disposition |
|---|---|
| PORTFOLIO_DOC | `README.md`, portfolio guide, architecture, privacy, deployment and final audit remain public |
| RESEARCH_EVIDENCE | frozen protocols, configs and evaluation reports remain in `docs/` and `research/` |
| REPRODUCIBILITY | pipelines, model code, jobs, schemas, tests and safe result configs remain tracked |
| ACTIVE_CODE | Streamlit, FastAPI, public-beta GAS adapter and security edge remain tracked |
| INTERNAL_HISTORY | handoff, project plan, rebaseline, GAS freeze and live-product audit moved to `docs/internal/` |
| REDUNDANT | unreferenced duplicate `docs/assets/public_web_demo_home.jpg` removed |

Historical milestone names, implementation boundaries and AI-assisted workflow language are
retained only in the internal archive when needed for provenance. They were removed from the root
portfolio path and current public narrative. Git authors, dates and historical commits were not
rewritten; no manual-development history was fabricated.

## Repository and data-rights boundary

- `.env`, `.tools/`, caches, local model/data artifacts, credentials and private data are ignored.
- Private legacy GAS files, Google resource identifiers and local absolute paths are absent from
  tracked portfolio-facing documents.
- TWMD remains licensed private metadata. No raw subject, full text or bulk licensed row is
  redistributed.
- Publisher article bodies are not packaged.
- Forward TWSE/TPEx objects remain in a private R2 bucket and are not GitHub artifacts.
- No repository-wide source-code license has been granted; public visibility alone does not grant
  reuse rights. Third-party data remain governed by their respective terms.

## Non-blocking future work

- accumulate naturally future official observations for a separately approved v1.1 external
  validation after approximately 3–6 months;
- resolve exact training/serving adjusted-price and 23-feature parity before current inference;
- independently validate Chinese linguistic sentiment, if a suitable lawful ground-truth source
  becomes available;
- optional LINE/LIFF UX improvements and additional public-safe English evidence.

None of these items blocks the v1.0 research portfolio. Collection does not trigger automatic
retraining or model promotion.

# R1A Public Web Demo Release Result

Date: 2026-08-29  
Status: **PUBLIC_WEB_DEMO_READY_FOR_MANUAL_DEPLOY**

## Decision

- Provider: Streamlit Community Cloud.
- Topology: one fixture-only Streamlit application.
- Entrypoint: `demo/public_app.py`.
- FastAPI required: no.
- Runtime secret required: no.
- Request-time provider calls: none.
- Public HTTPS URL: `https://mieuxwei-f6rbk4pvtvxs3rsh3k2zmn.streamlit.app/`.
- Initial HTTPS smoke: failed at import because the nested entrypoint could not resolve `demo`.
- Corrected local/cloud-like entrypoint test: passed; correction not pushed yet.

## Boundaries preserved

- Current-market inference remains disabled and `NOT_READY_FOR_F11B_2`.
- F11B-2A remains 6/9 gates with 5/23 exact features.
- Chinese linguistic sentiment remains abstained.
- Market-reaction magnitude remains a research-only historical-association signal.
- Track A/B models, target and feature contract were not modified.
- Live GAS, LINE webhook and portfolio flows were not modified.
- No deployment, commit or push occurred.

## Validation

- Local public-entrypoint browser smoke test: PASS.
- Controlled label, score card, intelligence, research evidence and limitation views: PASS.
- Request-time API/provider path in public mode: not invoked; enforced by automated test.
- Dependency declaration dry-run: PASS.
- Full pytest after Cloud entrypoint regression coverage: 311 passed; existing
  dependency/environment warnings only.
- Ruff: PASS.
- Secret scan: PASS.
- `git diff --check`: PASS.
- Public HTTPS smoke test: FAILED on the currently deployed revision; rerun after correction push.

## Cloud entrypoint correction

The first Streamlit Cloud launch exposed a nested-entrypoint import-path difference:
`demo/public_app.py` could not resolve the top-level `demo` package. The local release now derives
the repository root from `__file__`, adds only that fixed path to Python module resolution and then
imports `demo.app`. A regression test executes the nested entrypoint from outside the repository
and rejects any `ModuleNotFoundError`. The correction still requires a user-controlled commit/push
before Streamlit Cloud can redeploy it.

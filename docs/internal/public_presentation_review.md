# Public presentation review — 2026-09-04

## Scope and state

Local public-documentation and Streamlit presentation changes only. **Not deployed.**
No commit, push, tag, Release edit, research rerun, provider addition, or private-system change.
HEAD remains `207a5516f151827bb3220b95909f799cb039b40b`.

No applicable AGENTS.md was found in the repository/ancestor and edited-subdirectory checks.
The pre-existing deletion of `docs/private_forward_event_collection_runner.md` and new
`docs/private_forward_event_collection_runne.md` are preserved. Their contents compared identical;
no collector document was restored, overwritten or renamed by this task. The existing untracked
Chinese overview was integrated, not replaced by a second overview.

## Changes

- English-primary README with concise Chinese positioning, result, status and limitation summaries;
  reciprocal link to the existing full Chinese overview.
- Five explicit states: frozen v1.0 research, controlled historical demo, experimental LINE/GAS,
  disabled current-market inference, and future-validation collection.
- Home prioritizes stock analysis and GitHub. Details are secondary; no audience-specific copy.
- Stock score, historical percentile (not probability), communication band and feature date are
  distinguished. Related-page buttons retain ticker context, including 0050's missing event.
- Session-only holdings remain capped at five; sample-first copy and per-holding analysis shortcuts.
- Research summaries include sample sizes, protocols, frozen evidence links, Ridge/HGB practical tie,
  R² limitation, non-comparability of the two tracks and unsupported BERT direction gain.
- Architecture asset separates public Web, research/API, experimental LINE and private forward
  collection. It does not imply that the public Web runtime calls all components.
- README no longer uses the older synthetic-demo screenshot. That historical asset is preserved;
  the replacement is an actual **local** historical-evidence screenshot, explicitly labelled as
  not yet deployed.

## Frozen evidence verification

Checked against F7 and B4 reports, existing public fixture and release configuration:

| Study | Scope | Metrics and interpretation |
|---|---|---|
| A | 10 instruments, 20,637 OOS rows, 7 outer periods | Ridge alpha 100; mean outer Spearman 0.1940, MAE 0.5473, lift 1.3542. Practical-tie margin 0.01; lower mean MAE tie-break, not universal superiority. |
| B | 7,582 events, 3,433 windows, 9 tickers | Metadata magnitude OOF Spearman 0.2504, lift 1.623; historical association, not direction or causality. |

Current-market parity remains 5/23; gates remain 6/9. Chinese sentiment remains abstained.
The two tracks have different questions and protocols and are not head-to-head comparable.
No fixture or frozen evaluation artifact was edited. `git diff --quiet` returned 0 for research,
pipelines, backend, jobs, configs, .github and demo/fixtures.

## Validation performed

The repository .venv and some source files were macOS dataless/cloud placeholders, causing slow
imports. A temporary Python 3.12 environment under `/tmp` was used with the existing demo pins
(Streamlit 1.62.0, Pydantic 2.13.4) and existing test dependencies. No dependency manifest changed.

Relevant pytest selection: **27 passed**, with the normal repository conftest loaded. This is not
a full regression suite and is not the historical “384 tests passed” record.

```bash
python -m pytest -o addopts='' -q \
  tests/unit/test_public_web_demo_release.py \
  tests/unit/test_web_demo_portfolio.py \
  tests/unit/test_f12_portfolio_finalization.py \
  tests/integration/test_streamlit_dashboard.py \
  tests/integration/test_public_presentation.py
```

- Covers historical fixture coverage, full/partial states, 2308/0050 cross-page preservation,
  holdings create/update/delete/clear, five-ticker cap, independent sessions and page rendering
  with requests/httpx outbound calls rejected.
- Ruff on changed Python files: PASS.
- Targeted credential-pattern scan on changed/new textual files: PASS; screenshots visually checked.
- `git -c diff.renames=false diff --check`: PASS. Rename detection was disabled only for this read-only
  check to avoid slow unrelated file hydration; no Git configuration was saved.
- README and Chinese-overview relative links resolve. Five direct research evidence paths exist
  in the `v1.0.0-portfolio` Git tree. This is not a crawl of every outbound link in historical docs.
- Existing Starlette/httpx and anyio deprecation warnings remain; they were not changed here.

Actual local browser checks used `http://127.0.0.1:8504`: home, 2330 and 2308 stock snapshots,
2308 intelligence, 0050 stock-to-intelligence missing-event behavior, session sample load/add/update,
research and architecture. Delete/clear/five-cap are additionally verified through Streamlit AppTest.
At 390×844, navigation, stock, intelligence and holdings were operable; home/document width was
390 with no horizontal overflow. This is a browser viewport check, not a physical-device test.

## Real screenshots — local preview only

No image generation, synthetic dashboard composition or research-chart alteration was used.
These are viewport captures, not full-page exports; below-the-fold content may not appear.

- [Home, desktop](../assets/presentation/home-desktop.png)
- [Home, 390px](../assets/presentation/home-mobile.png)
- [Stock, desktop](../assets/presentation/stock-desktop.png)
- [0050, desktop](../assets/presentation/0050-desktop.png)
- [Session holdings](../assets/presentation/portfolio-desktop.png)
- [Financial intelligence](../assets/presentation/intelligence-desktop.png)
- [Research](../assets/presentation/research-desktop.png)
- [Architecture](../assets/presentation/architecture-desktop.png)

## Remote read-only findings and authorization queue

Checked GitHub repository metadata, Release API, tag ref and the Streamlit Manage app panel.

| Item | Observed | Proposed / pending |
|---|---|---|
| GitHub About | Financial news sentiment, stock trend research, and a LINE-based portfolio intelligence assistant. | Replace with neutral ML / stock-normalized volatility-surprise / financial NLP research wording; requires authorization. |
| Homepage | https://financial-ai-assistant-one.vercel.app | Set to the existing Streamlit demo; requires authorization. |
| Topics | Empty | Suggested: machine-learning, financial-nlp, time-series, streamlit, fastapi, research; requires authorization. |
| Release | v1.0.0-portfolio; published 2026-08-31; neither draft nor prerelease; empty body/assets | Preserve version and tag. Any descriptive Release edit requires separate authorization. |
| Tag | Points to HEAD above | No retag or rename. |
| Streamlit | main / demo/public_app.py; public app loaded the prior layout, not a sleep page during this check | This revision remains local. Conditional wake instructions retained; no keep-alive. |

Public URL: https://mieuxwei-f6rbk4pvtvxs3rsh3k2zmn.streamlit.app/

The current branch/entrypoint were visible in Manage app. Streamlit documents automatic updates
from the connected repository in [Manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app).
Therefore a later authorized push to main can update production; it must be treated as a deployment
step, followed by a new production smoke test. No reboot or deployment action was taken.

## Remaining verification boundaries

- Revised production behavior is **not verified** because this work is not deployed.
- No physical phone, broad cross-browser matrix, full test suite or new external validation was run.
- Forward-collection operational counts in the Chinese overview remain dated historical observations;
  live storage/scheduler health was not re-audited here.
- Existing LINE, GAS, LIFF, backend access control, R2 collector, data rights and repository-wide
  license policy were not modified. No historical Financial assets were deleted.

## Authorized publication follow-up

After the user's approval, the pre-commit check found four blank full-page captures and Markdown
trailing spaces. The captures were replaced with visually inspected viewport screenshots; the
0050 replacement is desktop-sized and named accordingly. Original historical assets remain intact.
The remote metadata edit was blocked by the environment authorization reviewer; About/homepage/topics
were not changed. This does not alter the completed local presentation verification above.

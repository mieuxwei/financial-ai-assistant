# Live Demo Product Audit Archive

> Internal before/after product-review evidence retained for design provenance. It is not a
> primary portfolio document.

Audit date: 2026-08-31  
Audited deployment: `https://mieuxwei-f6rbk4pvtvxs3rsh3k2zmn.streamlit.app/`

## Phase 1 — Blind live product audit

This phase evaluated only what a first-time visitor can see and operate in the deployed site. Prior
milestone status, repository documentation and implementation effort were not used as evidence.

### A. Executive verdict — BEFORE

**MAJOR_UX_REVISION_REQUIRED**

The deployment is visually clean and research-safe, but it currently behaves like one static
research record with four detail tabs, not a portfolio-ready product experience. A professor can
find authentic ML evidence, but only after interpreting unexplained English terminology. A general
visitor has no obvious first action, no ticker choice, no portfolio workflow and no architecture
view. Mobile rendering works only after manually collapsing a sidebar that initially occupies most
of the viewport.

### B. First 30-second test — BEFORE

| Question | Verdict | Blind-review observation |
|---|---|---|
| 這是什麼？ | WEAK | Title and “研究作品集” are visible, but the product purpose is not stated in one plain sentence. |
| 解決什麼問題？ | FAIL | “Relative Volatility Surprise” appears before a human explanation of the problem. |
| 最核心 AI 功能？ | WEAK | Three scores are prominent, but their relationship and practical meaning require scrolling/reading. |
| 可以操作什麼？ | FAIL | No guided action or selector is visible; the screen looks like a fixed 2330 report. |
| 第一個應按哪裡？ | FAIL | There is no primary CTA; tab labels appear below the score block. |
| 不是投資建議？ | PASS | The limitation is immediately visible and repeated. |
| 是研究作品而非交易產品？ | PASS | “Controlled Research Demo” and “研究作品集” are clear. |

### C. What works

1. The controlled-data boundary is unmistakable and does not masquerade as live inference.
2. The score, percentile and communication band are visually prominent and internally consistent.
3. The site explicitly avoids price-direction, return and investment-advice claims.
4. Research evidence includes the selected Ridge model, seven chronological periods, mean
   Spearman and top-decile lift rather than presenting an unsupported success claim.
5. Track B correctly separates event class, reaction magnitude and unvalidated Chinese sentiment.

### D. What is confusing

- “Next-session Relative Volatility Surprise” is the first major metric but is not translated next
  to the label.
- `0.80×`, `87.5%` and `HIGH` look related, but the page does not explain the relationship in one
  compact reading guide.
- The first screen simultaneously says “受控示範”, “受控合成離線資料”, “受控合成展示” and
  “不是即時資料”, creating warning fatigue before product value is established.
- The navigation is presented as small tabs after the score block; it does not read as a product
  information architecture.
- The fixed 2330 example gives no indication whether other stocks or scenarios can be explored.
- Research terms such as OOF, Spearman, F11, F9 and abstain are not translated for general visitors.
- “市場反應強度” can sound directional or causal until the visitor reads the explanatory sentence.

### E. Missing

| Missing element | Does it improve evaluation? | Priority |
|---|---|---|
| Plain-language one-sentence value proposition | Yes; answers what/why immediately | P0 |
| Primary CTA and guided first interaction | Yes; turns a static report into a usable demo | P0 |
| Ticker/scenario selector with company names | Yes; demonstrates a product contract beyond one hard-coded row | P0 |
| Web portfolio health workflow | Yes; proves the project’s portfolio-assistant positioning | P0 |
| Research-results visualization | Yes; professor can compare evidence without reading prose | P1 |
| Architecture view | Yes; proves this is more than an API wrapper | P0 |
| Compact “how to read this” beside the metric | Yes; prevents probability/direction misreading | P0 |
| Useful empty, validation and reset states | Yes; necessary for a demo portfolio interaction | P1 |
| Mobile-first navigation or default-collapsed sidebar | Yes; current first mobile impression is obstructed | P0 |
| Evidence links/details grouping | Yes; preserves rigor without dominating the product view | P1 |

### F. Unnecessary or excessive

- Sidebar repeats the controlled-demo status already shown in the page header.
- The same non-live/non-advice disclaimer appears in the header, blue callout, interpretation text
  and footer.
- Model lineage exposes a full artifact SHA, target identifier, fixture identifier and pipeline
  identifier directly to ordinary visitors.
- `F11`, `F9`, `F11B-2A`, gate counts and exact parity counts are internal project language, not
  user-facing explanations.
- The English “FINANCIAL INTELLIGENCE RESEARCH” eyebrow adds little beside the title and Chinese
  context.
- Static market-context metrics are displayed without explaining why the visitor should use them.

### G. Information hierarchy classification

| Information | Decision | Final location |
|---|---|---|
| Project title | KEEP | Home |
| Long Chinese research title | SIMPLIFY | Home subtitle; full title in Research |
| Controlled Research Demo | KEEP, reduce repetition | One global status badge + details |
| Non-advice/no-direction disclaimer | KEEP, consolidate | Global short line + Limitations |
| Model name / alpha | MOVE_TO_DETAILS | Research |
| Spearman / top-decile lift / R² | KEEP with plain explanation | Research summary/details |
| Seven folds | KEEP | Research |
| Feature parity / gate count | MOVE_TO_DETAILS and translate | Limitations |
| Model SHA / config version / schema version | MOVE_TO_DETAILS | Collapsed technical lineage |
| F7/F8/B4/F11B/F9 names | REMOVE from normal UI | Optional technical appendix only |
| Dataset sizes / fold boundaries | MOVE_TO_DETAILS | Methodology |
| Chinese sentiment status | SIMPLIFY | Intelligence + Limitations |
| Architecture | MISSING | Dedicated Architecture page |
| Provider/source information | SIMPLIFY | Intelligence; full lineage in details |
| Current-market limitation | KEEP in human language | Global status + Limitations |
| Forward collection implementation | MISSING from engineering evidence | Architecture/Methodology only |

### H. User-flow audit — BEFORE

| Flow | Verdict | Observation |
|---|---|---|
| Home → 股票分析 | CONFUSING | Home and stock analysis are effectively the same screen; no entry action. |
| 選股票 | BROKEN | No selector or alternate controlled scenario exists. |
| 看懂 score | CONFUSING | Explanation exists below, but terminology precedes meaning. |
| 看金融情報 | CLEAR | Tab works and task separation is reasonably explicit. |
| 建立/查看 Demo portfolio | BROKEN | No Web portfolio surface exists. |
| 持股健檢 | BROKEN | Not available in the deployed interface. |
| 看 Research | CLEAR | Evidence is concise but lacks visualization and R² context. |
| 看 Architecture | BROKEN | No architecture page is exposed. |
| 看 Limitations | CLEAR | Complete, but dominated by internal IDs/status codes. |

### I. Mobile issues

- At a 390 × 844 viewport, the Streamlit sidebar opens over roughly three quarters of the screen;
  the visitor must discover and press a collapse icon before seeing the product.
- Metric cards stack correctly after sidebar collapse, but the primary navigation is below multiple
  cards and outside the first viewport.
- The long title wraps cleanly, but the first useful interaction is pushed well below the fold.
- Technical labels remain English and long on small cards.
- The page is vertically long because the same global hero/metrics repeat above every tab.

### J. Claim issues

No direct false trading, direction, live-market or validated-Chinese-sentiment claim was observed.
However, the following language needs refinement:

- “Risk” without an immediate volatility qualifier can be read as loss probability.
- “Prediction” should always be scoped to retrospective controlled volatility-surprise research.
- “Market reaction” must keep “magnitude / historical association” adjacent to the label.
- “English sentiment can be scored” is capability language, not evidence that this record was scored.
- Internal maturity/status codes should not be surfaced as product copy.

### K. Top 10 prioritized improvements

1. **P0** — Create a true landing section with plain-language problem/value and one primary CTA.
2. **P0** — Add a controlled ticker/scenario selector and company names; never imply live data.
3. **P0** — Add a usable 0–5 holding browser-session portfolio and portfolio health workflow.
4. **P0** — Replace the four embedded tabs with a clear six-part product navigation structure.
5. **P0** — Translate score, percentile and band into one compact “how to read” explanation.
6. **P0** — Add an Architecture surface that demonstrates Web/FastAPI/data/ML/NLP and the
   experimental LINE/GAS path without exposing private identifiers.
7. **P0** — Fix the obstructive mobile sidebar/default navigation experience.
8. **P1** — Consolidate repeated disclaimers into one status language plus one limitations page.
9. **P1** — Move hashes, IDs, milestone names and gate counts into collapsed technical details.
10. **P1** — Add compact model/research comparison visuals and plain-language conclusions,
    including the R² limitation and unsupported BERT text increment.

## Phase 2 — Repository evidence gap audit

Phase 2 was performed only after the deployed-interface verdict above was frozen. Repository
claims were checked against source, tests and evaluation artifacts; they were not used to revise
the BEFORE verdict.

### Implemented but not visible in the deployed UI

| Capability/evidence | Classification | Recommended treatment |
|---|---|---|
| Web-first landing, three CTAs and seven-section navigation already present on `main` | SHOULD_SURFACE | Deploy as the primary visitor path after revision and smoke testing |
| Browser-session portfolio supporting up to five frozen-universe holdings | SHOULD_SURFACE | Make the workflow self-explanatory; show edit/delete/reset and honest unavailable states |
| Dedicated architecture view | SHOULD_SURFACE | Present Web, research services and experimental LINE path at portfolio level |
| Ridge vs Persistence vs HGB comparison | SHOULD_SURFACE | Use one compact comparison visual; explain why Ridge won a practical tie |
| Pooled decile/ranking evidence | SHOULD_SURFACE | One visual plus plain-language ranking interpretation |
| Point-forecast R² near zero | SHOULD_SURFACE | Keep beside the positive ranking evidence so claims remain balanced |
| FastAPI versioned research contracts | DETAILS_ONLY | Architecture/methodology evidence, not a homepage feature |
| Cloudflare raw-body LINE signature verification, HMAC identity, idempotency and Neon isolation | DETAILS_ONLY | Summarize under Experimental LINE Integration |
| TWSE/TPEx raw-first forward collector, R2 immutability and scheduled reconciliation | DETAILS_ONLY | Show as future-validation engineering, never as a user feature or live model feed |
| Full feature lineage, hashes, run manifests and exact fold tables | DETAILS_ONLY | Collapsed reproducibility details or repository evidence links |
| Private licensed-source audits and private artifacts | KEEP_HIDDEN | Do not expose rows, paths, credentials or payloads |

The largest evidence gap is therefore deployment/version visibility, not absence of engineering:
the checked-in application already contains several P0 surfaces that the public URL does not show.

### Visible but low value in the deployed UI

- Full model/artifact SHA and fixture/version identifiers in an ordinary-user tab.
- Internal milestone labels (`F9`, `F11B-2A`) and gate fractions without a user decision attached.
- Repeated controlled-data and non-advice warnings occupying several independent surfaces.
- Provider-style source identifiers and all-caps research contract labels.
- Static context numbers without a clear explanation of how they help interpret the result.

### Evidence missing from the demo

- A before/after research story: binary risk formulation → regime/threshold sensitivity →
  continuous stock-relative volatility-surprise forecasting.
- Direct model comparison and decile visuals already stored as public-safe SVG assets.
- A concise explanation that Ridge was selected from a practical tie using the frozen MAE
  tie-break, rather than because it dominated every metric.
- The balanced result that ranking evidence is positive while point-forecast R² is approximately
  `-0.009`.
- System evidence showing FastAPI contracts, the experimental LINE security path and the private
  forward-data/future-validation path without suggesting that the fixture-only Web request uses
  those systems at runtime.

### Evidence overexposed

- Reproducibility identifiers and internal status/milestone codes are presented before visitors
  understand the product.
- The current-market block is expressed as implementation gate arithmetic rather than a plain
  product limitation.
- Abstention and maturity concepts are technically correct but sometimes use research vocabulary
  where human wording is sufficient.

### Product-story assessment

The deployed version starts at **Result** and then exposes selected **Evidence** and
**Limitations**. It largely omits **Problem**, **Guided interaction** and **Engineering**, so the
visitor experiences “one record plus research notes” instead of a coherent product story.

The repository version is materially closer to a complete story, but still needs terminology
simplification, better research visuals, explicit fail-closed ticker behavior and less technical
noise in the normal path.

### Recommended final information architecture

1. **首頁** — problem, one-sentence value, controlled-demo state, primary CTA, three capabilities
   and a small evidence strip.
2. **股票分析** — frozen-universe selector, company name, score/percentile/band, one reading guide,
   event intelligence and an explicit unavailable state for unsupported controlled scenarios.
3. **持股健檢** — session-only 0–5 holdings, sample/reset controls, add/update/delete, whole-portfolio
   summary and per-holding supported/unavailable research state.
4. **金融情報** — event category, reaction magnitude and linguistic-sentiment limitation in three
   clearly separate concepts.
5. **研究成果** — research evolution, model comparison, ranking result, Track B evidence and
   balanced limitations.
6. **系統架構** — public runtime path, research/backend capabilities, experimental LINE/GAS path
   and private forward-collection/future-validation path.
7. **方法與限制** — retrospective design, no current inference/direction/validated Chinese
   sentiment, plus collapsed serving-readiness and reproducibility details.

## Phase 3 — Revision plan and implementation record

The revision follows **REMOVE → SIMPLIFY → REORGANIZE → ADD**:

1. Remove repeated warnings and ordinary-view internal IDs.
2. Simplify mixed English/internal labels into Traditional Chinese with the research term retained
   only where it helps an evaluator.
3. Reorganize around a seven-section guided path and keep technical proof in details.
4. Add only missing high-value interactions/evidence: fail-closed ticker selection, portfolio
   sample/reset/edit clarity, comparison/ranking visuals and forward-validation architecture.

Implementation and post-revision results are recorded after the revised UI is exercised locally.

### Implemented P0 and P1 revisions

- Replaced the public sidebar dependency with a single main-content page selector that remains
  usable at a 390 px viewport.
- Rewrote the landing hero around problem, capability, research boundary and three explicit CTAs.
- Replaced first-screen model/version jargon with three understandable evidence cards.
- Added frozen-universe stock selection. Only 2330 has a public-safe controlled fixture; all other
  selections fail closed with a clear unavailable state instead of borrowing or inventing output.
- Reworded score, percentile and band in Traditional Chinese and placed the non-probability,
  non-direction explanation beside the result.
- Expanded the browser-session portfolio into a demonstrable workflow: load sample, add/update,
  delete, reset, maximum-five enforcement, whole-portfolio summary and supported/unavailable state.
- Separated event class, historical reaction magnitude and linguistic sentiment in user language;
  provider-style/internal labels are no longer the primary card copy.
- Added the pre-existing model-comparison and ranking-decile visuals to the research page, together
  with the `R² ≈ -0.009` limitation and frozen Ridge tie-break explanation.
- Reframed architecture into public Web runtime, research/application layer, experimental LINE/GAS
  evidence and private forward-data/future-validation paths.
- Moved serving gate counts and full reproducibility identifiers into collapsed details; the normal
  limitation view now states the user decision in plain language.
- Added a sanitized public load-error state that never falls back to an unverified source or exposes
  internal exception details.

### Deliberately not implemented

- No alternate-ticker score was synthesized merely to make the selector look richer.
- No current price, ROI, live news, provider call, current-market feature or prediction was added.
- No animation, decorative gauge or additional dashboard card was added without decision value.
- No deep-link/query-parameter navigation was added; the single-session portfolio demo does not
  require shareable state.
- No LINE UX work was performed; LINE remains architecture evidence rather than the primary CTA.

## Post-revision verification

### First 30-second test — AFTER (local revised build)

| Question | BEFORE | AFTER | Evidence in revised build |
|---|---|---|---|
| 這是什麼？ | WEAK | PASS | Product title plus one-sentence Taiwan-equity AI assistant description |
| 解決什麼問題？ | FAIL | PASS | “預測股票相對波動異常程度，整合金融事件情報” is above the fold |
| 最核心 AI 功能？ | WEAK | PASS | Plain-language volatility ranking and NLP capability card |
| 可以操作什麼？ | FAIL | PASS | Stock analysis, portfolio health and intelligence are named in the first card |
| 第一個應按哪裡？ | FAIL | PASS | Primary “開始股票分析” CTA; two secondary CTAs |
| 不是投資建議？ | PASS | PASS | Short first-screen boundary and consolidated footer |
| 是研究作品而非交易產品？ | PASS | PASS | One controlled-research badge plus explicit non-live scope |

### Functional smoke — local revised build

| Surface/interaction | Result |
|---|---|
| Landing and main-content navigation | PASS |
| 2330 controlled stock analysis | PASS |
| 0050 unsupported selection fails closed | PASS |
| Score/percentile/band explanation | PASS |
| Financial intelligence concept separation | PASS |
| Portfolio empty state | PASS |
| Load two-holding example | PASS |
| Update 0050 shares | PASS |
| Delete a holding | PASS |
| Research results and two visuals | PASS |
| Architecture and forward-validation positioning | PASS |
| Human-readable limitations and collapsed technical details | PASS |
| 390 × 844 first view and navigation | PASS |

### AFTER verdict

**PORTFOLIO_READY for deployment.**

No P0 product issue remains in the revised local build. The only release mismatch is that the
authoritative public URL still serves the BEFORE version until these reviewed changes are committed
and pushed through the existing Streamlit deployment. Therefore the task success state is
`LIVE_WEB_DEMO_REVISION_READY_FOR_DEPLOYMENT`, not a claim that production has already updated.

Remaining P2 polish intentionally deferred:

- refresh repository screenshots after production deployment, so captured assets match the final
  deployed revision rather than a local-only state;
- optional shareable deep links for individual pages;
- optional additional public-safe controlled fixtures, but only if derived without fabricating
  ticker-specific evidence.

## Production deployment verification

Verification date: 2026-08-31

Production URL: <https://mieuxwei-f6rbk4pvtvxs3rsh3k2zmn.streamlit.app/>

Deployed revision: `313b4c7cd07e9347086cae3793a087182020fe2e`

The revision was confirmed on the GitHub `main` branch and detected by Streamlit Community Cloud.
The existing process initially continued serving the previous interface, so the app was explicitly
rebooted through the Streamlit management panel after user approval. A fresh browser session then
loaded the revised Web-first interface.

### First 30-second test — PRODUCTION AFTER

| Question | Result | Production evidence |
|---|---|---|
| 這是什麼？ | PASS | Product name and Taiwan-equity research-assistant description are above the fold |
| 解決什麼問題？ | PASS | Relative volatility-surprise forecasting and financial-event intelligence are stated directly |
| 最核心 AI 功能？ | PASS | Plain-language volatility ranking is identified as the research core |
| 可以操作什麼？ | PASS | Stock analysis, Demo portfolio health and financial intelligence are named immediately |
| 第一個應按哪裡？ | PASS | “開始股票分析” is the primary CTA |
| 不是投資建議？ | PASS | The first screen states non-live, no-direction and non-investment-advice boundaries |
| 是研究作品而非交易產品？ | PASS | Controlled Research Demo status is visible without opening details |

### Functional smoke — production

| Surface/interaction | Result |
|---|---|
| Landing, main-content navigation and all three CTAs | PASS |
| 2330 controlled stock analysis | PASS |
| 0050 unsupported selection fails closed without borrowed or fabricated output | PASS |
| Score, percentile and communication-band explanation | PASS |
| Portfolio empty state | PASS |
| Load two-holding example | PASS |
| Add a holding through the form | PASS |
| Update holding shares and average cost | PASS |
| Delete and clear holdings | PASS |
| Financial intelligence concept separation | PASS |
| Research metrics, model comparison and ranking visual | PASS |
| Architecture, experimental LINE path and forward-validation path | PASS |
| Current-market blocker and Chinese sentiment limitation | PASS |
| Sanitized UI with no browser console error/warning | PASS |

### Responsive and operational checks

- Desktop viewport (`1440 × 900`): PASS.
- Narrow/mobile viewport (`390 × 844`): all seven pages remained usable with no horizontal
  overflow, hidden sidebar dependency or traceback.
- A bounded reboot/cold-start check returned the revised app in approximately 20 seconds,
  including dependency preparation and a fresh browser connection.
- Public request handling remained fixture-only. No Yahoo, FinMind, TWMD, Gemini, Perplexity,
  OpenAI, GDELT, LINE or Google Sheets provider request was introduced.
- Current-market F7 inference remains disabled; the documented readiness evidence remains `6/9`
  serving gates and `5/23` exact features.
- Chinese linguistic sentiment remains explicitly unvalidated and no P/N/N probability is shown.
- Market-reaction magnitude remains a historical association signal, not direction or causality.

### Production screenshots

The public-safe assets under `docs/assets/public_web_demo_*.png` were refreshed from the verified
production deployment for the landing page, stock analysis, portfolio health, financial
intelligence, research results, architecture and mobile landing view.

### Production verdict

**PORTFOLIO_READY — production deployment verified.**

No P0 issue was found in the deployed revision. The production interface and the reviewed source
now match. This verification does not start Final Release Audit, create a release tag, freeze the
project, enable current-market inference or alter Track A/Track B research artifacts.

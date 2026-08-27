# F10 FastAPI / Backend Integration Result

Status: **COMPLETE — local research API integrated; not deployed**

F10 connects the frozen F7 continuous model and F8 Financial NLP Intelligence contract to
versioned FastAPI endpoints. It skipped optional F9 and did not alter its status: no NLP
incremental-value result is claimed.

## Endpoints

### `POST /api/v1/research/volatility-surprise/predict`

The caller supplies ticker, `as_of_date`, a timezone-aware information cutoff and exactly the 23
finite `risk-features-v1` values. The endpoint lazily loads the safe JSON F7 artifact, verifies its
canonical SHA-256, normalizes the ticker and returns:

- continuous predicted volatility-surprise score;
- historical OOF percentile;
- LOW/MODERATE/HIGH/VERY_HIGH communication band;
- model, target, feature-pipeline and artifact lineage;
- explicit research/non-direction/non-investment claim boundaries.

F10 intentionally does not compute fresh market features inside the endpoint. This prevents an
unverified current-data builder from being silently treated as the frozen F7 pipeline. Missing or
invalid local artifact state fails closed with HTTP 503; malformed input returns the existing
structured validation/error format.

### `GET /api/v1/research/intelligence/{ticker}`

The endpoint reads only already-ingested `news_articles`, `article_tickers` and an optional stored
result from the exact pinned FinBERT revision. It supports bounded `limit` and timezone-aware
`as_of_cutoff` parameters and returns the F8 intelligence contract:

- English stored FinBERT result, or `ELIGIBLE_NOT_SCORED` when absent;
- Chinese/Taiwan polarity `ABSTAIN` with null probabilities;
- official metadata and separate deterministic event/impact proxy;
- source excerpt, ticker match and lineage;
- no source URL, full article content, generated summary or private portfolio data.

The request performs no provider fetch, model inference, LLM call or external API request.

## Audit evidence

- F10 config SHA-256:
  `b4367815b484352375b6693d91b44298b8e4dc3b84bf0a3c69f956f97175a4f2`
- F10 aggregate analysis SHA-256:
  `dc26d6f13e07c27e8ec32b6da8d06ac6fb1fed9b5fff32040a9d69221394b5fb`
- F7 artifact SHA-256 verified:
  `279472ab0794d093cbff0ab5a171b43be16abc3a7abed56d938938235505d4de`
- F8 config SHA-256 verified:
  `de7c372fc4ba136f10cc2bf78056898d8ea97cf6ff0fbb4a2aa7857be9e1bbc4`
- Required API routes registered: **2/2**.
- Controlled prediction contract smoke: **passed**; not a performance evaluation.
- Controlled input/prediction persisted: **no**.
- External API, training, deployment, GAS modification and M7 rerun: **all no**.

## Security and claim boundary

These are public-research endpoints and expose no private holdings. Existing private portfolio
routes retain their separate user-ownership boundary. F10 does not add production authentication,
rate limiting, live market feature computation, job orchestration or deployment; those remain
limitations rather than hidden capabilities.

The predicted value is a relative volatility-surprise research score, not price direction,
investment advice, guaranteed future volatility or prospective accuracy. F11 may build a controlled
LINE/dashboard demo on these APIs only after review; working GAS remains unchanged.

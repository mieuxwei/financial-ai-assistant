# F11A Controlled Streamlit Dashboard Result

R0 classification note: this immutable result is F11A. Its original post-F11 next-unit guidance is
superseded by the R0 roadmap; the current next executable unit is B1, while F11B remains pending.

Status: **COMPLETE — local controlled demo, not deployed**

## Scope

F11A connects the already-frozen F7/F8/F10 product contracts to a Streamlit portfolio interface.
It does not train, retune or reevaluate a model and does not change the working GAS adapter.

## Modes

1. `CONTROLLED_OFFLINE` is the default. It reads a deterministic synthetic fixture and performs no
   network request.
2. `LOCAL_API` calls the F10 prediction and intelligence endpoints. The client accepts only plain
   HTTP loopback origins with explicit ports and rejects credentials, paths, queries and fragments.

The controlled score is a real F7 artifact inference over a synthetic 23-feature vector. It is not
a real 2330 observation, live signal, prospective test or performance result. The intelligence
examples preserve Chinese sentiment abstention and English eligible-but-not-scored status.

## Reproducibility

- Config: `research/configs/dashboard_demo.v1.json`
- Fixture: `demo/fixtures/controlled_dashboard_demo.v1.json`
- Canonical config SHA-256:
  `0f70c88b6ea3b6e21177ae2fce6a4bef17d1b02a89a0dd7d491d425663ebc267`
- Canonical fixture SHA-256:
  `c55f546ebe9ee94f616d518c205c18acb6b35683436dce1a312e7849c2935c06`
- Streamlit constraint: `>=1.62,<2.0`

## Safety and claim boundary

- no private holdings, LINE credentials, API keys or personal data;
- no external provider, FinBERT or LLM call in the controlled mode;
- no fabricated Chinese polarity probabilities;
- event proxy remains separate from sentiment ground truth;
- score communicates relative volatility surprise, not price direction;
- no investment advice, guaranteed future volatility or prospective-accuracy claim;
- no GAS modification, deployment, automatic commit or push.

F9 was not run and no NLP incremental-value claim is made. Under the later R0 rebaseline, F12 is
last and the next executable unit is B1 Source Candidate Audit.

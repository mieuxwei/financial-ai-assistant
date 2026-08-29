# B3 Domain Adaptation & Candidate Signals Result

Run date: 2026-08-29  
Decision: **PASS — B3 complete; B4 candidate manifest frozen**  
Next unit: **B4 Validation / Abstention Decision — not started**

## Artifacts and hashes

- Protocol/candidate manifest:
  `research/configs/b3_domain_and_candidate_signals.v1.json`  
  SHA-256: `24916be1d82b2f7d996d0925ad355fabb2a20103cd18475230d2d8d8fbadeb68`
- Evidence validator: `research/planning/b3_protocol.py`  
  SHA-256: `5f924e65501ac1edec5f1f4034f85b80696825efdc54902dfc08b3007e5c0939`
- Ignored aggregate B3 artifact SHA-256:
  `a8a4eb5c7295317e3ed7205528d8199ffbc59fea3d921d716efd2adac9ff6151`
- Ignored bounded GDELT recovery artifact SHA-256:
  `c9df6750a5abdac368ac2ef4f3f905593900083a6ea02b8d19d6d94bd71f76e7`
- Promoted ignored BERT adapted-weight SHA-256:
  `eaacc66a4993a448e9e9dd7d6aab0fc33290d1f4e4e4e8d209efc1d7a17fd3b9`

## B3A outcome

The existing bounded 200-step FSC MLM pilot was adopted after an integrity audit; no redundant
training was run. Both pinned candidates passed the 1% domain-loss-improvement gate. Under the
predeclared lowest-final-loss rule, BERT-base-Chinese (0.947099) remains the single promoted
representation candidate over MacBERT (1.162618). The sealed FSC test file was not read.

This is a project-owned domain-adapted encoder artifact for representation/embedding research. It
is not a Chinese sentiment classifier.

## B3B outcome

- No independently permissible sentiment-label source exists.
- No new sentiment classifier was trained.
- No pseudo-label or weak-label set was generated or used for training/evaluation.
- No manual annotation, correction, review or adjudication was used.
- No circular validation occurred.
- Historical sentiment baselines were preserved without rerunning a model search.
- Chinese sentiment remains `ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED`.

The B4 manifest separately records `DOMAIN_ENCODER`, `EMBEDDING`, `LINGUISTIC_SENTIMENT`,
`EVENT_CLASS`, `IMPACT_SIGNAL`, `MARKET_REACTION` and `MEDIA_TONE` candidates.

## Source outcomes

TWMD was used only as a B2.1 contract/candidate definition. Zero TWMD rows and no licensed raw
payload entered B3. `event_class` was not mapped to P/N/N, and the timezone remains a source
contract assumption.

The one bounded GDELT official RSS recovery kept TLS verification enabled and saved no raw data.
The path returned bytes that failed XML parsing, so GDELT remains accepted in principle but
temporarily unavailable/conditional for implementation. Tone remains a media-tone proxy only.

## Completion boundary

B3 satisfies its definition of done without claiming validated sentiment. It changed no Track A
target/fold/model, GAS/LINE behavior, Track C deployment or product portfolio state. B4 is the next
and only executable unit and requires a separate instruction.

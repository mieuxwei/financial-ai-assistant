# B3 Domain Adaptation & Candidate Signals Protocol

Status: **COMPLETE / candidate manifest frozen / B4 not started**  
Protocol: `b3-domain-and-candidate-signals-v1`  
Date: 2026-08-29

## Separate research questions

B3A asks whether an open Chinese encoder can be adapted reproducibly to Taiwan financial language.
B3B identifies sentiment, event, impact, reaction, media-tone and embedding candidates without
inventing semantic ground truth. These tasks retain separate outputs and maturity claims.

## B3A — domain adaptation

B3 reuses the already approved and completed 200-step project-owned MLM pilot instead of spending
compute to repeat it. The evidence audit recomputed the FSC train/validation and promoted-weight
hashes; it did not read the sealed test JSONL and did not train another checkpoint.

Corpus contract:

- 6,021 filtered FSC financial/regulatory documents;
- train: 5,117 records, with 512 deterministic examples used by the pilot;
- validation: 482 records, with 64 deterministic examples used by the pilot;
- sealed test: 422 records, not read by B3;
- corpus SHA-256:
  `389640a2f3232cb95bc8c47032673ba8f90a8d5eb23affc1f01a03971d20366c`;
- no sentiment labels, manual annotation, review or adjudication.

Frozen experiment:

- masked language modeling only;
- seed 20260826;
- pinned model/tokenizer revisions;
- max length 128, batch size 2, 200 steps;
- learning rate 0.00002, masking probability 0.15;
- selection required at least 1% held-out MLM-loss improvement and then the lowest final
  validation MLM loss under identical vocabulary hashes.

| Encoder | Initial MLM loss | Final MLM loss | Relative improvement | Decision |
| --- | ---: | ---: | ---: | --- |
| MacBERT-base | 1.424986 | 1.162618 | 18.4120% | Preserved comparison |
| BERT-base-Chinese | 1.135982 | 0.947099 | 16.6273% | Promoted representation candidate |

Exactly one candidate is promoted: `google-bert/bert-base-chinese` revision
`8f23c25b06e129b6c986331a13d8d025a92cf0ea`. Its ignored adapted weight SHA-256 is
`eaacc66a4993a448e9e9dd7d6aab0fc33290d1f4e4e4e8d209efc1d7a17fd3b9`.

The loss evidence supports domain adaptation/representation only. It is not sentiment accuracy,
event-impact accuracy or production validation.

## B3B — candidate output matrix

| Candidate | Output category | What it predicts | B3 maturity |
| --- | --- | --- | --- |
| FSC-adapted BERT | `DOMAIN_ENCODER` | masked-token likelihood and financial-domain context | representation candidate |
| FSC-adapted BERT embedding | `EMBEDDING` | similarity for retrieval/ranking | not downstream validated |
| Five historical Chinese baselines | `LINGUISTIC_SENTIMENT` | automated P/N/N textual polarity | all failed frozen B4 gate |
| Deterministic event/impact rules | `IMPACT_SIGNAL` | rule-matched impact hypothesis with abstention | automated signal only |
| TWMD major-event taxonomy | `EVENT_CLASS` | inferred category and classifier confidence | contract only; zero B3 rows |
| Historical reaction proxy | `MARKET_REACTION` | mechanically measured post-event movement | not linguistic sentiment |
| GDELT Tone | `MEDIA_TONE` | dictionary-derived media-tone/intensity proxy | temporarily unavailable/conditional |

Unlike tasks are not compared with one common accuracy metric.

## Sentiment and supervision decision

No permissible independent sentiment-label source was found. The FSC corpus is unlabeled;
TWMD event classes are inferred categories; market returns are reactions; GDELT Tone is a media
proxy; and the prior cross-model comparison is an AI stability diagnostic. None can become
human-validated sentiment truth.

Therefore B3 trained no sentiment classifier and generated no pseudo-label training/evaluation
set. Existing weak-supervision code is preserved as automated-signal infrastructure, but B3 made
no real-source weak-label run. No supervisor was reused as its evaluator, so circular validation
did not occur.

Historical sentiment results remain immutable: macro-F1 0.320, 0.357, 0.442, 0.592 and 0.640.
All failed the pre-existing B4 gate. Current Chinese product behavior remains
`ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED`.

## TWMD boundary

B3 reads only the public B2.1 contract and candidate schema. It uses zero TWMD dataset rows and no
raw licensed payload. `event_class` remains `EVENT_CLASS`, never sentiment. The event clock retains
`SOURCE_CONTRACT_ASSUMPTION` for Asia/Taipei; it is not reported as an observed offset.

## GDELT recovery

One bounded official HTTPS request targeted the GDELT Article List RSS path, capped at 512 KB.
TLS verification stayed enabled; no publisher page or raw payload was saved. The HTTP path was
reached, but the returned bytes failed RSS XML parsing, so implementation remains
`TEMPORARILY_UNAVAILABLE_CONDITIONAL`. This does not reject GDELT as a source and does not block
B3. GAL metadata availability would not establish GKG Tone availability in any case.

## B4 handoff

`research/configs/b3_domain_and_candidate_signals.v1.json` is the frozen B4 candidate manifest.
B4 may assign `VALIDATED`, `AUTOMATED_SIGNAL_ONLY` or `ABSTAIN`. Its sentiment gate remains
macro-F1 at least 0.70 and recall at least 0.60 for every required class. B3 makes no maturity
decision in advance.

No Track A, Track C, GAS, LINE, backend deployment or Streamlit behavior changed.

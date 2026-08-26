# M7 Bounded Domain-Adaptation Pilot Result

Run date: 2026-08-26  
Scope: bounded unlabelled MLM adaptation on the FSC train split  
Excluded: sealed test, sentiment labels, downstream prediction, backtesting and public release

## Predeclared budget

- corpus SHA-256: `389640a2f3232cb95bc8c47032673ba8f90a8d5eb23affc1f01a03971d20366c`;
- deterministic sample: 512 train records and 64 validation records;
- sequence length 128, batch size 2, 200 optimizer steps per candidate;
- learning rate 0.00002, MLM probability 0.15, gradient norm cap 1.0;
- seed 20260826 and CPU-only execution;
- maximum 900 seconds per candidate;
- selection gate: finite loss, at least 1% relative validation improvement, identical vocabulary
  hashes, then lowest final validation MLM loss.

## Result

| Candidate | Initial validation loss | Final validation loss | Relative improvement | Seconds/step | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| MacBERT-base | 1.424986 | 1.162618 | 18.4120% | 0.2859 | PASS |
| BERT-base-Chinese | 1.135982 | 0.947099 | 16.6273% | 0.2911 | PASS |

Both candidates use the same vocabulary SHA-256
`3e594fb37bd9c81abcad66bb4321b1e71bbbb5154784f02bf1533055b506b134`.
Under the predeclared final-loss rule, **BERT-base-Chinese is the recommended frozen
representation candidate** for the next research stage. MacBERT remains a preserved negative or
comparison result and must not be hidden.

This recommendation is limited to MLM fit on the accepted FSC regulatory validation subset. It is
not evidence of sentiment accuracy, event-impact accuracy, Taiwan news generalisation or downstream
stock-prediction value. Those claims require later leakage-safe ablation and sealed evaluation.

## Resource and artifact record

- MacBERT runtime: 59.7064 seconds; weight SHA-256
  `3be49cf57cc9f6330dee377cd97fbba0749bafea09529093c97735bc3b09fc9b`.
- BERT-base-Chinese runtime: 61.1723 seconds; weight SHA-256
  `eaacc66a4993a448e9e9dd7d6aab0fc33290d1f4e4e4e8d209efc1d7a17fd3b9`.
- Peak process RSS: 2,450,964,480 bytes.
- Adapted artifacts: about 391 MB each, 782 MB total.
- Artifact root: ignored `.tools/models/m7-domain-adaptation-pilot-v1/`.
- No checkpoint, raw corpus, secret or model weight is committed.

Each artifact directory includes `model.safetensors`, tokenizer files and a raw-free
`pilot_metadata.json` pinning base revision, corpus/train hashes, seed, hyperparameters and adapted
weight hash. The runner refuses to overwrite an existing artifact directory.

## M7 decision

M7 is complete at the approved bounded-pilot scope. Do not launch a larger/full-corpus training run
until downstream representation usefulness or a new explicit research need justifies its compute.
The next planned milestone is M8 automatic market-reaction labeling; the selected representation
must remain frozen and the sealed FSC test must remain unread.

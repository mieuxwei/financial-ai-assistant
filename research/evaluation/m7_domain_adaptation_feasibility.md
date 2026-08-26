# M7 Taiwan Financial Domain-Adaptation Feasibility

Run date: 2026-08-26  
Decision scope: operational feasibility only  
Excluded: sentiment evaluation, downstream prediction claims, full training and model release

## Corpus snapshot

The deterministic FSC builder consumed the five checksummed official archives and wrote raw text
only under ignored `.tools/corpora/fsc-domain-corpus-v1/`.

| Stage | Records |
| --- | ---: |
| FSC XML input | 6,047 |
| Empty content excluded | 1 |
| Invalid publication date excluded | 10 |
| Normalized duplicate content excluded | 15 |
| Retained | 6,021 |
| Train | 5,117 |
| Validation | 482 |
| Sealed test | 422 |

Corpus SHA-256:
`389640a2f3232cb95bc8c47032673ba8f90a8d5eb23affc1f01a03971d20366c`.

Splits use each document family's maximum publication date. A family is assigned wholly to train
(through 2022-12-31), validation (through 2024-12-31) or sealed test (2025 onward). This explains
why a later split can contain an older revision: it was moved forward with its newer family member
instead of leaking across splits. The builder verified that neither family hashes nor normalized
content hashes cross splits.

## Bounded model check

The CPU-only check used 16 deterministic train examples, eight validation examples, length 64,
batch size two, two optimizer steps, seed 20260826 and no test records. Model revisions were pinned:

| Candidate | Revision | Parameters | Initial validation MLM loss | Final validation MLM loss | Seconds/step |
| --- | --- | ---: | ---: | ---: | ---: |
| [`hfl/chinese-macbert-base`](https://huggingface.co/hfl/chinese-macbert-base) | `a986e004…` | 102,290,312 | 2.124423 | 1.855565 | 0.2510 |
| [`google-bert/bert-base-chinese`](https://huggingface.co/google-bert/bert-base-chinese) | `8f23c25b…` | 102,290,312 | 1.336560 | 1.364859 | 0.2571 |

Both produced finite losses. Peak process RSS was 2,348,171,264 bytes. Each ignored model snapshot
occupies about 393 MB. No adapted weights were saved.

The observed loss deltas are **not a model ranking**: two steps and eight validation examples are
far below a scientific comparison. They only prove that corpus loading, deterministic masking,
forward/backward passes, revision pinning and raw-free reporting work within local resources.

## Decision

The M7 small-feasibility gate is `PASS` for both candidates. The subsequently approved bounded
pilot is complete and recorded in `research/evaluation/m7_domain_adaptation_pilot.md`. It kept test
sealed, remained unlabelled and saved weights only to ignored storage. Neither feasibility nor the
pilot establishes Traditional-Chinese sentiment accuracy or authorizes public model release.

Reproduce the corpus and feasibility checks:

```bash
python -m research.training.fsc_corpus \
  --config research/configs/fsc_domain_corpus.v1.json \
  --output-dir .tools/corpora/fsc-domain-corpus-v1

python -m research.training.domain_adaptation_feasibility \
  --config research/configs/m7_domain_adaptation_feasibility.v1.json \
  --corpus-dir .tools/corpora/fsc-domain-corpus-v1 \
  --cache-dir .tools/huggingface \
  --output artifacts/m7-domain-adaptation-feasibility-report.json
```

The report records no source text, manual labels, manual review or model weights.

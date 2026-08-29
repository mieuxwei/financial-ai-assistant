# B3.1 Chinese Financial Sentiment Label Source Audit

Audit date: 2026-08-29  
Decision: **NO independently permissible training/evaluation label source**  
Next executable unit: **B4 — Validation / Abstention Decision; not started**

## Scope and decision rule

This bounded audit examined exactly three primary candidates: CFSC-ABSA, the Chinese subset of
`Kenpache/multilingual-financial-sentiment`, and StockSentCN. No secondary dataset search was
needed. The audit asks whether a source is independently usable for Chinese/Taiwan financial
`LINGUISTIC_SENTIMENT` with `positive`/`neutral`/`negative` outputs. It does not equate this task
with `EVENT_CLASS`, `MARKET_REACTION`, `FINANCIAL_IMPACT`, `MEDIA_TONE` or `INVESTOR_MOOD`.

Existing externally published human labels are compatible with the project's zero-manual-label
rule. The project itself created no labels and performed no label review or adjudication.

## Comparison table

| Source | Dataset size | Chinese sample count | Task | Label set | Label provenance | Human / weak / pseudo | Domain | Script | Split structure | Leakage risk | License | Raw-text redistribution | Train suitability | Independent-eval suitability | Final classification |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CFSC-ABSA | 41,496 aspect instances from 15,446 sentences | 15,446 sentences | Aspect-level polarity | positive / neutral / negative | Not documented in the repository | Unverified | Mainland Chinese financial-news sentences | Simplified | 33,184 train / 8,312 test aspect instances; no dev; sentence-family isolation unknown | High: repeated sentence per aspect and possible cross-split sentence leakage are unresolved | **No license found**; GitHub API reports `null` | Not established; source publishers are not identified | No | No | **HOLD** |
| Multilingual financial sentiment — ZH | 39,829 total | 7,930 | Claimed sentence-level sentiment | negative / neutral / positive | Card says “annotated” but names no method, annotators, rules or source corpus | Unverified | Mainland Chinese financial-news sentences | Simplified in bounded sample | One 39,829-row `train` file; no dev/test | High: no official split, provenance, source-family isolation or cross-language-overlap evidence | Metadata says Apache-2.0; card also says academic/noncommercial only and publisher copyright retained | Restricted/ambiguous; no clean publisher-text grant | No | No | **HOLD** |
| StockSentCN | 9,238,551 | 9,238,551 | Bullish / bearish / neutral investor expectation | 0 negative, 1 positive, 2 neutral | 191,129 base rows: emoji distant supervision plus a small manually created neutral seed; 9,047,422 model pseudo-labels | Mixed, overwhelmingly weak/pseudo | EastMoney stock-forum comments | Simplified | Base rows reportedly random 8:1:1; 900 expert-audit labels are not released as a separable split | High: pseudo-label circularity, non-temporal split and duplicate/source-family risk unverified | **No license found**; full dataset is not in the repository | Not established; scraped forum-text rights not granted | No | No | **HOLD** |

The table's “No” decisions mean **not approved now**. They do not claim that the corpora have no
scientific value.

## A. CFSC / CFSC-ABSA

### Verified facts

The public [CFSC repository](https://github.com/Ya-dongLi/CFSC) describes 15,446 Chinese financial-
news sentences expanded into 41,496 aspect instances. Each instance contains a sentence, one
aspect term and its aspect polarity. The reported class counts are 25,519 positive, 5,260 neutral
and 10,717 negative. Its provided 8:2 split contains 33,184 train and 8,312 test instances.

The repository was inspected at tree SHA `3f0226161cf5266b87438c98a30418f65d5cd064`. It exposes the
data files without authentication, but contains no `LICENSE` file; repository metadata reports no
license. The README's citation section still contains only `aaa` and gives no paper, annotation
manual, annotator qualification, agreement statistic, exact news publishers, dates or copyright
grant.

### Special audit findings

- The labels are **aspect-level**, not whole-sentence labels.
- One sentence can yield multiple examples because each aspect term is one row.
- The repository does not establish whether splitting occurred before or after aspect expansion.
- It does not establish that all aspects from one sentence remain in one split.
- Full sentence-level duplicate and cross-split leakage rates were therefore not verified.
- Label provenance cannot be called human, expert, crowd, weak or pseudo from available evidence.
- No deterministic aspect-to-sentence mapping is adopted. Conflicting aspect polarities would make
  a silent sentence-level conversion scientifically invalid.
- The corpus is Simplified Chinese and Mainland-market focused; this is a transfer limitation, not
  an automatic rejection.

### Decision

Task alignment is **PARTIAL_MATCH**. Final classification: **HOLD**. Approval requires, at minimum,
an explicit dataset/raw-text license, annotation provenance, source/copyright provenance, and a
sentence-family-isolated split or a reproducible rebuild of one. CFSC-ABSA is not approved for
training or independent evaluation in B3.2/B4.

## B. Multilingual Financial Sentiment Dataset — Chinese subset

### Verified facts

The [Hugging Face dataset card](https://huggingface.co/datasets/Kenpache/multilingual-financial-sentiment)
at revision `9d43950d151602f623f28bba62f30554b5d40dd2` reports 39,829 news sentences across seven
languages and 7,930 Chinese rows: 1,921 negative, 3,126 neutral and 2,883 positive. Chinese sources
are listed as Sina Finance, EastMoney, 10jqka, NBD, China Securities, 163 Finance, Hexun and STCN.
The published schema is `sentence`, `label`, `source`, `language`.

Access is public and ungated. The repository has one CSV exposed as a single `train` split and no
official development or test split. A bounded Dataset Viewer inspection sampled 100 rows at each
of eight fixed offsets (800/39,829 total); 100 observed Chinese rows were Simplified Chinese and
came from Sina Finance, EastMoney and 10jqka. There were zero exact duplicate sentences within
those 800 rows. This is only a schema/sanity result—it is **not** a full duplicate, near-duplicate,
publisher-family or cross-language overlap audit.

### Provenance and license boundary

The card calls the rows “annotated” but does not say whether the labels came from people, experts,
crowd workers, rules, models, LLMs, translation, market reactions or another dataset. It does not
state whether Chinese is original or translated, nor whether Chinese rows are paired with English
rows. The source fields and bounded samples are consistent with originally Chinese publisher text,
but that is not proof of an independent Chinese label process.

The metadata declares `apache-2.0`, while the same card limits use to academic/noncommercial
research, invokes fair-use/TDM exceptions, retains copyright with publishers, and requires separate
publisher licenses for commercial use. Apache-2.0 does not itself cure missing rights to underlying
news sentences. The scope of the license over text, labels, derivative model weights and public
artifacts is therefore ambiguous.

### Decision

Task alignment is **DIRECT_MATCH** in format, but label provenance, split independence and rights
are unresolved. Final classification: **HOLD**. It is not approved for training, validation or
external evaluation, and its Chinese rows cannot be treated as independent from the English rows.

## C. StockSentCN

### Verified facts and portion separation

The peer-reviewed [StockSentCN paper](https://doi.org/10.13451/j.sxu.ns.2024111) states that raw
comments were scraped from 881 EastMoney stock forums over 1990–2023. Its label semantics are
explicitly bullish, bearish and neutral investor expectations about stock-price movement—not
general news linguistic tone.

The 9,238,551 rows separate conceptually as follows:

- **Base distant-supervised portion — 191,129:** 50,261 negative, 126,903 positive and 13,965
  neutral. Positive/negative seeds were generated from selected bullish/bearish emojis, followed by
  classifier-based filtering. The authors manually created a small neutral seed.
- **Pseudo-labelled expansion — 9,047,422:** 2,645,371 negative, 4,836,677 positive and 1,565,374
  neutral, generated by a continually updated classifier.
- **Human-evaluation sample — 900:** three random groups of 300, each independently labelled by one
  trained financial-domain expert. The paper reports mean Kappa 0.85, macro-F1 88.45% and weighted
  F1 90.34% against the automatic labels.

The human evaluation supports a published quality claim, but it does not turn all 9.23 million
labels into gold truth. More importantly, those 900 expert labels are not released as a separable
evaluation file. The paper's base-data 8:1:1 experiment evaluates weak labels, not that independent
human-gold set.

### Access and rights

The [StockSentCN repository](https://github.com/lidayuls/StockSentCN) at tree SHA
`62a4b6118cf70dde63ab0ce6a21e3f4669c975aa` contains only a README sample and asks interested users
to contact the authors. It contains no dataset file and no license; repository metadata reports no
license. Available evidence also does not grant redistribution or derivative-training rights for
the scraped EastMoney forum text.

### Decision

Task alignment is **WEAK_PROXY** because this is investor mood/directional expectation rather than
Taiwan financial-news linguistic sentiment. If access and rights were later cleared, the base
portion could be considered only for weak supervision, the pseudo-labelled expansion only as
training auxiliary, and the 900 expert subset only as gold evaluation **if actually released**.
Under current evidence, the single final classification is **HOLD**.

## Independence, duplication and Taiwan transfer

No candidate supplies a currently usable independent evaluation set:

- CFSC's aspect families may cross its instance-level split;
- the multilingual dataset supplies no evaluation split or annotation lineage;
- StockSentCN's expert labels are unpublished and its released sample does not distinguish base,
  pseudo or gold provenance.

All three are Simplified-Chinese/Mainland-domain resources. This does not disqualify them, but a
later approved source would still need Taiwan-domain robustness reporting. No candidate may be
mixed with FSC adaptation data and then called independent without source/family overlap checks.

## Reproducibility record

Only public metadata, README files and bounded Dataset Viewer rows were stored under ignored
`.tools/b3_1_audit/`. No full corpus or publisher article body was downloaded. The authoritative
machine decision is
`research/configs/b3_1_chinese_sentiment_label_sources.v1.json`. Stable identifiers used here are:

- CFSC tree SHA: `3f0226161cf5266b87438c98a30418f65d5cd064`;
- multilingual dataset revision: `9d43950d151602f623f28bba62f30554b5d40dd2`;
- StockSentCN tree SHA: `62a4b6118cf70dde63ab0ce6a21e3f4669c975aa`;
- StockSentCN DOI: `10.13451/j.sxu.ns.2024111`.

Ignored local evidence-manifest SHA-256 values are `9e4e4679...` (CFSC metadata/READMEs),
`05f2d411...` (multilingual metadata/README), `97c2685f...` (eight fixed-offset Dataset Viewer
samples) and `de206f10...` (StockSentCN metadata/README). Full values and the hash method are frozen
in the machine decision file. These are evidence/sample hashes, not full-corpus hashes.

Required preprocessing and mapping were **not** frozen because no source passed admission. A
future CFSC proposal would need aspect-family grouping and an explicit aspect-to-sentence policy;
a future StockSentCN proposal would need provenance flags separating base/pseudo/gold rows.

## Gate answer and stop boundary

Is there now at least one independently permissible label source that justifies training a
project-owned Chinese financial sentiment classifier?

**NO**

Therefore B3.2 is not created. The next and only executable unit remains **B4 — Validation /
Abstention Decision**, with the existing macro-F1 `>= 0.70` and per-required-class recall
`>= 0.60` gate unchanged. Chinese sentiment remains
`ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED`.

No sentiment model was trained, no pseudo-label set was generated, eLAND was not used or
re-audited, no manual labels were created, and Track A, GAS, deployment, commit and push were not
modified by this audit.

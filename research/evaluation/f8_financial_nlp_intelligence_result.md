# F8 Financial NLP Intelligence Result

Status: **COMPLETE — contract and evidence audit only; no model training or deployment**

F8 unified the existing English FinBERT, language gate, TWSE announcement metadata, ticker
matching and deterministic Taiwan event cues behind one abstention-safe product contract. It did
not download a model, call an external API or LLM, run model inference, persist source rows, modify
Track A, or claim new NLP performance.

## Frozen behavior

| Input/capability | Product behavior |
| --- | --- |
| English financial text with pinned prediction | Stores FinBERT polarity, three probabilities, score, exact model revision and input hash |
| English text without optional model runtime | `ELIGIBLE_NOT_SCORED`; all polarity outputs remain null |
| Chinese/Taiwan text | `ABSTAIN / CHINESE_SENTIMENT_NOT_VALIDATED`; all polarity outputs remain null |
| Unsupported other language | `ABSTAIN / UNSUPPORTED_LANGUAGE` |
| TWSE official metadata | Passes through company name, source clause and fact date without rewriting |
| Deterministic Taiwan cue match | Separate research-only event/impact proxy; never sentiment ground truth |
| No deterministic cue match | Explicit event abstention |
| Source summary | Bounded source excerpt only; no generated summary or full article storage |

The only accepted English sentiment model remains
`ProsusAI/finbert@4556d13015211d73dccd3fdd39d39232506f3e43`. A supplied prediction from any
other revision is rejected. A supplied prediction for Chinese or another unsupported language is
also rejected rather than silently converted.

## Audit result

- F8 config SHA-256:
  `de7c372fc4ba136f10cc2bf78056898d8ea97cf6ff0fbb4a2aa7857be9e1bbc4`
- Aggregate analysis SHA-256:
  `8994a66e2fef70da2ad16d54cb3698ac8e2f14badad4e9237a03e2669b97ab42`
- Seven pre-existing evidence files: **7/7 byte hashes verified**.
- Controlled contract-routing fixtures: **3**; these are not a performance evaluation.
- Sentiment routing: 2 `ABSTAIN`, 1 `ELIGIBLE_NOT_SCORED`.
- Event routing: 1 `SIGNAL`, 2 `ABSTAIN`.
- Fixture rows/private text persisted: **no**.
- External API, model download, inference, training, manual annotation/review, LLM and deployment:
  **all no**.

The aggregate machine analysis is stored only under ignored `.tools/`; the raw-free report under
`artifacts/` is also ignored by the repository policy. This public record contains only aggregate
contract evidence.

## Capability boundary

News/TWSE retrieval, ticker matching, official metadata and the optional English FinBERT adapter
already exist. Deterministic event cues remain research signals. Embedding-based related-event
retrieval is a research candidate, not an integrated product capability. LLM/Perplexity daily
briefing remains optional and on-demand only and was not executed in F8.

Existing Chinese model diagnostic scores, the FSC 6,021-record corpus, BERT/MacBERT feasibility,
weak-supervision research and source-governance evidence remain unchanged. None is human-validated
Chinese sentiment ground truth. Eland remains `HOLD / excluded from active modeling` and appears
only as historical rejection evidence.

## Claim boundary and next decision

F8 proves that the product can route supported, unsupported and event-intelligence outputs without
fabricating polarity. It does **not** prove English or Chinese model accuracy, semantic validity,
market predictiveness, causal impact or prospective performance.

F9 is optional and non-blocking. After review, the project may either run F9 only if timestamp-safe
historical NLP features are already suitable for the frozen paired ablation, or skip directly to
F10 backend integration. F8 itself does not authorize either next step.

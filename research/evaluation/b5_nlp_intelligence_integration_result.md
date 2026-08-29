# B5 NLP Intelligence Integration Result

Date: 2026-08-29  
Decision: **B5 COMPLETE**  
Next executable unit: **F11B — Controlled LINE Financial AI Integration; not started**

B5 reuses the F8 item assembler and F10 `GET /api/v1/research/intelligence/{ticker}` endpoint. The
existing response remains version `financial-intelligence-response-v1`; each item gains an optional
`track_b_intelligence` extension, so existing fixtures and clients remain valid.

The extension contains separate event classification, linguistic sentiment, stored market-
reaction magnitude, media tone, representation lineage, source/cutoff lineage and limitations.
Chinese probabilities and polarity are null; direction is null. Market-reaction maturity remains
`AUTOMATED_SIGNAL_ONLY`. Stored B4 scores are converted to LOW/MODERATE/HIGH/VERY_HIGH with the
frozen historical reference. No stored score or unsafe availability timestamp returns abstention.

B4 findings are unchanged: signed Spearman 0.0349/0.0784/0.0408 for market/metadata/BERT; mean text
increment -0.0394; metadata absolute-reaction Spearman 0.2504 and top-decile lift 1.623. BERT is
retained only for financial-domain representation and future semantic retrieval.

GDELT tone is null with `UNAVAILABLE_OR_CONDITIONAL`; event class cannot populate sentiment. The
service uses database rows only and makes no request-time provider, model or LLM calls.

Audit analysis SHA-256:
`99d2fa67a7fd32a76fecbc41cfc0c362f40d5cf06979d92a7d9e11a3bfd856c2`.
Config canonical SHA-256:
`6ea9be0f46b1cf2b7bc7667912a32f8ecd9041a4216450503e268c54547b5b0e`.

No model retraining, Track A modification, GAS/LINE modification, deployment or provider call
occurred. F11B was not started automatically.

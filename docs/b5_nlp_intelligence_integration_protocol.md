# B5 NLP Intelligence Integration Protocol

Status: **COMPLETE / FROZEN**  
Contract: `b5-financial-intelligence-v1`

B5 extends the existing F8 assembler and F10 database-only endpoint with one optional,
backward-safe `track_b_intelligence` object. It performs no provider call, model inference,
training, LLM call or deployment during request handling.

The object keeps event classification, linguistic sentiment, market reaction, media tone and
financial-domain representation separate. Chinese polarity and direction are always null with
explicit abstention. TWMD classification is an inferred taxonomy only. GDELT media tone remains
unavailable/conditional and, if later supported, must remain a proxy.

The B4 metadata magnitude signal keeps maturity `AUTOMATED_SIGNAL_ONLY`. Stored scores use the
frozen 2021–2025 OOF reference and thresholds fixed before individual presentation: 50th, 80th and
95th percentiles, corresponding to score cutoffs 0.0091336201, 0.0121038278 and 0.0148006953.
Bands are LOW, MODERATE, HIGH and VERY_HIGH. Missing, future or timezone-uncertain availability
timestamps abstain. B5 never computes a fresh score inside an API request.

The FSC-adapted BERT artifact remains representation-only. B4's negative text increment is
preserved; B5 does not claim BERT improves return, reaction or direction prediction.

TWMD remains `ACCEPT_SECONDARY` and `LICENSED_EVENT_METADATA_PRIVATE`. Raw payloads, bulk licensed
records, secrets and private paths are never returned. The public contract contains only safe
derived fields, version identifiers, aggregate evidence and limitations.

F11B, F12, Track A, GAS and LINE are outside B5 and were not modified.

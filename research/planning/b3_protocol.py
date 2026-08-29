from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROTOCOL_VERSION = "b3-domain-and-candidate-signals-v1"
DEFAULT_CONFIG = Path("research/configs/b3_domain_and_candidate_signals.v1.json")


class CorpusContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["fsc-domain-corpus-v1"]
    path: Path
    corpus_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    train_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    test_sha256_recorded_from_manifest_only: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_count: Literal[6021]
    sentiment_labels_present: Literal[False]
    manual_labels_used: Literal[False]
    allowed_objective: Literal["MASKED_LANGUAGE_MODELING_AND_REPRESENTATION_ONLY"]


class EncoderCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    model_id: str
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    initial_validation_mlm_loss: float = Field(gt=0)
    final_validation_mlm_loss: float = Field(gt=0)
    relative_validation_improvement: float
    weight_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    promoted: bool


class DomainAdaptationContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_source: Literal["m7-domain-adaptation-pilot-v1"]
    retrain_in_b3: Literal[False]
    objective: Literal["MASKED_LANGUAGE_MODELING"]
    train_examples: Literal[512]
    validation_examples: Literal[64]
    sealed_test_read: Literal[False]
    max_length: Literal[128]
    batch_size: Literal[2]
    train_steps: Literal[200]
    learning_rate: Literal[0.00002]
    mlm_probability: Literal[0.15]
    selection_metric: Literal["final_validation_mlm_loss"]
    minimum_relative_validation_improvement: Literal[0.01]
    candidates: list[EncoderCandidate] = Field(min_length=2, max_length=2)
    promoted_candidate: Literal["bert-base-chinese"]
    artifact_directory: Path
    vocabulary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    claim: Literal[
        "DOMAIN_ADAPTED_CHINESE_FINANCIAL_REPRESENTATION_CANDIDATE_NOT_SENTIMENT_MODEL"
    ]

    @model_validator(mode="after")
    def validate_promotion(self) -> DomainAdaptationContract:
        promoted = [item for item in self.candidates if item.promoted]
        if len(promoted) != 1 or promoted[0].candidate_id != self.promoted_candidate:
            raise ValueError("B3 must promote exactly one predeclared representation candidate")
        eligible = [
            item
            for item in self.candidates
            if item.relative_validation_improvement
            >= self.minimum_relative_validation_improvement
        ]
        winner = min(eligible, key=lambda item: item.final_validation_mlm_loss)
        if winner.candidate_id != self.promoted_candidate:
            raise ValueError("promoted encoder violates the frozen final-loss rule")
        return self


class SentimentTrainingContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    independent_permissible_label_source: None
    new_classifier_trained: Literal[False]
    pseudo_labels_used_for_training: Literal[False]
    manual_annotation_used: Literal[False]
    manual_review_used: Literal[False]
    circular_validation: Literal[False]
    current_product_output: Literal["ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED"]


class HistoricalBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    macro_f1: float = Field(ge=0, le=1)
    gate: Literal["FAIL"]


class SignalCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    output_category: Literal[
        "DOMAIN_ENCODER",
        "LINGUISTIC_SENTIMENT",
        "EVENT_CLASS",
        "IMPACT_SIGNAL",
        "MARKET_REACTION",
        "MEDIA_TONE",
        "EMBEDDING",
    ]
    predicts: str = Field(min_length=1)
    maturity: str = Field(min_length=1)
    ground_truth_claim: str = Field(min_length=1)


class TwmdContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_contract: Literal["b2.1-twmd-secondary-source-v1"]
    b3_usage: Literal["CONTRACT_AND_CANDIDATE_SCHEMA_ONLY_NO_DATASET_ROWS"]
    event_class_is_sentiment: Literal[False]
    timezone_basis: Literal["SOURCE_CONTRACT_ASSUMPTION"]
    raw_payload_used: Literal[False]


class GdeltContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_status: Literal["ACCEPT_SECONDARY_IN_PRINCIPLE"]
    implementation_status: Literal["TEMPORARILY_UNAVAILABLE_CONDITIONAL"]
    recovery_endpoint: str
    recovery_result: Literal["TLS_VERIFIED_HTTP_PATH_REACHED_BUT_RSS_PARSE_FAILED"]
    tls_verification_disabled: Literal[False]
    publisher_pages_fetched: Literal[False]
    raw_payload_saved: Literal[False]
    tone_is_sentiment_truth: Literal[False]


class B4Gate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    macro_f1_minimum: Literal[0.70]
    per_required_class_recall_minimum: Literal[0.60]
    allowed_decisions: list[Literal["VALIDATED", "AUTOMATED_SIGNAL_ONLY", "ABSTAIN"]]
    predeclared_in_b3: Literal[True]


class B3Protocol(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: Literal["b3-domain-and-candidate-signals-v1"] = PROTOCOL_VERSION
    status: Literal["B3_CURRENT_PROTOCOL_FROZEN"]
    seed: Literal[20260826]
    corpus: CorpusContract
    domain_adaptation: DomainAdaptationContract
    sentiment_training: SentimentTrainingContract
    historical_sentiment_baselines: list[HistoricalBaseline] = Field(min_length=5, max_length=5)
    candidate_output_matrix: list[SignalCandidate] = Field(min_length=1)
    twmd: TwmdContract
    gdelt: GdeltContract
    b4_gate: B4Gate
    prohibited_sources: list[Literal["eland"]]
    track_a_modified: Literal[False]
    track_c_modified: Literal[False]
    next_executable_unit: Literal["B4_VALIDATION_ABSTENTION_DECISION"]

    @model_validator(mode="after")
    def validate_research_boundaries(self) -> B3Protocol:
        expected_scores = [0.320, 0.357, 0.442, 0.592, 0.640]
        observed_scores = [item.macro_f1 for item in self.historical_sentiment_baselines]
        if observed_scores != expected_scores:
            raise ValueError("historical sentiment evidence must remain immutable")
        categories = {item.output_category for item in self.candidate_output_matrix}
        required = {
            "DOMAIN_ENCODER",
            "LINGUISTIC_SENTIMENT",
            "EVENT_CLASS",
            "IMPACT_SIGNAL",
            "MARKET_REACTION",
            "MEDIA_TONE",
            "EMBEDDING",
        }
        if categories != required:
            raise ValueError("B3 candidate matrix must preserve separate output concepts")
        if self.b4_gate.allowed_decisions != [
            "VALIDATED",
            "AUTOMATED_SIGNAL_ONLY",
            "ABSTAIN",
        ]:
            raise ValueError("B4 decision vocabulary is frozen")
        return self


def load_protocol(path: Path = DEFAULT_CONFIG) -> B3Protocol:
    return B3Protocol.model_validate_json(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_b3_evidence(protocol: B3Protocol) -> dict[str, object]:
    corpus_manifest = json.loads((protocol.corpus.path / "manifest.json").read_text())
    if corpus_manifest["corpus_sha256"] != protocol.corpus.corpus_sha256:
        raise ValueError("FSC corpus semantic hash mismatch")
    if corpus_manifest["manual_labels_used"] is not False:
        raise ValueError("FSC corpus cannot contain manual labels")
    if sha256_file(protocol.corpus.path / "train.jsonl") != protocol.corpus.train_sha256:
        raise ValueError("FSC train split hash mismatch")
    if (
        sha256_file(protocol.corpus.path / "validation.jsonl")
        != protocol.corpus.validation_sha256
    ):
        raise ValueError("FSC validation split hash mismatch")

    artifact_root = protocol.domain_adaptation.artifact_directory
    metadata = json.loads((artifact_root / "pilot_metadata.json").read_text())
    promoted = next(item for item in protocol.domain_adaptation.candidates if item.promoted)
    if metadata["candidate_id"] != promoted.candidate_id:
        raise ValueError("promoted artifact metadata identifies another candidate")
    if metadata["base_revision"] != promoted.revision:
        raise ValueError("promoted artifact base revision mismatch")
    if metadata["corpus_sha256"] != protocol.corpus.corpus_sha256:
        raise ValueError("promoted artifact corpus lineage mismatch")
    weight_sha256 = sha256_file(artifact_root / "model.safetensors")
    if weight_sha256 != promoted.weight_sha256 or metadata["weight_sha256"] != weight_sha256:
        raise ValueError("promoted artifact weight hash mismatch")
    return {
        "protocol_version": protocol.protocol_version,
        "corpus_sha256": protocol.corpus.corpus_sha256,
        "train_sha256": protocol.corpus.train_sha256,
        "validation_sha256": protocol.corpus.validation_sha256,
        "sealed_test_file_read": False,
        "promoted_candidate": promoted.candidate_id,
        "promoted_revision": promoted.revision,
        "promoted_weight_sha256": weight_sha256,
        "new_training_performed": False,
        "new_sentiment_classifier_trained": False,
        "pseudo_labels_used": False,
        "manual_labels_used": False,
        "circular_validation": False,
        "twmd_dataset_rows_used": 0,
        "gdelt_implementation_status": protocol.gdelt.implementation_status,
        "candidate_categories": sorted(
            item.output_category for item in protocol.candidate_output_matrix
        ),
        "next_executable_unit": protocol.next_executable_unit,
    }

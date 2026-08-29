import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from research.planning.b3_protocol import B3Protocol, audit_b3_evidence, load_protocol


def test_b3_protocol_freezes_domain_and_signal_boundaries() -> None:
    protocol = load_protocol()
    assert protocol.corpus.sentiment_labels_present is False
    assert protocol.domain_adaptation.retrain_in_b3 is False
    assert protocol.domain_adaptation.promoted_candidate == "bert-base-chinese"
    assert protocol.sentiment_training.new_classifier_trained is False
    assert protocol.sentiment_training.circular_validation is False
    assert protocol.twmd.event_class_is_sentiment is False
    assert protocol.gdelt.tone_is_sentiment_truth is False
    assert protocol.next_executable_unit == "B4_VALIDATION_ABSTENTION_DECISION"


def test_b3_evidence_hashes_are_reproducible_without_reading_test_split() -> None:
    report = audit_b3_evidence(load_protocol())
    assert report["promoted_candidate"] == "bert-base-chinese"
    assert report["promoted_weight_sha256"] == (
        "eaacc66a4993a448e9e9dd7d6aab0fc33290d1f4e4e4e8d209efc1d7a17fd3b9"
    )
    assert report["sealed_test_file_read"] is False
    assert report["twmd_dataset_rows_used"] == 0
    assert report["manual_labels_used"] is False


def test_b3_rejects_sentiment_training_without_independent_labels() -> None:
    payload = json.loads(
        Path("research/configs/b3_domain_and_candidate_signals.v1.json").read_text()
    )
    payload["sentiment_training"]["new_classifier_trained"] = True
    with pytest.raises(ValidationError):
        B3Protocol.model_validate(payload)


def test_b3_rejects_twmd_sentiment_and_circular_validation() -> None:
    payload = json.loads(
        Path("research/configs/b3_domain_and_candidate_signals.v1.json").read_text()
    )
    payload["twmd"]["event_class_is_sentiment"] = True
    with pytest.raises(ValidationError):
        B3Protocol.model_validate(payload)

    payload = json.loads(
        Path("research/configs/b3_domain_and_candidate_signals.v1.json").read_text()
    )
    payload["sentiment_training"]["circular_validation"] = True
    with pytest.raises(ValidationError):
        B3Protocol.model_validate(payload)


def test_b3_rejects_multiple_promoted_encoders_and_changed_gate() -> None:
    payload = json.loads(
        Path("research/configs/b3_domain_and_candidate_signals.v1.json").read_text()
    )
    payload["domain_adaptation"]["candidates"][0]["promoted"] = True
    with pytest.raises(ValidationError, match="exactly one"):
        B3Protocol.model_validate(payload)

    payload = json.loads(
        Path("research/configs/b3_domain_and_candidate_signals.v1.json").read_text()
    )
    payload["b4_gate"]["macro_f1_minimum"] = 0.60
    with pytest.raises(ValidationError):
        B3Protocol.model_validate(payload)

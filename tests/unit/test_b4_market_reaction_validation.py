import json
from datetime import UTC, date, datetime
from pathlib import Path

from jobs.b4_market_reaction_validation import build_b4_audit
from research.evaluation.b4_market_reaction_validation import (
    SufficiencyObservation,
    align_reaction_window,
    assess_data_sufficiency,
    event_family_id,
    load_protocol,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "research/configs/b4_market_reaction_validation.v1.json"


def test_protocol_freezes_task_and_model_boundaries() -> None:
    protocol = load_protocol(CONFIG)

    assert protocol.primary_target.name == "next_eligible_session_signed_abnormal_return"
    assert protocol.primary_target.continuous is True
    assert protocol.primary_target.causal_claim is False
    assert protocol.sentiment.status == "ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED"
    assert protocol.sentiment.market_reaction_is_sentiment_ground_truth is False
    assert protocol.representation.retrain_encoder is False
    assert protocol.chronological_evaluation.random_split_allowed is False
    assert [item.family for item in protocol.candidate_models] == ["Ridge", "Ridge", "Ridge"]


def test_alignment_handles_preopen_intraday_after_close_weekend_and_unknown_time() -> None:
    protocol = load_protocol(CONFIG)
    sessions = [date(2024, 12, 27), date(2024, 12, 30), date(2024, 12, 31)]

    preopen = align_reaction_window(
        datetime(2024, 12, 30, 0, 0, tzinfo=UTC),
        sessions,
        protocol,
        timestamp_basis="OBSERVED_OFFSET",
    )
    intraday = align_reaction_window(
        datetime(2024, 12, 30, 2, 0, tzinfo=UTC),
        sessions,
        protocol,
        timestamp_basis="OBSERVED_OFFSET",
    )
    after_close = align_reaction_window(
        datetime(2024, 12, 30, 6, 0, tzinfo=UTC),
        sessions,
        protocol,
        timestamp_basis="OBSERVED_OFFSET",
    )
    weekend = align_reaction_window(
        datetime(2024, 12, 29, 4, 0, tzinfo=UTC),
        sessions,
        protocol,
        timestamp_basis="OBSERVED_OFFSET",
    )
    unknown = align_reaction_window(
        datetime(2024, 12, 30, 8, 0),
        sessions,
        protocol,
        timestamp_basis="UNKNOWN",
    )

    assert (preopen.anchor_session, preopen.reaction_session) == (
        date(2024, 12, 27),
        date(2024, 12, 30),
    )
    assert intraday.status == "ABSTAIN_INTRADAY_PRICE_UNAVAILABLE"
    assert (after_close.anchor_session, after_close.reaction_session) == (
        date(2024, 12, 30),
        date(2024, 12, 31),
    )
    assert (weekend.anchor_session, weekend.reaction_session) == (
        date(2024, 12, 27),
        date(2024, 12, 30),
    )
    assert unknown.status == "ABSTAIN_TIMESTAMP"


def test_event_family_normalization_is_deterministic() -> None:
    first = event_family_id("2330", "董事會  決議", date(2024, 12, 30))
    second = event_family_id("2330", "董事會 決議", date(2024, 12, 30))

    assert first == second
    assert len(first) == 64


def test_data_sufficiency_failure_has_explicit_abstention() -> None:
    protocol = load_protocol(CONFIG)
    result = assess_data_sufficiency(
        SufficiencyObservation(
            usable_event_windows=3,
            unique_tickers=1,
            calendar_years=2,
            outer_folds=1,
            minimum_events_in_any_evaluation_fold=2,
            reliable_timestamp_ratio=1.0,
            market_match_ratio=1.0,
            cross_source_dedup_coverage=1.0,
        ),
        protocol.data_sufficiency_gate,
    )

    assert result["passed"] is False
    assert result["maturity"] == "ABSTAIN_INSUFFICIENT_MARKET_REACTION_DATA"
    assert result["failed_checks"] == [
        "usable_event_windows",
        "unique_tickers",
        "calendar_years",
        "outer_folds",
        "events_per_evaluation_fold",
    ]


def test_bounded_audit_never_emits_licensed_subject_text(tmp_path: Path) -> None:
    b2 = tmp_path / "b2.json"
    m8 = tmp_path / "m8.json"
    market = tmp_path / "market.json"
    twmd_2018 = tmp_path / "twmd-2018.json"
    twmd_2024 = tmp_path / "twmd-2024.json"
    b2.write_text(json.dumps({"record_count": 6021}), encoding="utf-8")
    m8.write_text(json.dumps({"deduplicated_event_count": 108}), encoding="utf-8")
    market.write_text(
        json.dumps(
            {
                "sha256": "a" * 64,
                "benchmark_rows": [
                    {"date": value, "price": 100 + index}
                    for index, value in enumerate(
                        ["2018-12-28", "2019-01-02", "2024-12-30", "2024-12-31"]
                    )
                ],
                "stock_rows": [
                    {"ticker": "2330", "trading_date": value, "adjusted_close": 200 + index}
                    for index, value in enumerate(
                        ["2018-12-28", "2019-01-02", "2024-12-30", "2024-12-31"]
                    )
                ],
            }
        ),
        encoding="utf-8",
    )
    twmd_2018.write_text(
        json.dumps(
            {
                "data": [
                    {
                        "ticker": "2330",
                        "event_date": "2018-12-28",
                        "event_time": "18:00:00",
                        "subject": "PRIVATE LICENSED SUBJECT A",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    twmd_2024.write_text(
        json.dumps(
            {
                "data": [
                    {
                        "ticker": "2330",
                        "event_date": "2024-12-30",
                        "event_time": "18:00:00",
                        "subject": "PRIVATE LICENSED SUBJECT B",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = build_b4_audit(
        config_path=CONFIG,
        b2_manifest_path=b2,
        m8_report_path=m8,
        market_dataset_path=market,
        twmd_files=(twmd_2018, twmd_2024),
    )
    serialized = json.dumps(result)

    assert result["maturity"] == "ABSTAIN_INSUFFICIENT_MARKET_REACTION_DATA"
    assert "PRIVATE LICENSED SUBJECT" not in serialized
    assert result["boundaries"]["model_trained"] is False
    assert result["boundaries"]["market_reaction_is_sentiment_ground_truth"] is False

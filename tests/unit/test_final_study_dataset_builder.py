from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from pipelines.features.final_study_builder import build_final_study_dataset
from pipelines.features.risk_builder import load_risk_feature_config
from research.evaluation.final_study_feature_audit import (
    assess_concentration,
    audit_final_study_dataset,
    load_coverage_audit_config,
)
from research.planning.final_study_protocol import (
    HistoricalMarketDataset,
    OuterEvaluation,
    OuterFold,
    load_final_study_config,
    validate_outer_rows,
)

PROTOCOL_PATH = Path("research/configs/final_volatility_surprise_study.v1.json")
FEATURE_CONFIG_PATH = Path("research/configs/risk_features.v1.json")
COVERAGE_CONFIG_PATH = Path(
    "research/configs/final_study_coverage_bias_audit.v1.json"
)


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _dates() -> list[date]:
    start = date(2020, 1, 1)
    return [start + timedelta(days=index) for index in range(120)]


def _market_dataset() -> dict[str, object]:
    dates = _dates()
    config = {
        "schema_version": "risk-market-dataset-config-v1",
        "dataset_version": "risk-market-dataset-v1",
        "market_timezone": "Asia/Taipei",
        "stock_source": "yahoo",
        "stock_source_terms_url": "https://example.test/yahoo",
        "benchmark_dataset_id": "TaiwanStockTotalReturnIndex",
        "benchmark_id": "TAIEX",
        "benchmark_source": "FinMind",
        "benchmark_source_terms_url": "https://example.test/finmind",
        "snapshot_start": dates[0].isoformat(),
        "train_start": dates[35].isoformat(),
        "train_end": dates[60].isoformat(),
        "validation_start": dates[61].isoformat(),
        "validation_end": dates[80].isoformat(),
        "test_start": dates[81].isoformat(),
        "test_end": dates[-1].isoformat(),
        "minimum_warmup_sessions": 1,
        "minimum_train_sessions": 1,
        "minimum_validation_sessions": 1,
        "minimum_test_sessions": 1,
        "maximum_missing_session_ratio": 0.1,
        "universe": [
            {"ticker": "2330", "provider_symbol": "2330.TW", "name": "台積電"}
        ],
    }
    stock_rows = []
    benchmark_rows = []
    for index, session in enumerate(dates):
        close = Decimal(100 + index) + Decimal(index % 5) / Decimal(10)
        stock_rows.append(
            {
                "ticker": "2330",
                "trading_date": session.isoformat(),
                "split": None,
                "open": format(close - Decimal("0.2"), "f"),
                "high": format(close + Decimal("1"), "f"),
                "low": format(close - Decimal("1"), "f"),
                "close": format(close, "f"),
                "adjusted_close": format(close, "f"),
                "volume": 1000 + index * 13 + (index % 7) * 19,
                "source": "yahoo",
            }
        )
        benchmark_rows.append(
            {
                "date": session.isoformat(),
                "price": str(1000 + index * 2 + index % 3),
                "stock_id": "TAIEX",
            }
        )
    content: dict[str, object] = {
        "schema_version": "risk-market-dataset-v1",
        "config": config,
        "benchmark_snapshot_sha256": "b" * 64,
        "benchmark_rows": benchmark_rows,
        "stock_rows": stock_rows,
        "sealed_test_outcomes_inspected": False,
        "risk_labels_generated": False,
        "models_trained": False,
    }
    return {**content, "sha256": _hash(content)}


def _protocol(market: dict[str, object]):
    dates = _dates()
    base = load_final_study_config(PROTOCOL_PATH)
    history = HistoricalMarketDataset(
        schema_version="risk-market-dataset-v1",
        sha256=str(market["sha256"]),
        observed_start=dates[0],
        observed_end=dates[-1],
        stock_row_count=len(market["stock_rows"]),
        benchmark_row_count=len(market["benchmark_rows"]),
        ticker_count=1,
        use_previously_inspected_periods_as_historical_outer_folds=True,
        claim_as_new_sealed_test=False,
    )
    outer = OuterEvaluation(
        method="expanding_window_rolling_origin",
        random_split_allowed=False,
        purge_incomplete_or_overlapping_target=True,
        folds=(
            OuterFold(
                name="one",
                train_start=dates[35],
                train_end=dates[49],
                evaluation_start=dates[50],
                evaluation_end=dates[59],
            ),
            OuterFold(
                name="two",
                train_start=dates[35],
                train_end=dates[59],
                evaluation_start=dates[60],
                evaluation_end=dates[69],
            ),
            OuterFold(
                name="three",
                train_start=dates[35],
                train_end=dates[69],
                evaluation_start=dates[70],
                evaluation_end=dates[89],
            ),
        ),
    )
    return base.model_copy(
        update={"historical_market_dataset": history, "outer_evaluation": outer}
    )


def _rehash(market: dict[str, object]) -> None:
    content = {key: value for key, value in market.items() if key != "sha256"}
    market["sha256"] = _hash(content)


def _row(dataset: dict[str, object], session: date) -> dict[str, object]:
    return next(
        row for row in dataset["rows"] if row["feature_session"] == session.isoformat()
    )


def test_f2_dataset_is_continuous_deterministic_and_raw_free() -> None:
    market = _market_dataset()
    protocol = _protocol(market)
    features = load_risk_feature_config(FEATURE_CONFIG_PATH)

    first, report = build_final_study_dataset(protocol, features, market)
    second, second_report = build_final_study_dataset(protocol, features, market)

    assert first == second
    assert report == second_report
    assert first["schema_version"] == "final-volatility-surprise-dataset-v1"
    assert first["binary_labels_materialized"] is False
    assert first["preprocessing_fitted"] is False
    assert first["models_trained"] is False
    assert report["candidate_row_count"] == 55
    assert report["eligible_row_count"] == 54
    assert report["excluded_row_counts"] == {"target_session_after_study_end": 1}
    assert report["raw_rows_in_report"] is False
    assert report["systematic_missing_stock_sessions"] == []
    assert report["data_quality_warnings"] == []
    assert all("risk_label" not in row["target"] for row in first["rows"])
    assert all("target" not in row["features"] for row in first["rows"])


def test_mutating_t_plus_one_changes_target_but_not_t_feature_hash() -> None:
    dates = _dates()
    feature_session = dates[50]
    target_session = dates[51]
    original_market = _market_dataset()
    original, _ = build_final_study_dataset(
        _protocol(original_market),
        load_risk_feature_config(FEATURE_CONFIG_PATH),
        original_market,
    )
    mutated_market = deepcopy(original_market)
    target_bar = next(
        row
        for row in mutated_market["stock_rows"]
        if row["trading_date"] == target_session.isoformat()
    )
    target_bar["adjusted_close"] = str(Decimal(str(target_bar["adjusted_close"])) * 2)
    _rehash(mutated_market)
    mutated, _ = build_final_study_dataset(
        _protocol(mutated_market),
        load_risk_feature_config(FEATURE_CONFIG_PATH),
        mutated_market,
    )

    before = _row(original, feature_session)
    after = _row(mutated, feature_session)
    assert before["feature_values_sha256"] == after["feature_values_sha256"]
    assert before["target"]["primary"] != after["target"]["primary"]


def test_f2_rows_pass_the_frozen_outer_isolation_guard() -> None:
    market = _market_dataset()
    protocol = _protocol(market)
    dataset, _ = build_final_study_dataset(
        protocol,
        load_risk_feature_config(FEATURE_CONFIG_PATH),
        market,
    )
    fold = protocol.outer_evaluation.folds[1]
    training = [
        row
        for row in dataset["rows"]
        if fold.train_start
        <= date.fromisoformat(str(row["feature_session"]))
        <= fold.train_end
        and date.fromisoformat(str(row["target_session"])) < fold.evaluation_start
    ]
    evaluation = [
        row
        for row in dataset["rows"]
        if fold.evaluation_start
        <= date.fromisoformat(str(row["feature_session"]))
        <= fold.evaluation_end
    ]

    validate_outer_rows(protocol, fold, training, evaluation)


def test_f2_refuses_market_data_outside_frozen_lineage() -> None:
    market = _market_dataset()
    protocol = _protocol(market)
    market["sha256"] = "f" * 64

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        build_final_study_dataset(
            protocol,
            load_risk_feature_config(FEATURE_CONFIG_PATH),
            market,
        )


def test_f2_excludes_and_counts_near_zero_target_denominators() -> None:
    market = _market_dataset()
    for row in market["stock_rows"]:
        row.update(
            {
                "open": "100",
                "high": "101",
                "low": "99",
                "close": "100",
                "adjusted_close": "100",
            }
        )
    _rehash(market)

    dataset, report = build_final_study_dataset(
        _protocol(market),
        load_risk_feature_config(FEATURE_CONFIG_PATH),
        market,
    )

    assert dataset["rows"] == []
    assert report["passed"] is False
    assert report["excluded_row_counts"] == {
        "near_zero_or_non_finite_trailing_volatility": 54,
        "target_session_after_study_end": 1,
    }


def test_f3_audits_target_features_and_all_coverage_axes() -> None:
    market = _market_dataset()
    protocol = _protocol(market)
    feature_config = load_risk_feature_config(FEATURE_CONFIG_PATH)
    dataset, _ = build_final_study_dataset(protocol, feature_config, market)
    dataset = json.loads(json.dumps(dataset, ensure_ascii=False, sort_keys=True))
    audit_config = load_coverage_audit_config(COVERAGE_CONFIG_PATH)

    report = audit_final_study_dataset(
        audit_config,
        protocol,
        feature_config,
        market,
        dataset,
    )

    assert report["passed"] is True
    assert report["row_contract_audit"]["row_count"] == 54
    assert report["row_contract_audit"]["target_feature_overlap_count"] == 0
    assert set(report["feature_availability"]) == set(feature_config.feature_names)
    coverage = report["coverage_bias_audit"]
    assert set(coverage["group_tables"]) == {
        "ticker",
        "calendar_year",
        "outer_fold",
        "volatility_regime",
    }
    assert coverage["missing_at_random_claimed"] is False


def test_f3_concentration_rule_requires_predeclared_absolute_and_ratio_gates() -> None:
    config = load_coverage_audit_config(COVERAGE_CONFIG_PATH)
    groups = {
        "ordinary": {
            "candidate_row_count": 1000,
            "excluded_row_count": 100,
            "eligible_row_count": 900,
            "exclusion_rate": 0.1,
        },
        "concentrated": {
            "candidate_row_count": 1000,
            "excluded_row_count": 400,
            "eligible_row_count": 600,
            "exclusion_rate": 0.4,
        },
    }

    findings = assess_concentration(config, "calendar_year", groups)

    assert [finding["group"] for finding in findings] == ["concentrated"]

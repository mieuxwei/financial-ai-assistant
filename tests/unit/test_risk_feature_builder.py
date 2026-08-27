import hashlib
import json
import math
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipelines.features.risk_builder import (
    FEATURE_NAMES,
    RiskFeatureConfig,
    build_risk_feature_dataset,
    write_immutable_json,
)
from research.risk_labels.protocol import RiskLabelConfig, build_risk_label_dataset


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _dates() -> list[date]:
    start = date(2020, 1, 1)
    return [start + timedelta(days=index) for index in range(70)]


def _market_dataset() -> dict[str, object]:
    dates = _dates()
    market_config = {
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
        "train_end": dates[49].isoformat(),
        "validation_start": dates[50].isoformat(),
        "validation_end": dates[59].isoformat(),
        "test_start": dates[60].isoformat(),
        "test_end": dates[69].isoformat(),
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
    for index, trading_date in enumerate(dates):
        close = Decimal(100 + index) + Decimal(index % 3) / Decimal(10)
        stock_rows.append(
            {
                "ticker": "2330",
                "trading_date": trading_date.isoformat(),
                "split": None,
                "open": format(close - Decimal("0.2"), "f"),
                "high": format(close + Decimal("1"), "f"),
                "low": format(close - Decimal("1"), "f"),
                "close": format(close, "f"),
                "adjusted_close": format(close, "f"),
                "volume": 1000 + index * 11 + (index % 4) * 17,
                "source": "yahoo",
            }
        )
        benchmark_rows.append(
            {
                "date": trading_date.isoformat(),
                "price": str(1000 + index * 2 + index % 5),
                "stock_id": "TAIEX",
            }
        )
    content: dict[str, object] = {
        "schema_version": "risk-market-dataset-v1",
        "config": market_config,
        "benchmark_snapshot_sha256": "b" * 64,
        "benchmark_rows": benchmark_rows,
        "stock_rows": stock_rows,
        "sealed_test_outcomes_inspected": False,
        "risk_labels_generated": False,
        "models_trained": False,
    }
    return {**content, "sha256": _hash(content)}


def _label_config() -> RiskLabelConfig:
    return RiskLabelConfig.model_validate(
        {
            "schema_version": "next-session-volatility-risk-config-v1",
            "protocol_version": "next-session-volatility-risk-v1",
            "market_timezone": "Asia/Taipei",
            "information_cutoff": "13:30:00",
            "primary_outcome": "next_normalized_abs_log_return",
            "trailing_volatility_sessions": 20,
            "trailing_volatility_ddof": 0,
            "threshold_fit_split": "train",
            "threshold_quantile": "0.8",
            "quantile_method": "linear",
            "label_comparison": "greater_than_or_equal",
            "high_risk_label": "HIGH_RISK",
            "normal_label": "NORMAL",
            "materialized_splits": ["train", "validation"],
            "minimum_training_rows": 10,
            "minimum_training_rows_per_ticker": 10,
            "minimum_validation_rows_per_ticker": 5,
            "secondary_outcomes": [
                "next_abs_log_return",
                "next_high_low_log_range",
                "next_parkinson_volatility",
            ],
        }
    )


def _feature_config(**overrides: object) -> RiskFeatureConfig:
    values: dict[str, object] = {
        "schema_version": "risk-feature-config-v1",
        "pipeline_version": "risk-features-v1",
        "market_timezone": "Asia/Taipei",
        "information_cutoff": "13:30:00",
        "materialized_splits": ["train", "validation"],
        "required_consecutive_sessions": 35,
        "return_windows": [1, 5, 10, 20],
        "moving_average_windows": [5, 20],
        "volume_zscore_window": 20,
        "volatility_windows": [5, 20],
        "atr_window": 14,
        "parkinson_window": 5,
        "rsi_window": 14,
        "macd_fast_span": 12,
        "macd_slow_span": 26,
        "macd_signal_span": 9,
        "benchmark_return_windows": [1, 20],
        "benchmark_volatility_window": 20,
        "benchmark_drawdown_window": 20,
        "minimum_training_rows_per_ticker": 10,
        "minimum_validation_rows_per_ticker": 5,
        "feature_names": list(FEATURE_NAMES),
    }
    values.update(overrides)
    return RiskFeatureConfig.model_validate(values)


def _labels(market: dict[str, object]) -> dict[str, object]:
    dataset, _, _ = build_risk_label_dataset(_label_config(), market)
    return dataset


def _row(dataset: dict[str, object], feature_session: date) -> dict[str, object]:
    return next(
        row
        for row in dataset["rows"]
        if row["feature_session"] == feature_session.isoformat()
    )


def _rehash_market(market: dict[str, object]) -> None:
    content = {key: value for key, value in market.items() if key != "sha256"}
    market["sha256"] = _hash(content)


def test_feature_dataset_has_fixed_complete_contract_and_no_test_rows() -> None:
    market = _market_dataset()
    dataset, report = build_risk_feature_dataset(_feature_config(), market, _labels(market))

    assert dataset["materialized_splits"] == ["train", "validation"]
    assert dataset["sealed_test_features_materialized"] is False
    assert dataset["preprocessing_fitted"] is False
    assert {row["split"] for row in dataset["rows"]} == {"train", "validation"}
    assert all(tuple(row["features"]) == FEATURE_NAMES for row in dataset["rows"])
    assert all(
        all(value is not None for value in row["features"].values())
        for row in dataset["rows"]
    )
    assert all("continuous_risk_outcome" not in row["features"] for row in dataset["rows"])
    assert report["feature_count"] == 23
    assert report["validation_label_distribution_inspected"] is False


def test_feature_formulas_use_only_current_and_trailing_market_state() -> None:
    dates = _dates()
    market = _market_dataset()
    dataset, _ = build_risk_feature_dataset(_feature_config(), market, _labels(market))
    row = _row(dataset, dates[40])
    stock_rows = market["stock_rows"]
    benchmark_rows = market["benchmark_rows"]
    stock_return = math.log(
        float(stock_rows[40]["adjusted_close"]) / float(stock_rows[39]["adjusted_close"])
    )
    benchmark_return = math.log(
        float(benchmark_rows[40]["price"]) / float(benchmark_rows[39]["price"])
    )

    assert row["features"]["return_log_1"] == pytest.approx(stock_return, abs=1e-12)
    assert row["features"]["benchmark_return_log_1"] == pytest.approx(
        benchmark_return,
        abs=1e-12,
    )
    assert row["features"]["stock_minus_benchmark_return_log_1"] == pytest.approx(
        stock_return - benchmark_return,
        abs=1e-12,
    )
    assert row["features"]["zero_volume_flag"] == 0


def test_mutating_stock_target_changes_target_not_same_day_features() -> None:
    dates = _dates()
    feature_session = dates[52]
    target_session = dates[53]
    original_market = _market_dataset()
    original, _ = build_risk_feature_dataset(
        _feature_config(), original_market, _labels(original_market)
    )
    mutated_market = deepcopy(original_market)
    target = next(
        row
        for row in mutated_market["stock_rows"]
        if row["trading_date"] == target_session.isoformat()
    )
    target.update(
        {
            "open": "240",
            "high": "260",
            "low": "230",
            "close": "250",
            "adjusted_close": "250",
        }
    )
    _rehash_market(mutated_market)
    mutated, _ = build_risk_feature_dataset(
        _feature_config(), mutated_market, _labels(mutated_market)
    )

    before = _row(original, feature_session)
    after = _row(mutated, feature_session)
    assert before["features"] == after["features"]
    assert before["feature_values_sha256"] == after["feature_values_sha256"]
    assert before["target"]["continuous_risk_outcome"] != after["target"][
        "continuous_risk_outcome"
    ]
    assert after["target"]["risk_label"] == "HIGH_RISK"


def test_mutating_next_benchmark_value_does_not_change_same_day_features() -> None:
    dates = _dates()
    feature_session = dates[52]
    target_session = dates[53]
    original_market = _market_dataset()
    original, _ = build_risk_feature_dataset(
        _feature_config(), original_market, _labels(original_market)
    )
    mutated_market = deepcopy(original_market)
    target = next(
        row
        for row in mutated_market["benchmark_rows"]
        if row["date"] == target_session.isoformat()
    )
    target["price"] = "9999"
    _rehash_market(mutated_market)
    mutated, _ = build_risk_feature_dataset(
        _feature_config(), mutated_market, _labels(mutated_market)
    )

    assert _row(original, feature_session)["features"] == _row(
        mutated, feature_session
    )["features"]


def test_tampered_label_dataset_is_rejected() -> None:
    market = _market_dataset()
    labels = _labels(market)
    original = labels["rows"][0]["risk_label"]
    labels["rows"][0]["risk_label"] = (
        "HIGH_RISK" if original == "NORMAL" else "NORMAL"
    )

    with pytest.raises(ValueError, match="risk-label dataset SHA-256 mismatch"):
        build_risk_feature_dataset(_feature_config(), market, labels)


def test_config_forbids_sealed_test_features() -> None:
    with pytest.raises(ValidationError):
        _feature_config(materialized_splits=["train", "test"])


def test_feature_output_is_immutable(tmp_path: Path) -> None:
    output = tmp_path / "risk-features.json"
    write_immutable_json(output, {"version": 1})
    write_immutable_json(output, {"version": 1})

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_immutable_json(output, {"version": 2})

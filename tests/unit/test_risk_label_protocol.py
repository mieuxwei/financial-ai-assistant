import hashlib
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from research.risk_labels.protocol import (
    RiskLabelConfig,
    build_risk_label_dataset,
    linear_quantile,
    write_immutable_json,
)


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _risk_config(**overrides: object) -> RiskLabelConfig:
    values: dict[str, object] = {
            "schema_version": "next-session-volatility-risk-config-v1",
            "protocol_version": "next-session-volatility-risk-v1",
            "market_timezone": "Asia/Taipei",
            "information_cutoff": "13:30:00",
            "primary_outcome": "next_normalized_abs_log_return",
            "trailing_volatility_sessions": 2,
            "trailing_volatility_ddof": 0,
            "threshold_fit_split": "train",
            "threshold_quantile": "0.5",
            "quantile_method": "linear",
            "label_comparison": "greater_than_or_equal",
            "high_risk_label": "HIGH_RISK",
            "normal_label": "NORMAL",
            "materialized_splits": ["train", "validation"],
            "minimum_training_rows": 3,
            "minimum_training_rows_per_ticker": 3,
            "minimum_validation_rows_per_ticker": 2,
            "secondary_outcomes": [
                "next_abs_log_return",
                "next_high_low_log_range",
                "next_parkinson_volatility",
            ],
    }
    values.update(overrides)
    return RiskLabelConfig.model_validate(values)


def _market_dataset() -> dict[str, object]:
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
        "snapshot_start": "2020-01-01",
        "train_start": "2020-01-03",
        "train_end": "2020-01-06",
        "validation_start": "2020-01-07",
        "validation_end": "2020-01-09",
        "test_start": "2020-01-10",
        "test_end": "2020-01-12",
        "minimum_warmup_sessions": 1,
        "minimum_train_sessions": 1,
        "minimum_validation_sessions": 1,
        "minimum_test_sessions": 1,
        "maximum_missing_session_ratio": 0.1,
        "universe": [
            {"ticker": "2330", "provider_symbol": "2330.TW", "name": "台積電"}
        ],
    }
    closes = ["100", "101", "99", "103", "102", "106", "105", "107", "104", "108", "106", "109"]
    stock_rows = []
    for day, close in enumerate(closes, start=1):
        close_value = Decimal(close)
        stock_rows.append(
            {
                "ticker": "2330",
                "trading_date": f"2020-01-{day:02d}",
                "split": None,
                "open": format(close_value - Decimal("0.5"), "f"),
                "high": format(close_value + Decimal("1"), "f"),
                "low": format(close_value - Decimal("1"), "f"),
                "close": close,
                "adjusted_close": close,
                "volume": 1000 + day,
                "source": "yahoo",
            }
        )
    content: dict[str, object] = {
        "schema_version": "risk-market-dataset-v1",
        "config": market_config,
        "benchmark_snapshot_sha256": "b" * 64,
        "benchmark_rows": [
            {"date": f"2020-01-{day:02d}", "price": str(1000 + day), "stock_id": "TAIEX"}
            for day in range(1, 13)
        ],
        "stock_rows": stock_rows,
        "sealed_test_outcomes_inspected": False,
        "risk_labels_generated": False,
        "models_trained": False,
    }
    return {**content, "sha256": _hash(content)}


def _row(dataset: dict[str, object], feature_session: str) -> dict[str, object]:
    return next(row for row in dataset["rows"] if row["feature_session"] == feature_session)


def _rehash_market_dataset(dataset: dict[str, object]) -> None:
    content = {key: value for key, value in dataset.items() if key != "sha256"}
    dataset["sha256"] = _hash(content)


def test_linear_quantile_is_deterministic() -> None:
    assert linear_quantile(
        [Decimal("1"), Decimal("3"), Decimal("5"), Decimal("7")],
        Decimal("0.5"),
    ) == Decimal("4.000000000000")


def test_threshold_is_train_only_and_test_is_not_materialized() -> None:
    dataset, threshold, report = build_risk_label_dataset(
        _risk_config(),
        _market_dataset(),
    )

    assert threshold["fit_split"] == "train"
    assert threshold["validation_rows_used"] == 0
    assert threshold["sealed_test_rows_used"] == 0
    assert {row["split"] for row in dataset["rows"]} == {"train", "validation"}
    assert not any(row["feature_session"] == "2020-01-06" for row in dataset["rows"])
    assert report["sealed_test_rows_materialized"] is False
    assert report["validation_label_distribution_inspected"] is False
    assert "validation_label_counts" not in report


def test_config_forbids_sealed_test_materialization() -> None:
    with pytest.raises(ValidationError):
        _risk_config(materialized_splits=["train", "test"])


def test_mutating_target_changes_outcome_not_feature_state_or_threshold() -> None:
    original_market = _market_dataset()
    original, original_threshold, _ = build_risk_label_dataset(
        _risk_config(),
        original_market,
    )
    mutated_market = deepcopy(original_market)
    target = next(
        row for row in mutated_market["stock_rows"] if row["trading_date"] == "2020-01-08"
    )
    target.update(
        {
            "open": "190",
            "high": "210",
            "low": "185",
            "close": "200",
            "adjusted_close": "200",
        }
    )
    _rehash_market_dataset(mutated_market)
    mutated, mutated_threshold, _ = build_risk_label_dataset(
        _risk_config(),
        mutated_market,
    )

    before = _row(original, "2020-01-07")
    after = _row(mutated, "2020-01-07")
    assert before["feature_state_sha256"] == after["feature_state_sha256"]
    assert before["continuous_risk_outcome"] != after["continuous_risk_outcome"]
    assert before["risk_label"] == "NORMAL"
    assert after["risk_label"] == "HIGH_RISK"
    assert original_threshold["threshold"] == mutated_threshold["threshold"]
    assert original_threshold["training_row_count"] == mutated_threshold["training_row_count"]


def test_missing_next_exchange_session_is_not_replaced_by_later_bar() -> None:
    market = _market_dataset()
    market["stock_rows"] = [
        row for row in market["stock_rows"] if row["trading_date"] != "2020-01-09"
    ]
    _rehash_market_dataset(market)

    dataset, _, report = build_risk_label_dataset(
        _risk_config(minimum_validation_rows_per_ticker=1),
        market,
    )

    assert not any(row["feature_session"] == "2020-01-08" for row in dataset["rows"])
    assert report["excluded_row_counts"]["missing_consecutive_market_bar"] > 0


def test_market_dataset_hash_is_verified() -> None:
    market = _market_dataset()
    market["stock_rows"][0]["close"] = "999"

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        build_risk_label_dataset(_risk_config(), market)


def test_risk_label_output_is_immutable(tmp_path: Path) -> None:
    output = tmp_path / "risk-labels.json"
    write_immutable_json(output, {"version": 1})
    write_immutable_json(output, {"version": 1})

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_immutable_json(output, {"version": 2})

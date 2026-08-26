import hashlib
import json
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from pipelines.market_data.risk_dataset import (
    RiskMarketDatasetConfig,
    build_risk_market_dataset,
    write_immutable_json,
)
from pipelines.market_data.types import MarketBar


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _config(**overrides: object) -> RiskMarketDatasetConfig:
    values: dict[str, object] = {
        "schema_version": "risk-market-dataset-config-v1",
        "dataset_version": "risk-market-dataset-v1",
        "market_timezone": "Asia/Taipei",
        "stock_source": "yahoo",
        "stock_source_terms_url": "https://example.test/yahoo-terms",
        "benchmark_dataset_id": "TaiwanStockTotalReturnIndex",
        "benchmark_id": "TAIEX",
        "benchmark_source": "FinMind",
        "benchmark_source_terms_url": "https://example.test/finmind-terms",
        "snapshot_start": "2020-01-01",
        "train_start": "2020-01-02",
        "train_end": "2020-01-03",
        "validation_start": "2020-01-04",
        "validation_end": "2020-01-04",
        "test_start": "2020-01-05",
        "test_end": "2020-01-05",
        "minimum_warmup_sessions": 1,
        "minimum_train_sessions": 2,
        "minimum_validation_sessions": 1,
        "minimum_test_sessions": 1,
        "maximum_missing_session_ratio": 0,
        "universe": [
            {"ticker": "2330", "provider_symbol": "2330.TW", "name": "台積電"}
        ],
    }
    values.update(overrides)
    return RiskMarketDatasetConfig.model_validate(values)


def _benchmark() -> dict[str, object]:
    content: dict[str, object] = {
        "schema_version": "finmind-taiex-total-return-v1",
        "endpoint": "https://example.test",
        "dataset_id": "TaiwanStockTotalReturnIndex",
        "benchmark_id": "TAIEX",
        "start_date": "2020-01-01",
        "end_date": "2020-01-05",
        "rows": [
            {"date": f"2020-01-0{day}", "price": str(100 + day), "stock_id": "TAIEX"}
            for day in range(1, 6)
        ],
        "raw_content_stored": False,
    }
    return {**content, "sha256": _canonical_hash(content)}


def _bars(*, omit: date | None = None) -> list[MarketBar]:
    return [
        MarketBar(
            ticker="2330",
            trading_date=date(2020, 1, day),
            open=Decimal("100"),
            high=Decimal("103"),
            low=Decimal("99"),
            close=Decimal("102"),
            adjusted_close=Decimal("101.5"),
            volume=1000,
            source="yahoo",
        )
        for day in range(1, 6)
        if date(2020, 1, day) != omit
    ]


def test_config_rejects_overlapping_temporal_splits() -> None:
    with pytest.raises(ValidationError, match="ordered and disjoint"):
        _config(validation_start="2020-01-03")


def test_dataset_audit_passes_without_labels_or_modeling() -> None:
    dataset, report = build_risk_market_dataset(_config(), _bars(), _benchmark())

    assert report["passed"] is True
    assert report["fatal_issues"] == []
    assert report["dataset_sha256"] == dataset["sha256"]
    assert report["benchmark_split_session_counts"] == {
        "test": 1,
        "train": 2,
        "validation": 1,
        "warmup": 1,
    }
    assert report["sealed_test_outcomes_inspected"] is False
    assert report["risk_labels_generated"] is False
    assert report["models_trained"] is False
    assert report["manual_labels_used"] is False


def test_dataset_audit_fails_when_a_required_session_is_missing() -> None:
    _, report = build_risk_market_dataset(
        _config(),
        _bars(omit=date(2020, 1, 4)),
        _benchmark(),
    )

    assert report["passed"] is False
    assert report["ticker_reports"][0]["missing_session_counts"]["validation"] == 1
    assert any("missing-session ratio" in issue for issue in report["fatal_issues"])


def test_dataset_rejects_tampered_benchmark_snapshot() -> None:
    benchmark = _benchmark()
    benchmark["rows"][0]["price"] = "999"

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        build_risk_market_dataset(_config(), _bars(), benchmark)


def test_immutable_writer_refuses_different_content(tmp_path) -> None:
    path = tmp_path / "snapshot.json"
    write_immutable_json(path, {"version": 1})
    write_immutable_json(path, {"version": 1})

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_immutable_json(path, {"version": 2})

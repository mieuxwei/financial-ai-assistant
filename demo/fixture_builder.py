from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.schemas.research import VolatilitySurprisePredictionResponse
from demo.contracts import ControlledDashboardFixture, FeatureContext
from pipelines.features.risk_builder import FEATURE_NAMES
from pipelines.intelligence.financial_nlp import (
    assemble_intelligence_item,
    load_financial_nlp_intelligence_config,
)
from pipelines.news.types import NewsItem, TickerMatch
from research.modeling.final_research_model import predict_from_artifact

DEFAULT_ARTIFACT = Path(".tools/models/f7-final-ridge-research-v1/model.json")
DEFAULT_INTELLIGENCE_CONFIG = Path(
    "research/configs/financial_nlp_intelligence.v1.json"
)
TAIPEI = ZoneInfo("Asia/Taipei")


def build_controlled_fixture(
    artifact_path: Path = DEFAULT_ARTIFACT,
    intelligence_config_path: Path = DEFAULT_INTELLIGENCE_CONFIG,
) -> ControlledDashboardFixture:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    intelligence_config = load_financial_nlp_intelligence_config(
        intelligence_config_path
    )
    features = _synthetic_features()
    request = {
        "ticker": "2330",
        "as_of_date": date(2026, 8, 28),
        "information_cutoff": datetime(2026, 8, 28, 13, 30, tzinfo=TAIPEI),
        "features": features,
    }
    prediction = predict_from_artifact(
        artifact,
        request["ticker"],
        request["as_of_date"].isoformat(),
        request["information_cutoff"].isoformat(),
        features,
    )
    prediction_response = VolatilitySurprisePredictionResponse(
        schema_version="volatility-surprise-prediction-response-v1",
        **prediction,
        target_version=str(artifact["target_version"]),
        artifact_sha256=str(artifact["sha256"]),
        claim_boundary={
            "research_signal_only": True,
            "prospective_accuracy": False,
            "price_direction_forecast": False,
            "investment_advice": False,
            "guaranteed_future_volatility": False,
        },
    )
    intelligence_items = [
        assemble_intelligence_item(
            intelligence_config,
            _chinese_item(),
            [TickerMatch("2330", 1.0, "controlled_fixture")],
        ),
        assemble_intelligence_item(
            intelligence_config,
            _english_item(),
            [TickerMatch("2330", 0.9, "controlled_fixture")],
        ),
    ]
    return ControlledDashboardFixture(
        schema_version="controlled-dashboard-fixture-v1",
        fixture_id="synthetic-2330-f11-v1",
        controlled_synthetic_data=True,
        actual_market_observation=False,
        performance_evaluation=False,
        private_or_user_data=False,
        company_display_name="2330 台積電（受控示範）",
        data_notice=(
            "所有數值與情報均為受控合成展示，不是 2330 的真實即時資料或投資訊號。"
        ),
        feature_context=FeatureContext(
            return_20_session_pct=8.0,
            volatility_20_session_pct=1.1,
            volume_zscore_20=0.8,
            benchmark_return_20_session_pct=4.0,
            benchmark_drawdown_20_session_pct=-2.0,
        ),
        prediction_request=request,
        prediction_response=prediction_response,
        intelligence_version=intelligence_config.intelligence_version,
        intelligence_items=intelligence_items,
    )


def _synthetic_features() -> dict[str, float]:
    values = {
        "return_log_1": 0.008,
        "return_log_5": 0.025,
        "return_log_10": 0.04,
        "return_log_20": 0.08,
        "overnight_gap_log_1": 0.002,
        "close_ma_deviation_5": 0.01,
        "close_ma_deviation_20": 0.04,
        "volume_log_change_1p_1": 0.1,
        "volume_zscore_20": 0.8,
        "zero_volume_flag": 0.0,
        "volatility_log_return_5": 0.012,
        "volatility_log_return_20": 0.011,
        "high_low_log_range_1": 0.018,
        "atr_14_normalized": 0.016,
        "parkinson_mean_5": 0.01,
        "rsi_14": 58.0,
        "macd_12_26_normalized": 0.005,
        "macd_signal_9_normalized": 0.003,
        "benchmark_return_log_1": 0.003,
        "benchmark_return_log_20": 0.04,
        "benchmark_volatility_log_return_20": 0.009,
        "stock_minus_benchmark_return_log_1": 0.005,
        "benchmark_drawdown_20": -0.02,
    }
    if set(values) != set(FEATURE_NAMES):
        raise ValueError("controlled fixture feature contract drifted")
    return values


def _chinese_item() -> NewsItem:
    return NewsItem(
        title="【受控範例】公司公告月營收成長並取得重大訂單",
        published_at=datetime(2026, 8, 28, 9, 0, tzinfo=TAIPEI),
        source="controlled_demo",
        source_type="controlled_official_announcement",
        url="https://example.invalid/controlled-zh",
        summary="合成公告摘要，只用於展示中文 abstention 與事件代理。",
        language="zh-TW",
        external_id="controlled-f11-zh-1",
        explicit_tickers=("2330",),
        metadata={
            "company_name": "受控範例公司",
            "clause": "DEMO",
            "fact_date": "2026-08-28",
        },
    )


def _english_item() -> NewsItem:
    return NewsItem(
        title="Controlled example: Company reports quarterly results",
        published_at=datetime(2026, 8, 27, 16, 0, tzinfo=TAIPEI),
        source="controlled_demo",
        source_type="controlled_news",
        url="https://example.invalid/controlled-en",
        summary="Synthetic English excerpt for an eligible but unscored FinBERT route.",
        language="en",
        external_id="controlled-f11-en-1",
        explicit_tickers=("2330",),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the deterministic F11 fixture")
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument(
        "--intelligence-config", type=Path, default=DEFAULT_INTELLIGENCE_CONFIG
    )
    args = parser.parse_args()
    fixture = build_controlled_fixture(args.artifact, args.intelligence_config)
    print(json.dumps(fixture.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

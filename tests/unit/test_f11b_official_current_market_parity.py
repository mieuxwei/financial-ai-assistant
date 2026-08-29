import json
from pathlib import Path

from pipelines.features.risk_builder import FEATURE_NAMES
from research.evaluation.f11b_official_current_market_parity import (
    compare_numeric_rows,
    normalize_twse_month,
    parse_twse_current,
    roc_date,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "research/configs/f11b_official_current_market_parity.v1.json"


def load_config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_roc_date_supports_compact_and_slash_formats() -> None:
    assert roc_date("1150828") == "2026-08-28"
    assert roc_date("113/01/02") == "2024-01-02"


def test_twse_month_parser_normalizes_shares_and_allows_note_column() -> None:
    payload = {
        "stat": "OK",
        "fields": [
            "日期",
            "成交股數",
            "成交金額",
            "開盤價",
            "最高價",
            "最低價",
            "收盤價",
            "漲跌價差",
            "成交筆數",
            "註記",
        ],
        "data": [
            ["113/01/02", "1,234", "10,000", "10", "11", "9", "10.5", "+0.5", "8", ""],
        ],
    }
    assert normalize_twse_month(payload, "2330") == [
        {
            "ticker": "2330",
            "trading_date": "2024-01-02",
            "open": "10",
            "high": "11",
            "low": "9",
            "close": "10.5",
            "volume": 1234,
            "source": "TWSE_STOCK_DAY",
        }
    ]


def test_twse_current_parser_does_not_guess_missing_rows() -> None:
    parsed = parse_twse_current(
        [
            {
                "Date": "1150828",
                "Code": "0050",
                "Name": "元大台灣50",
                "TradeVolume": "1,000",
                "OpeningPrice": "50",
                "HighestPrice": "51",
                "LowestPrice": "49",
                "ClosingPrice": "50.5",
            },
            {"Code": "BROKEN"},
        ]
    )
    assert set(parsed) == {"0050"}
    assert parsed["0050"]["trading_date"] == "2026-08-28"


def test_numeric_comparison_reports_session_and_unit_mismatch() -> None:
    historical = [
        {
            "trading_date": "2024-01-02",
            "open": "10.000000",
            "high": "11.000000",
            "low": "9.000000",
            "close": "10.500000",
            "volume": 1000,
        }
    ]
    official = [
        {
            "trading_date": "2024-01-02",
            "open": "10",
            "high": "11",
            "low": "9",
            "close": "10.6",
            "volume": 1,
        }
    ]
    result = compare_numeric_rows(historical, official)
    assert result["aligned_row_count"] == 1
    assert result["fields"]["open"]["exact_match_count"] == 1
    assert result["fields"]["close"]["exact_match_count"] == 0
    assert result["fields"]["volume"]["max_absolute_difference"] == "999"


def test_decision_is_adjusted_parity_unresolved_and_not_ready() -> None:
    config = load_config()
    assert (
        config["decision_code"]
        == "OFFICIAL_OHLCV_AVAILABLE_BUT_ADJUSTED_PARITY_UNRESOLVED"
    )
    assert config["adjusted_price_parity"]["training_equivalent"] is False
    assert config["next_action"] == "NOT_READY_FOR_F11B_2"
    assert config["f11b_2_started"] is False


def test_universe_is_frozen_and_all_current_rows_are_fresh_twse() -> None:
    config = load_config()
    expected = ["0050", "1301", "1303", "2308", "2317", "2330", "2412", "2454", "2881", "2882"]
    assert [row["ticker"] for row in config["universe"]] == expected
    assert {row["market"] for row in config["universe"]} == {"TWSE"}
    assert all(row["covered_sessions"] == 35 for row in config["coverage"]["per_ticker"])
    assert all(row["stale"] is False for row in config["coverage"]["per_ticker"])


def test_feature_contract_is_exact_and_only_five_features_pass() -> None:
    config = load_config()
    rows = config["feature_parity"]["rows"]
    assert [row["feature_name"] for row in rows] == list(FEATURE_NAMES)
    assert len(rows) == 23
    assert sum(row["status"] == "PASS" for row in rows) == 5
    assert config["feature_parity"]["overall_status"] == "FAIL"


def test_benchmark_identity_and_gate_count_are_not_overstated() -> None:
    config = load_config()
    assert config["benchmark"]["historical_identity"] == "TAIEX total-return index"
    assert config["benchmark"]["exact_match_count"] == 20
    assert config["benchmark"]["status"] == "PASS"
    assert config["gate_pass_count"] == 6
    assert config["gate_total"] == 9
    gates = {row["gate"]: row["status"] for row in config["gate_decisions"]}
    assert gates["exact_23_feature_parity"] == "FAIL"
    assert gates["training_inference_feature_parity"] == "FAIL"
    assert gates["end_to_end_validation"] == "NOT_RUN"


def test_safety_contract_forbids_silent_fallback_and_mutation() -> None:
    config = load_config()
    assert config["freshness"]["gap_positive"].startswith("ABSTAIN_CURRENT_DATA")
    assert config["missing_data"]["carry_forward"] is False
    assert config["missing_data"]["imputation"] is False
    assert config["lineage"]["raw_payload_tracked"] is False
    assert config["model_modified"] is False
    assert config["gas_modified"] is False
    assert config["deployment_performed"] is False


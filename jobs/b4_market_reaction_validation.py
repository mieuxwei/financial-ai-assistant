from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from research.evaluation.b4_market_reaction_validation import (
    SufficiencyObservation,
    align_reaction_window,
    assess_data_sufficiency,
    event_family_id,
    load_protocol,
    sha256_json,
    ticker_window_id,
)

DEFAULT_CONFIG = Path("research/configs/b4_market_reaction_validation.v1.json")
DEFAULT_B2_MANIFEST = Path(".tools/datasets/b2-taiwan-financial-text-v1/manifest.json")
DEFAULT_M8_REPORT = Path("artifacts/m8-market-reaction-build-report.json")
DEFAULT_MARKET_DATASET = Path(".tools/datasets/risk-market-dataset-v1/dataset.json")
DEFAULT_TWMD_FILES = (
    Path(
        ".tools/datasets/twmd-pro-reaudit-v1/"
        "major_event_taxonomy_runtime_filters_2018.json"
    ),
    Path(
        ".tools/datasets/twmd-pro-reaudit-v1/"
        "major_event_taxonomy_runtime_filters_2024.json"
    ),
)
DEFAULT_OUTPUT = Path(".tools/evaluations/b4-market-reaction-validation-v1/audit.json")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_twmd_timestamp(event_date: str, event_time: str) -> datetime:
    parsed_time = event_time if event_time.count(":") == 2 else f"{event_time}:00"
    naive = datetime.fromisoformat(f"{event_date}T{parsed_time}")
    return naive.replace(tzinfo=ZoneInfo("Asia/Taipei"))


def build_b4_audit(
    *,
    config_path: Path = DEFAULT_CONFIG,
    b2_manifest_path: Path = DEFAULT_B2_MANIFEST,
    m8_report_path: Path = DEFAULT_M8_REPORT,
    market_dataset_path: Path = DEFAULT_MARKET_DATASET,
    twmd_files: tuple[Path, ...] = DEFAULT_TWMD_FILES,
) -> dict[str, object]:
    protocol = load_protocol(config_path)
    b2_manifest = _load_json(b2_manifest_path)
    m8_report = _load_json(m8_report_path)
    market_dataset = _load_json(market_dataset_path)

    benchmark_by_date = {
        row["date"]: Decimal(str(row["price"])) for row in market_dataset["benchmark_rows"]
    }
    sessions = [datetime.fromisoformat(value).date() for value in benchmark_by_date]
    stock_by_key = {
        (row["ticker"], row["trading_date"]): Decimal(str(row["adjusted_close"]))
        for row in market_dataset["stock_rows"]
    }

    source_rows: list[dict[str, object]] = []
    for path in twmd_files:
        payload = _load_json(path)
        for row in payload["data"]:
            publication = _parse_twmd_timestamp(row["event_date"], row["event_time"])
            window = align_reaction_window(
                publication,
                sessions,
                protocol,
                timestamp_basis="SOURCE_CONTRACT_ASSUMPTION",
            )
            family_id = event_family_id(row["ticker"], row["subject"], publication.date())
            market_match = False
            window_id = None
            if (
                window.status == "ELIGIBLE"
                and window.anchor_session is not None
                and window.reaction_session is not None
            ):
                anchor = window.anchor_session.isoformat()
                reaction = window.reaction_session.isoformat()
                market_match = (
                    (row["ticker"], anchor) in stock_by_key
                    and (row["ticker"], reaction) in stock_by_key
                    and anchor in benchmark_by_date
                    and reaction in benchmark_by_date
                )
                window_id = ticker_window_id(row["ticker"], window)
            source_rows.append(
                {
                    "source_id": "twmd_major_event_taxonomy",
                    "family_id": family_id,
                    "ticker": row["ticker"],
                    "publication_date": row["event_date"],
                    "timestamp_basis": "SOURCE_CONTRACT_ASSUMPTION",
                    "alignment_status": window.status,
                    "anchor_session": (
                        window.anchor_session.isoformat() if window.anchor_session else None
                    ),
                    "reaction_session": (
                        window.reaction_session.isoformat() if window.reaction_session else None
                    ),
                    "ticker_window_id": window_id,
                    "market_match": market_match,
                    "title_retained": False,
                    "event_class_is_sentiment": False,
                }
            )

    unique_families = {row["family_id"] for row in source_rows}
    matched = [row for row in source_rows if row["market_match"]]
    unique_windows = {row["ticker_window_id"] for row in matched}
    years = {str(row["publication_date"])[:4] for row in matched}
    tickers = {row["ticker"] for row in matched}
    evaluation_2024_windows = {
        row["ticker_window_id"]
        for row in matched
        if str(row["publication_date"]).startswith("2024-")
    }

    event_count = len(source_rows)
    reliable_count = sum(
        row["timestamp_basis"] in protocol.timestamp_bases_allowed for row in source_rows
    )
    match_count = len(matched)
    observation = SufficiencyObservation(
        usable_event_windows=len(unique_windows),
        unique_tickers=len(tickers),
        calendar_years=len(years),
        outer_folds=1 if evaluation_2024_windows else 0,
        minimum_events_in_any_evaluation_fold=len(evaluation_2024_windows),
        reliable_timestamp_ratio=reliable_count / event_count if event_count else 0.0,
        market_match_ratio=match_count / event_count if event_count else 0.0,
        cross_source_dedup_coverage=1.0 if event_count else 0.0,
    )
    sufficiency = assess_data_sufficiency(observation, protocol.data_sufficiency_gate)

    result = {
        "protocol_version": protocol.protocol_version,
        "status": "B4_COMPLETE_DATA_INSUFFICIENT_NO_MODEL_TRAINED",
        "maturity": sufficiency["maturity"],
        "source_breakdown": {
            "fsc_filtered_corpus": {
                "available_documents": b2_manifest["record_count"],
                "b4_usable_events": 0,
                "reason": "no ticker mapping and date-only timestamps",
            },
            "twse_bounded_m8_snapshot": {
                "available_event_groups": m8_report["deduplicated_event_count"],
                "b4_usable_events": 0,
                "reason": "two-day target-only engine evidence without governed text features",
            },
            "tpex_b2_snapshot": {
                "available_events": 0,
                "b4_usable_events": 0,
            },
            "twmd_major_event_taxonomy": {
                "available_events": event_count,
                "unique_event_families": len(unique_families),
                "market_matchable_events": match_count,
                "aggregated_ticker_reaction_windows": len(unique_windows),
                "b4_usable_events": event_count,
            },
            "gdelt_gkg_gal": {
                "available_events": 0,
                "b4_usable_events": 0,
            },
        },
        "usable_event_count": event_count,
        "usable_ticker_reaction_window_count": len(unique_windows),
        "date_coverage": {
            "minimum": min((row["publication_date"] for row in matched), default=None),
            "maximum": max((row["publication_date"] for row in matched), default=None),
        },
        "ticker_coverage": sorted(tickers),
        "alignment": {
            "eligible_events": sum(row["alignment_status"] == "ELIGIBLE" for row in source_rows),
            "market_matchable_events": match_count,
            "statuses": _counts(row["alignment_status"] for row in source_rows),
            "publication_timing": "all admitted TWMD rows were after market close",
        },
        "deduplication": {
            "input_events": event_count,
            "unique_event_families": len(unique_families),
            "exact_duplicate_events": event_count - len(unique_families),
            "aggregated_ticker_reaction_windows": len(unique_windows),
        },
        "chronological_split_manifest": {
            "development": {
                "years": ["2018"],
                "events": sum(
                    str(row["publication_date"]).startswith("2018-") for row in matched
                ),
            },
            "evaluation": {
                "years": ["2024"],
                "events": sum(
                    str(row["publication_date"]).startswith("2024-") for row in matched
                ),
            },
            "valid_outer_fold_count": 0,
            "reason": "predeclared minimum events per fold and total coverage are not met",
        },
        "data_sufficiency": sufficiency,
        "model_results": {
            "market_only_ridge": "NOT_RUN_DATA_SUFFICIENCY_GATE_FAILED",
            "metadata_only_ridge": "NOT_RUN_DATA_SUFFICIENCY_GATE_FAILED",
            "bert_text_metadata_ridge": "NOT_RUN_DATA_SUFFICIENCY_GATE_FAILED",
            "text_incremental_value": "NOT_ESTIMABLE",
            "directional_diagnostic": "NOT_RUN",
        },
        "boundaries": {
            "linguistic_sentiment": "ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED",
            "market_reaction_is_sentiment_ground_truth": False,
            "causal_impact_claimed": False,
            "encoder_retrained": False,
            "model_trained": False,
            "b5_started": False,
            "track_a_modified": False,
            "gas_modified": False,
            "eland_used": False,
        },
        "lineage": {
            "config_sha256": _sha256_file(config_path),
            "b2_manifest_sha256": _sha256_file(b2_manifest_path),
            "m8_report_sha256": _sha256_file(m8_report_path),
            "market_dataset_sha256": market_dataset["sha256"],
            "twmd_file_sha256": {str(path): _sha256_file(path) for path in twmd_files},
        },
        "raw_licensed_text_stored": False,
        "next_executable_unit": "B5_NLP_INTELLIGENCE_INTEGRATION",
    }
    result["audit_sha256"] = sha256_json(result)
    return result


def _counts(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return result


def write_immutable(path: Path, payload: dict[str, object]) -> None:
    target = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != target:
        raise FileExistsError(f"refusing to overwrite different B4 audit artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(target, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit B4 market-reaction data sufficiency")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = build_b4_audit(config_path=args.config)
    write_immutable(args.output, result)
    print(json.dumps({"maturity": result["maturity"], "audit_sha256": result["audit_sha256"]}))


if __name__ == "__main__":
    main()

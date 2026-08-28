from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

AUDIT_VERSION = "finmind-news-longitudinal-audit-v1"
DEFAULT_CONFIG = Path("research/configs/finmind_news_longitudinal_audit.v1.json")
DEFAULT_OUTPUT = Path("artifacts/finmind-news-longitudinal-audit.json")
DEFAULT_CACHE = Path(".tools/datasets/finmind-news-longitudinal-audit")
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


class ContentThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_title_characters: int = Field(ge=1, le=500)
    minimum_combined_characters: int = Field(ge=1, le=2_000)
    minimum_usable_content_rate: float = Field(ge=0, le=1)
    minimum_nonempty_description_rate: float = Field(ge=0, le=1)
    maximum_exact_link_duplicate_rate: float = Field(ge=0, le=1)


class FinMindLongitudinalAuditConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    audit_version: Literal["finmind-news-longitudinal-audit-v1"] = AUDIT_VERSION
    endpoint: HttpUrl
    dataset_id: Literal["TaiwanStockNews"]
    tickers: list[str] = Field(min_length=1, max_length=100)
    start_year: int = Field(ge=2000, le=2100)
    end_year: int = Field(ge=2000, le=2100)
    sampling_mode: Literal["quarterly_weekday_sample", "daily_census"]
    sample_months: list[int] = Field(default_factory=list, max_length=12)
    sample_weekday: int = Field(default=2, ge=0, le=6)
    sample_day_on_or_after: int = Field(default=14, ge=1, le=28)
    maximum_requests: int = Field(ge=1, le=100_000)
    max_workers: int = Field(ge=1, le=16)
    timeout_seconds: float = Field(gt=0, le=120)
    max_response_bytes: int = Field(gt=0, le=10_000_000)
    required_fields: list[str] = Field(min_length=1)
    optional_fields: list[str] = Field(default_factory=list)
    token_environment_variable: Literal["FINMIND_API_TOKEN"]
    raw_retention: Literal["ignored_local_cache_only"]
    timestamp_semantics_documented: Literal[False] = False
    timezone_documented: Literal[False] = False
    thresholds: ContentThresholds

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("tickers must be unique")
        if any(not re.fullmatch(r"[0-9A-Z]{2,12}", ticker) for ticker in value):
            raise ValueError("ticker format is invalid")
        return value

    @field_validator("sample_months", "required_fields", "optional_fields")
    @classmethod
    def validate_unique_values(cls, value: list[object]) -> list[object]:
        if len(value) != len(set(value)):
            raise ValueError("configured values must be unique")
        return value

    @model_validator(mode="after")
    def validate_period_and_sampling(self) -> FinMindLongitudinalAuditConfig:
        if self.end_year < self.start_year:
            raise ValueError("end_year must not precede start_year")
        if self.end_year >= 2025:
            raise ValueError("this audit must remain before the 2025 sealed-test boundary")
        if self.sampling_mode == "quarterly_weekday_sample":
            invalid_month = any(month < 1 or month > 12 for month in self.sample_months)
            if not self.sample_months or invalid_month:
                raise ValueError("quarterly sample requires valid sample_months")
        elif self.sample_months:
            raise ValueError("daily census must not define sample_months")
        overlap = set(self.required_fields) & set(self.optional_fields)
        if overlap:
            raise ValueError(f"required_fields and optional_fields overlap: {sorted(overlap)}")
        if len(build_request_plan(self)) > self.maximum_requests:
            raise ValueError("request plan exceeds maximum_requests")
        return self


@dataclass(frozen=True)
class RequestUnit:
    ticker: str
    requested_date: date


@dataclass
class RowObservation:
    ticker: str
    year: int
    request_nonempty: bool = False
    record_count: int = 0
    valid_timestamp_count: int = 0
    requested_day_match_count: int = 0
    timezone_aware_count: int = 0
    midnight_count: int = 0
    nonempty_title_count: int = 0
    nonempty_description_count: int = 0
    usable_content_count: int = 0
    title_lengths: list[int] = field(default_factory=list)
    combined_lengths: list[int] = field(default_factory=list)
    link_hashes: list[str] = field(default_factory=list)
    title_hashes: list[str] = field(default_factory=list)
    schemas: list[tuple[str, ...]] = field(default_factory=list)


def load_config(path: Path) -> FinMindLongitudinalAuditConfig:
    return FinMindLongitudinalAuditConfig.model_validate_json(path.read_text(encoding="utf-8"))


def build_request_plan(config: FinMindLongitudinalAuditConfig) -> list[RequestUnit]:
    dates: list[date] = []
    if config.sampling_mode == "daily_census":
        current = date(config.start_year, 1, 1)
        end = date(config.end_year, 12, 31)
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)
    else:
        for year in range(config.start_year, config.end_year + 1):
            for month in config.sample_months:
                current = date(year, month, config.sample_day_on_or_after)
                while current.weekday() != config.sample_weekday:
                    current += timedelta(days=1)
                dates.append(current)
    return [
        RequestUnit(ticker=ticker, requested_date=day)
        for ticker in config.tickers
        for day in dates
    ]


def run_longitudinal_audit(
    config: FinMindLongitudinalAuditConfig,
    *,
    cache_dir: Path = DEFAULT_CACHE,
    output_path: Path = DEFAULT_OUTPUT,
    retrieved_at: datetime | None = None,
) -> dict[str, object]:
    observed_at = retrieved_at or datetime.now(UTC)
    if observed_at.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")
    cache_dir.mkdir(parents=True, exist_ok=True)
    plan = build_request_plan(config)
    token = os.environ.get(config.token_environment_variable, "").strip()
    headers = {"User-Agent": "financial-ai-assistant/0.1 longitudinal-news-audit"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    results: list[dict[str, object]] = []
    with httpx.Client(
        timeout=httpx.Timeout(config.timeout_seconds, connect=10.0),
        follow_redirects=True,
        headers=headers,
    ) as client:
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            futures = {
                executor.submit(_load_or_fetch, config, unit, cache_dir, client): unit
                for unit in plan
            }
            for index, future in enumerate(as_completed(futures), start=1):
                unit = futures[future]
                try:
                    results.append(future.result())
                except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as error:
                    status = (
                        error.response.status_code
                        if isinstance(error, httpx.HTTPStatusError)
                        else None
                    )
                    results.append(
                        {
                            "ticker": unit.ticker,
                            "requested_date": unit.requested_date.isoformat(),
                            "http_status": status,
                            "cache_hit": False,
                            "error_code": type(error).__name__,
                        }
                    )
                if index % 25 == 0 or index == len(plan):
                    print(f"FinMind audit progress: {index}/{len(plan)}", flush=True)

    report = build_report(config, results, observed_at=observed_at, cache_dir=cache_dir)
    write_report(output_path, report)
    return report


def _load_or_fetch(
    config: FinMindLongitudinalAuditConfig,
    unit: RequestUnit,
    cache_dir: Path,
    client: httpx.Client,
) -> dict[str, object]:
    path = cache_dir / unit.ticker / f"{unit.requested_date.isoformat()}.json"
    cache_hit = path.exists()
    if cache_hit:
        payload_bytes = path.read_bytes()
        http_status = 200
    else:
        response = client.get(
            str(config.endpoint),
            params={
                "dataset": config.dataset_id,
                "data_id": unit.ticker,
                "start_date": unit.requested_date.isoformat(),
            },
        )
        http_status = response.status_code
        response.raise_for_status()
        payload_bytes = response.content
        if len(payload_bytes) > config.max_response_bytes:
            raise ValueError("FinMind news response exceeded max_response_bytes")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload_bytes)
    if len(payload_bytes) > config.max_response_bytes:
        raise ValueError("cached FinMind news response exceeded max_response_bytes")
    payload = json.loads(payload_bytes)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TypeError("FinMind response did not contain a data list")
    if any(not isinstance(row, dict) for row in payload["data"]):
        raise TypeError("FinMind news rows must be objects")
    return {
        "ticker": unit.ticker,
        "requested_date": unit.requested_date.isoformat(),
        "http_status": http_status,
        "cache_hit": cache_hit,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "rows": payload["data"],
    }


def build_report(
    config: FinMindLongitudinalAuditConfig,
    results: list[dict[str, object]],
    *,
    observed_at: datetime,
    cache_dir: Path,
) -> dict[str, object]:
    grouped: dict[tuple[str, int], list[RowObservation]] = defaultdict(list)
    global_observations: list[RowObservation] = []
    error_count = 0
    cache_hits = 0
    payload_hashes = []
    for result in results:
        if "rows" not in result:
            error_count += 1
            continue
        try:
            observation = analyze_rows(
                ticker=str(result["ticker"]),
                requested_date=date.fromisoformat(str(result["requested_date"])),
                rows=result["rows"],  # type: ignore[arg-type]
                config=config,
            )
        except (KeyError, TypeError, ValueError):
            error_count += 1
            continue
        grouped[(observation.ticker, observation.year)].append(observation)
        global_observations.append(observation)
        cache_hits += bool(result.get("cache_hit"))
        payload_hashes.append(str(result["payload_sha256"]))

    summary = _summarize(global_observations, config)
    by_ticker_year = []
    for (ticker, year), observations in sorted(grouped.items()):
        values = _summarize(observations, config)
        by_ticker_year.append({"ticker": ticker, "year": year, **values})

    record_count = int(summary["record_count"])
    usable_rate = float(summary["usable_content_rate"])
    duplicate_rate = float(summary["exact_link_duplicate_rate"])
    timestamp_valid_rate = float(summary["valid_timestamp_rate"])
    timestamp_day_match_rate = float(summary["requested_day_match_rate"])
    title_level_gate = (
        record_count > 0
        and usable_rate >= config.thresholds.minimum_usable_content_rate
    )
    rich_text_gate = (
        title_level_gate
        and float(summary["nonempty_description_rate"])
        >= config.thresholds.minimum_nonempty_description_rate
    )
    duplicate_gate = duplicate_rate <= config.thresholds.maximum_exact_link_duplicate_rate
    timestamp_format_gate = timestamp_valid_rate >= 0.99 and timestamp_day_match_rate >= 0.99
    complete = len(results) == len(build_request_plan(config)) and error_count == 0
    lineage_payload = "\n".join(sorted(payload_hashes)).encode()
    decision_reasons = [
        "sample_not_full_census" if config.sampling_mode != "daily_census" else None,
        "timestamp_semantics_not_documented",
        "timezone_not_documented",
        "publisher_content_rights_not_inherited",
        None if title_level_gate else "title_level_content_gate_failed",
        None if rich_text_gate else "rich_text_content_gate_failed",
        (
            None
            if duplicate_rate <= config.thresholds.maximum_exact_link_duplicate_rate
            else "duplicate_rate_exceeded"
        ),
    ]
    return {
        "audit_version": config.audit_version,
        "generated_at": observed_at.astimezone(UTC).isoformat(),
        "dataset_id": config.dataset_id,
        "period": {"start_year": config.start_year, "end_year": config.end_year},
        "sealed_test_rows_requested": 0,
        "sampling_mode": config.sampling_mode,
        "ticker_count": len(config.tickers),
        "tickers": config.tickers,
        "planned_request_count": len(build_request_plan(config)),
        "completed_request_count": len(results) - error_count,
        "cache_hit_count": cache_hits,
        "completion_status": "COMPLETE" if complete else "PARTIAL",
        "aggregate": summary,
        "by_ticker_year": by_ticker_year,
        "timestamp_format_gate_passed": timestamp_format_gate,
        "timestamp_semantics_documented": False,
        "timezone_documented": False,
        "title_level_feature_gate_passed": title_level_gate,
        "rich_text_feature_gate_passed": rich_text_gate,
        "deduplication_gate_passed": duplicate_gate,
        "content_sufficiency_gate_passed": rich_text_gate,
        "market_reaction_weak_supervision_decision": "HOLD",
        "decision_reasons": [reason for reason in decision_reasons if reason],
        "request_lineage_sha256": hashlib.sha256(lineage_payload).hexdigest(),
        "local_cache_path": str(cache_dir),
        "raw_content_committed": False,
        "manual_labels_used": False,
        "sentiment_ground_truth": False,
    }


def analyze_rows(
    *,
    ticker: str,
    requested_date: date,
    rows: list[dict[str, object]],
    config: FinMindLongitudinalAuditConfig,
) -> RowObservation:
    observation = RowObservation(
        ticker=ticker, year=requested_date.year, request_nonempty=bool(rows)
    )
    observation.record_count = len(rows)
    for row in rows:
        observation.schemas.append(tuple(sorted(str(key) for key in row)))
        timestamp = _parse_timestamp(row.get("date"))
        if timestamp is not None:
            observation.valid_timestamp_count += 1
            observation.requested_day_match_count += timestamp.date() == requested_date
            observation.timezone_aware_count += timestamp.tzinfo is not None
            observation.midnight_count += timestamp.time().isoformat() == "00:00:00"
        title = _clean_text(row.get("title"))
        description = _clean_text(row.get("description"))
        observation.nonempty_title_count += bool(title)
        observation.nonempty_description_count += bool(description)
        observation.title_lengths.append(len(title))
        combined_length = len(SPACE_RE.sub(" ", f"{title} {description}").strip())
        observation.combined_lengths.append(combined_length)
        usable = (
            len(title) >= config.thresholds.minimum_title_characters
            and combined_length >= config.thresholds.minimum_combined_characters
        )
        observation.usable_content_count += usable
        link = _canonical_link(row.get("link"))
        if link:
            observation.link_hashes.append(hashlib.sha256(link.encode()).hexdigest())
        if title:
            observation.title_hashes.append(hashlib.sha256(title.encode()).hexdigest())
    return observation


def _summarize(
    observations: list[RowObservation], config: FinMindLongitudinalAuditConfig
) -> dict[str, object]:
    records = sum(item.record_count for item in observations)
    links = [value for item in observations for value in item.link_hashes]
    titles = [value for item in observations for value in item.title_hashes]
    link_counts = Counter(links)
    title_counts = Counter(titles)
    title_lengths = [value for item in observations for value in item.title_lengths]
    combined_lengths = [value for item in observations for value in item.combined_lengths]
    schemas = Counter(schema for item in observations for schema in item.schemas)
    return {
        "request_count": len(observations),
        "nonempty_request_count": sum(item.request_nonempty for item in observations),
        "record_count": records,
        "valid_timestamp_rate": _rate(
            sum(item.valid_timestamp_count for item in observations), records
        ),
        "requested_day_match_rate": _rate(
            sum(item.requested_day_match_count for item in observations), records
        ),
        "timezone_aware_timestamp_rate": _rate(
            sum(item.timezone_aware_count for item in observations), records
        ),
        "midnight_timestamp_rate": _rate(
            sum(item.midnight_count for item in observations), records
        ),
        "nonempty_title_rate": _rate(
            sum(item.nonempty_title_count for item in observations), records
        ),
        "nonempty_description_rate": _rate(
            sum(item.nonempty_description_count for item in observations), records
        ),
        "usable_content_rate": _rate(
            sum(item.usable_content_count for item in observations), records
        ),
        "median_title_characters": median(title_lengths) if title_lengths else 0,
        "median_combined_characters": median(combined_lengths) if combined_lengths else 0,
        "p10_combined_characters": _percentile(combined_lengths, 0.10),
        "p90_combined_characters": _percentile(combined_lengths, 0.90),
        "distinct_link_count": len(link_counts),
        "exact_link_duplicate_count": sum(count - 1 for count in link_counts.values()),
        "exact_link_duplicate_rate": _rate(
            sum(count - 1 for count in link_counts.values()), len(links)
        ),
        "exact_title_duplicate_count": sum(count - 1 for count in title_counts.values()),
        "exact_title_duplicate_rate": _rate(
            sum(count - 1 for count in title_counts.values()), len(titles)
        ),
        "schema_variant_count": len(schemas),
        "documented_description_field_observed": any(
            "description" in schema for schema in schemas
        ),
        "content_thresholds": config.thresholds.model_dump(),
    }


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return SPACE_RE.sub(" ", TAG_RE.sub(" ", html.unescape(str(value)))).strip()


def _canonical_link(value: object) -> str:
    if value is None or not str(value).strip():
        return ""
    parts = urlsplit(str(value).strip())
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query)
        if not key.casefold().startswith("utm_")
    ]
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), parts.path, urlencode(query), "")
    )


def _parse_timestamp(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _percentile(values: list[int], quantile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return ordered[index]


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit FinMind news coverage without publishing text"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_longitudinal_audit(
        load_config(args.config), cache_dir=args.cache_dir, output_path=args.output
    )
    print(json.dumps({
        "output": str(args.output),
        "completion_status": report["completion_status"],
        "record_count": report["aggregate"]["record_count"],  # type: ignore[index]
        "market_reaction_weak_supervision_decision": "HOLD",
        "raw_content_committed": False,
    }, ensure_ascii=False))
    return 0 if report["completion_status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())

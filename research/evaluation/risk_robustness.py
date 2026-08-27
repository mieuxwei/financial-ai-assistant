from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import median
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research.modeling.metrics import binary_classification_metrics

CONFIG_VERSION = "risk-robustness-config-v1"
PROTOCOL_VERSION = "risk-robustness-v1"
ANALYSIS_VERSION = "risk-robustness-analysis-v1"
REPORT_VERSION = "m8-risk-robustness-report-v1"
ERROR_TYPES = ("TN", "FP", "FN", "TP")


class RiskRobustnessConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["risk-robustness-config-v1"] = CONFIG_VERSION
    protocol_version: Literal["risk-robustness-v1"] = PROTOCOL_VERSION
    sealed_evaluation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    opening_intent_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    completion_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pretest_feature_dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_threshold: float
    probability_bin_edges: tuple[float, ...] = Field(min_length=3)
    regime_quantiles: tuple[float, float]
    stock_regime_feature: Literal["volatility_log_return_20"]
    market_regime_feature: Literal["benchmark_volatility_log_return_20"]
    minimum_stratum_rows: int = Field(ge=1)
    minimum_stratum_positive_rows: int = Field(ge=1)
    bootstrap_iterations: int = Field(ge=100, le=10000)
    bootstrap_seed: int
    bootstrap_cluster: Literal["feature_session"]
    bootstrap_confidence: float = Field(gt=0.5, lt=1)
    m7_rerun_allowed: Literal[False]
    model_or_threshold_selection_allowed: Literal[False]

    @field_validator("probability_bin_edges")
    @classmethod
    def validate_probability_edges(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if value[0] != 0.0 or value[-1] != 1.0:
            raise ValueError("probability bins must cover [0, 1]")
        if tuple(sorted(set(value))) != value:
            raise ValueError("probability bin edges must be sorted and unique")
        return value

    @model_validator(mode="after")
    def validate_contract(self) -> RiskRobustnessConfig:
        if self.selected_threshold != 0.1:
            raise ValueError("M8 must retain the frozen M7 threshold 0.10")
        if not 0 < self.regime_quantiles[0] < self.regime_quantiles[1] < 1:
            raise ValueError("regime quantiles must be ordered inside (0, 1)")
        return self


def load_risk_robustness_config(path: Path) -> RiskRobustnessConfig:
    return RiskRobustnessConfig.model_validate_json(path.read_text(encoding="utf-8"))


def verify_m7_chain(
    config: RiskRobustnessConfig,
    evaluation: dict[str, object],
    opening_intent: dict[str, object],
    completion: dict[str, object],
    m7_report: dict[str, object],
    pretest_dataset: dict[str, object],
) -> None:
    for name, payload in (
        ("sealed evaluation", evaluation),
        ("opening intent", opening_intent),
        ("completion", completion),
        ("pre-test dataset", pretest_dataset),
    ):
        _verify_hash(payload, name)
    expected = {
        "sealed evaluation": (evaluation["sha256"], config.sealed_evaluation_sha256),
        "opening intent": (opening_intent["sha256"], config.opening_intent_sha256),
        "completion": (completion["sha256"], config.completion_record_sha256),
        "pre-test dataset": (
            pretest_dataset["sha256"],
            config.pretest_feature_dataset_sha256,
        ),
    }
    for name, (actual, frozen) in expected.items():
        if actual != frozen:
            raise ValueError(f"{name} does not match the frozen M8 config")
    if evaluation.get("opening_intent_sha256") != opening_intent["sha256"]:
        raise ValueError("evaluation/opening chain mismatch")
    if completion.get("opening_intent_sha256") != opening_intent["sha256"]:
        raise ValueError("completion/opening chain mismatch")
    if completion.get("sealed_test_evaluation_sha256") != evaluation["sha256"]:
        raise ValueError("completion/evaluation chain mismatch")
    if completion.get("report_sha256") != _hash(m7_report):
        raise ValueError("completion/M7 report chain mismatch")
    for payload in (evaluation, opening_intent, completion):
        if payload.get("evaluation_sequence") != 1:
            raise ValueError("M7 evaluation sequence is not exactly one")
        if payload.get("candidate_manifest_sha256") != config.candidate_manifest_sha256:
            raise ValueError("M7 candidate manifest lineage mismatch")
    if completion.get("repeat_evaluation_allowed") is not False:
        raise ValueError("M7 completion does not permanently refuse repeats")
    if m7_report.get("sealed_test_evaluations") != 1:
        raise ValueError("M7 aggregate report counter is not one")
    if m7_report.get("model_or_threshold_selection_performed") is not False:
        raise ValueError("M7 report indicates forbidden selection")


def analyze_risk_robustness(
    config: RiskRobustnessConfig,
    evaluation: dict[str, object],
    pretest_dataset: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    rows = _verified_evaluation_rows(config, evaluation)
    regime_thresholds = _regime_thresholds(config, pretest_dataset)
    enriched = [_enrich_row(row, config, regime_thresholds) for row in rows]
    y_true = np.asarray([row["actual"] for row in enriched], dtype=np.int8)
    probabilities = np.asarray([row["probability"] for row in enriched], dtype=np.float64)
    main_metrics = binary_classification_metrics(
        y_true, probabilities, config.selected_threshold
    )
    ticker = _stratify(enriched, "ticker", config)
    quarter = _stratify(enriched, "quarter", config)
    stock_regime = _stratify(enriched, "stock_regime", config)
    market_regime = _stratify(enriched, "market_regime", config)
    probability_buckets = _probability_buckets(enriched, config)
    uncertainty = _cluster_bootstrap(enriched, config)
    separation = {
        "overall": _separation_summary(enriched),
        "by_stock_volatility_regime": _separation_by(enriched, "stock_regime"),
        "by_market_volatility_regime": _separation_by(enriched, "market_regime"),
        "by_ticker": _separation_by(enriched, "ticker"),
    }
    errors = {
        "overall_counts": dict(sorted(Counter(row["error_type"] for row in enriched).items())),
        "by_ticker": _error_distribution(enriched, "ticker"),
        "by_quarter": _error_distribution(enriched, "quarter"),
        "by_stock_volatility_regime": _error_distribution(enriched, "stock_regime"),
        "by_market_volatility_regime": _error_distribution(enriched, "market_regime"),
    }
    config_payload = config.model_dump(mode="json")
    content = {
        "schema_version": ANALYSIS_VERSION,
        "protocol_version": config.protocol_version,
        "config": config_payload,
        "config_sha256": _hash(config_payload),
        "sealed_evaluation_sha256": evaluation["sha256"],
        "pretest_feature_dataset_sha256": pretest_dataset["sha256"],
        "row_count": len(enriched),
        "regime_thresholds_fit_source": "pretest_2011_2024_only",
        "regime_thresholds": regime_thresholds,
        "main_metrics": main_metrics,
        "cluster_bootstrap": uncertainty,
        "ticker": ticker,
        "quarter": quarter,
        "stock_volatility_regime": stock_regime,
        "market_volatility_regime": market_regime,
        "probability_buckets": probability_buckets,
        "error_analysis": errors,
        "realized_risk_separation": separation,
        "m7_rerun_performed": False,
        "model_or_threshold_selection_performed": False,
        "rows_persisted": False,
    }
    analysis = {**content, "sha256": _hash(content)}
    report = {
        "schema_version": REPORT_VERSION,
        "passed": True,
        "protocol_version": config.protocol_version,
        "config_sha256": content["config_sha256"],
        "analysis_sha256": analysis["sha256"],
        "sealed_evaluation_sha256": evaluation["sha256"],
        "row_count": len(enriched),
        "main_metrics": main_metrics,
        "cluster_bootstrap": uncertainty,
        "regime_thresholds": regime_thresholds,
        "ticker": ticker,
        "quarter": quarter,
        "stock_volatility_regime": stock_regime,
        "market_volatility_regime": market_regime,
        "probability_buckets": probability_buckets,
        "error_analysis": errors,
        "realized_risk_separation": separation,
        "m7_evaluation_sequence": 1,
        "m7_rerun_performed": False,
        "model_or_threshold_selection_performed": False,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return analysis, report


def _verified_evaluation_rows(
    config: RiskRobustnessConfig,
    evaluation: dict[str, object],
) -> list[dict[str, object]]:
    _verify_hash(evaluation, "sealed evaluation")
    if evaluation["sha256"] != config.sealed_evaluation_sha256:
        raise ValueError("sealed evaluation hash drifted")
    if evaluation.get("evaluation_sequence") != 1:
        raise ValueError("M8 accepts only M7 evaluation sequence one")
    if evaluation.get("model_or_threshold_selection_performed") is not False:
        raise ValueError("M7 evaluation indicates forbidden selection")
    rows = evaluation.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("M7 evaluation rows are missing")
    identities = set()
    output = []
    for row in rows:
        identity = (str(row["ticker"]), str(row["feature_session"]))
        if identity in identities:
            raise ValueError("duplicate M7 evaluation identity")
        identities.add(identity)
        probability = float(row["calibrated_probability"])
        if not 0 <= probability <= 1:
            raise ValueError("invalid calibrated probability")
        expected_label = "HIGH_RISK" if probability >= config.selected_threshold else "NORMAL"
        if row.get("predicted_label") != expected_label:
            raise ValueError("stored M7 prediction differs from frozen threshold")
        output.append(row)
    return sorted(output, key=lambda row: (str(row["feature_session"]), str(row["ticker"])))


def _regime_thresholds(
    config: RiskRobustnessConfig,
    pretest_dataset: dict[str, object],
) -> dict[str, object]:
    _verify_hash(pretest_dataset, "pre-test dataset")
    if pretest_dataset["sha256"] != config.pretest_feature_dataset_sha256:
        raise ValueError("pre-test dataset hash drifted")
    rows = pretest_dataset.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("pre-test rows are missing")
    output = {}
    for name, feature in (
        ("stock_volatility", config.stock_regime_feature),
        ("market_volatility", config.market_regime_feature),
    ):
        values = np.asarray([float(row["features"][feature]) for row in rows])
        quantiles = np.quantile(values, config.regime_quantiles, method="linear")
        output[name] = {
            "feature": feature,
            "low_upper": float(quantiles[0]),
            "middle_upper": float(quantiles[1]),
            "fit_rows": len(rows),
        }
    return output


def _enrich_row(
    row: dict[str, object],
    config: RiskRobustnessConfig,
    thresholds: dict[str, object],
) -> dict[str, object]:
    actual = int(row["target"]["risk_label"] == "HIGH_RISK")
    probability = float(row["calibrated_probability"])
    predicted = int(probability >= config.selected_threshold)
    session = date.fromisoformat(str(row["feature_session"]))
    error_type = ("T" if actual == predicted else "F") + ("P" if predicted else "N")
    return {
        "ticker": str(row["ticker"]),
        "feature_session": session.isoformat(),
        "quarter": f"{session.year}-Q{(session.month - 1) // 3 + 1}",
        "probability": probability,
        "actual": actual,
        "predicted": predicted,
        "error_type": error_type,
        "stock_regime": _regime(
            float(row["features"][config.stock_regime_feature]),
            thresholds["stock_volatility"],
        ),
        "market_regime": _regime(
            float(row["features"][config.market_regime_feature]),
            thresholds["market_volatility"],
        ),
        "continuous_risk_outcome": float(row["target"]["continuous_risk_outcome"]),
        "next_abs_log_return": float(row["target"]["next_abs_log_return"]),
        "next_high_low_log_range": float(row["target"]["next_high_low_log_range"]),
        "next_parkinson_volatility": float(row["target"]["next_parkinson_volatility"]),
    }


def _regime(value: float, thresholds: dict[str, object]) -> str:
    if value <= float(thresholds["low_upper"]):
        return "LOW"
    if value <= float(thresholds["middle_upper"]):
        return "MIDDLE"
    return "HIGH"


def _stratify(
    rows: list[dict[str, object]],
    key: str,
    config: RiskRobustnessConfig,
) -> dict[str, object]:
    groups: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {name: _stratum_metrics(group, config) for name, group in sorted(groups.items())}


def _stratum_metrics(
    rows: list[dict[str, object]],
    config: RiskRobustnessConfig,
) -> dict[str, object]:
    positives = sum(int(row["actual"]) for row in rows)
    base = {
        "row_count": len(rows),
        "high_risk_count": positives,
        "high_risk_prevalence": positives / len(rows),
        "predicted_high_risk_count": sum(int(row["predicted"]) for row in rows),
        "mean_probability": float(np.mean([row["probability"] for row in rows])),
        "error_counts": dict(sorted(Counter(row["error_type"] for row in rows).items())),
    }
    if (
        len(rows) < config.minimum_stratum_rows
        or positives < config.minimum_stratum_positive_rows
        or positives == len(rows)
    ):
        return {**base, "status": "INSUFFICIENT_FOR_FULL_METRICS", "metrics": None}
    y_true = np.asarray([row["actual"] for row in rows], dtype=np.int8)
    probability = np.asarray([row["probability"] for row in rows], dtype=np.float64)
    return {
        **base,
        "status": "OK",
        "metrics": binary_classification_metrics(
            y_true, probability, config.selected_threshold
        ),
    }


def _probability_buckets(
    rows: list[dict[str, object]],
    config: RiskRobustnessConfig,
) -> list[dict[str, object]]:
    output = []
    edges = config.probability_bin_edges
    for index, (lower, upper) in enumerate(zip(edges, edges[1:], strict=False)):
        group = [
            row
            for row in rows
            if lower <= float(row["probability"]) < upper
            or (index == len(edges) - 2 and float(row["probability"]) == upper)
        ]
        count = len(group)
        output.append(
            {
                "lower": lower,
                "upper": upper,
                "row_count": count,
                "mean_probability": (
                    float(np.mean([row["probability"] for row in group])) if count else None
                ),
                "observed_high_risk_rate": (
                    float(np.mean([row["actual"] for row in group])) if count else None
                ),
                "error_counts": (
                    dict(sorted(Counter(row["error_type"] for row in group).items()))
                    if count
                    else {}
                ),
            }
        )
    return output


def _cluster_bootstrap(
    rows: list[dict[str, object]],
    config: RiskRobustnessConfig,
) -> dict[str, object]:
    by_session: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_session[str(row["feature_session"])].append(row)
    sessions = sorted(by_session)
    rng = np.random.default_rng(config.bootstrap_seed)
    samples: defaultdict[str, list[float]] = defaultdict(list)
    for _ in range(config.bootstrap_iterations):
        selected = rng.choice(sessions, size=len(sessions), replace=True)
        sampled = [row for session in selected for row in by_session[str(session)]]
        y_true = np.asarray([row["actual"] for row in sampled], dtype=np.int8)
        probability = np.asarray([row["probability"] for row in sampled], dtype=np.float64)
        if len(np.unique(y_true)) < 2:
            continue
        metrics = binary_classification_metrics(
            y_true, probability, config.selected_threshold
        )
        for name in ("recall_high_risk", "mcc", "pr_auc", "roc_auc", "brier_score"):
            samples[name].append(float(metrics[name]))
    alpha = (1 - config.bootstrap_confidence) / 2
    return {
        "method": "feature_session_cluster_bootstrap",
        "iterations_requested": config.bootstrap_iterations,
        "iterations_valid": min(len(values) for values in samples.values()),
        "cluster_count": len(sessions),
        "confidence": config.bootstrap_confidence,
        "intervals": {
            name: {
                "lower": float(np.quantile(values, alpha)),
                "upper": float(np.quantile(values, 1 - alpha)),
            }
            for name, values in sorted(samples.items())
        },
    }


def _separation_by(
    rows: list[dict[str, object]],
    key: str,
) -> dict[str, object]:
    groups: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {name: _separation_summary(group) for name, group in sorted(groups.items())}


def _separation_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    groups = {
        "NORMAL": [row for row in rows if not row["predicted"]],
        "HIGH_RISK": [row for row in rows if row["predicted"]],
    }
    output = {name: _outcome_summary(group) for name, group in groups.items()}
    normal = output["NORMAL"]
    high = output["HIGH_RISK"]
    output["high_minus_normal"] = {
        name: (
            float(high[name]) - float(normal[name])
            if high[name] is not None and normal[name] is not None
            else None
        )
        for name in (
            "mean_continuous_risk_outcome",
            "median_continuous_risk_outcome",
            "mean_next_abs_log_return",
            "mean_next_high_low_log_range",
            "mean_next_parkinson_volatility",
        )
    }
    return output


def _outcome_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {
            "row_count": 0,
            "mean_continuous_risk_outcome": None,
            "median_continuous_risk_outcome": None,
            "mean_next_abs_log_return": None,
            "mean_next_high_low_log_range": None,
            "mean_next_parkinson_volatility": None,
        }
    return {
        "row_count": len(rows),
        "mean_continuous_risk_outcome": _mean(rows, "continuous_risk_outcome"),
        "median_continuous_risk_outcome": float(
            median(float(row["continuous_risk_outcome"]) for row in rows)
        ),
        "mean_next_abs_log_return": _mean(rows, "next_abs_log_return"),
        "mean_next_high_low_log_range": _mean(rows, "next_high_low_log_range"),
        "mean_next_parkinson_volatility": _mean(rows, "next_parkinson_volatility"),
    }


def _mean(rows: list[dict[str, object]], key: str) -> float:
    return float(np.mean([float(row[key]) for row in rows]))


def _error_distribution(
    rows: list[dict[str, object]],
    key: str,
) -> dict[str, object]:
    groups: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        groups[str(row[key])][str(row["error_type"])] += 1
    return {
        name: {error: counts.get(error, 0) for error in ERROR_TYPES}
        for name, counts in sorted(groups.items())
    }


def _verify_hash(payload: dict[str, object], name: str) -> None:
    expected = payload.get("sha256")
    content = {key: value for key, value in payload.items() if key != "sha256"}
    if not isinstance(expected, str) or _hash(content) != expected:
        raise ValueError(f"{name} SHA-256 mismatch")


def _hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def write_immutable_json(path: Path, payload: dict[str, object]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if path.exists():
        if path.read_bytes() != encoded:
            raise FileExistsError(f"refusing to overwrite a different immutable file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

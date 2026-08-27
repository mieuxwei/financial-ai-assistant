from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from pipelines.features.risk_builder import (
    FEATURE_NAMES,
    RiskFeatureConfig,
    _benchmark_market,
    _calculate_features,
    _stock_market,
    _verify_m2_feature_state,
)
from pipelines.market_data.risk_dataset import RiskMarketDatasetConfig
from research.modeling.baselines import (
    RiskBaselineConfig,
    binary_labels,
    feature_matrix,
    verify_feature_dataset,
)
from research.modeling.metrics import binary_classification_metrics, uniform_calibration_bins
from research.modeling.tree_models import RiskTreeModelConfig
from research.risk_labels.protocol import RiskLabelConfig, build_sealed_test_drafts

CONFIG_VERSION = "risk-sealed-test-config-v1"
PROTOCOL_VERSION = "risk-sealed-test-v1"
EVALUATION_VERSION = "risk-sealed-test-evaluation-v1"
REPORT_VERSION = "m7-risk-sealed-test-report-v1"
EXPECTED_CANDIDATE_MANIFEST_SHA256 = (
    "951a5f627fe2bf67e318cb35e48f76f538aa1931a71c16c6052ada297c641c81"
)


class RiskSealedTestConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["risk-sealed-test-config-v1"] = CONFIG_VERSION
    protocol_version: Literal["risk-sealed-test-v1"] = PROTOCOL_VERSION
    candidate_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    market_dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    threshold_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pretest_feature_dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    label_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tree_model_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_model: Literal["logistic_regression"]
    selected_calibration: Literal["platt"]
    selected_threshold: float
    test_start: date
    test_end: date
    minimum_test_rows: int = Field(ge=1)
    minimum_test_rows_per_ticker: int = Field(ge=1)
    calibration_bins: int = Field(ge=2, le=50)
    evaluation_sequence: Literal[1]
    model_or_threshold_selection_allowed: Literal[False]
    repeat_evaluation_allowed: Literal[False]

    @model_validator(mode="after")
    def validate_frozen_contract(self) -> RiskSealedTestConfig:
        if self.candidate_manifest_sha256 != EXPECTED_CANDIDATE_MANIFEST_SHA256:
            raise ValueError("M7 candidate manifest hash is not the frozen M6 hash")
        if self.selected_threshold != 0.1:
            raise ValueError("M7 threshold must remain frozen at 0.10")
        if self.test_start != date(2025, 1, 1) or self.test_end != date(2026, 8, 26):
            raise ValueError("M7 sealed-test period does not match the frozen M1 split")
        return self


def load_risk_sealed_test_config(path: Path) -> RiskSealedTestConfig:
    return RiskSealedTestConfig.model_validate_json(path.read_text(encoding="utf-8"))


def verify_sealed_test_preflight(
    config: RiskSealedTestConfig,
    candidate_manifest: dict[str, object],
    label_config: RiskLabelConfig,
    feature_config: RiskFeatureConfig,
    baseline_config: RiskBaselineConfig,
    tree_config: RiskTreeModelConfig,
    pretest_feature_dataset: dict[str, object],
) -> None:
    _verify_hash(candidate_manifest, "candidate manifest")
    if candidate_manifest["sha256"] != config.candidate_manifest_sha256:
        raise ValueError("candidate manifest does not match frozen M6 hash")
    if candidate_manifest.get("candidate_recipe_frozen") is not True:
        raise ValueError("candidate recipe is not frozen")
    if candidate_manifest.get("sealed_test_features_or_outcomes_opened") is not False:
        raise ValueError("candidate manifest says sealed test was already opened")
    if candidate_manifest.get("sealed_test_evaluations") != 0:
        raise ValueError("candidate manifest test counter is not zero")
    expected = {
        "selected_model": config.selected_model,
        "selected_calibration": config.selected_calibration,
        "selected_threshold": config.selected_threshold,
    }
    for key, value in expected.items():
        if candidate_manifest.get(key) != value:
            raise ValueError(f"candidate manifest {key} drifted")
    upstream = {
        "label config": (label_config.model_dump(mode="json"), config.label_config_sha256),
        "feature config": (
            feature_config.model_dump(mode="json"),
            config.feature_config_sha256,
        ),
        "baseline config": (
            baseline_config.model_dump(mode="json"),
            config.baseline_config_sha256,
        ),
        "tree config": (tree_config.model_dump(mode="json"), config.tree_model_config_sha256),
    }
    for name, (payload, expected_hash) in upstream.items():
        if _hash(payload) != expected_hash:
            raise ValueError(f"{name} hash drifted")
    verify_feature_dataset(baseline_config, pretest_feature_dataset)
    if pretest_feature_dataset["sha256"] != config.pretest_feature_dataset_sha256:
        raise ValueError("pre-test feature dataset hash drifted")
    if candidate_manifest.get("feature_dataset_sha256") != config.pretest_feature_dataset_sha256:
        raise ValueError("candidate and pre-test dataset lineage differ")


def claim_sealed_test_opening(
    path: Path,
    config: RiskSealedTestConfig,
) -> dict[str, object]:
    if path.exists():
        raise FileExistsError(
            "sealed test opening record already exists; repeat evaluation refused"
        )
    content = {
        "schema_version": "risk-sealed-test-opening-intent-v1",
        "protocol_version": config.protocol_version,
        "evaluation_sequence": config.evaluation_sequence,
        "candidate_manifest_sha256": config.candidate_manifest_sha256,
        "test_start": config.test_start.isoformat(),
        "test_end": config.test_end.isoformat(),
        "authorized_by_user": True,
        "repeat_evaluation_allowed": False,
        "opened_at_utc": datetime.now(UTC).isoformat(),
    }
    payload = {**content, "sha256": _hash(content)}
    write_immutable_json(path, payload)
    return payload


def evaluate_sealed_test(
    config: RiskSealedTestConfig,
    candidate_manifest: dict[str, object],
    market_dataset: dict[str, object],
    threshold_artifact: dict[str, object],
    label_config: RiskLabelConfig,
    feature_config: RiskFeatureConfig,
    baseline_config: RiskBaselineConfig,
    tree_config: RiskTreeModelConfig,
    pretest_feature_dataset: dict[str, object],
    opening_intent: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    verify_sealed_test_preflight(
        config,
        candidate_manifest,
        label_config,
        feature_config,
        baseline_config,
        tree_config,
        pretest_feature_dataset,
    )
    _verify_market_and_threshold(config, market_dataset, threshold_artifact)
    _verify_hash(opening_intent, "opening intent")
    if opening_intent.get("candidate_manifest_sha256") != config.candidate_manifest_sha256:
        raise ValueError("opening intent candidate hash mismatch")

    test_rows, exclusion_counts = _materialize_test_rows(
        config,
        market_dataset,
        threshold_artifact,
        label_config,
        feature_config,
    )
    if len(test_rows) < config.minimum_test_rows:
        raise ValueError("eligible sealed-test rows are below minimum")
    ticker_counts = Counter(str(row["ticker"]) for row in test_rows)
    if any(count < config.minimum_test_rows_per_ticker for count in ticker_counts.values()):
        raise ValueError("a ticker has too few sealed-test rows")

    pretest_rows = list(pretest_feature_dataset["rows"])
    if _hash(pretest_rows) != candidate_manifest["final_fit_rows_sha256"]:
        raise ValueError("final-fit row commitment mismatch")
    x_train = feature_matrix(pretest_rows)
    y_train = binary_labels(pretest_rows, label_config.high_risk_label)
    x_test = feature_matrix(test_rows)
    y_test = binary_labels(test_rows, label_config.high_risk_label)
    raw_probability, reconstructed_state, train_probability = _reconstruct_logistic(
        x_train,
        y_train,
        x_test,
        baseline_config,
    )
    if reconstructed_state != candidate_manifest["final_model_state"]:
        raise ValueError("reconstructed final model state differs from frozen candidate")
    if _hash(reconstructed_state) != candidate_manifest["final_model_state_sha256"]:
        raise ValueError("reconstructed final model state hash mismatch")
    if _hash([float(value) for value in train_probability]) != candidate_manifest[
        "final_training_probability_sha256"
    ]:
        raise ValueError("reconstructed training probability commitment mismatch")

    calibrated_probability = _apply_frozen_platt(
        raw_probability,
        candidate_manifest["final_calibrator"],
    )
    predicted = calibrated_probability >= config.selected_threshold
    evaluated_rows = []
    for row, raw_value, calibrated_value, predicted_value in zip(
        test_rows,
        raw_probability,
        calibrated_probability,
        predicted,
        strict=True,
    ):
        evaluated_rows.append(
            {
                **row,
                "raw_probability": float(raw_value),
                "calibrated_probability": float(calibrated_value),
                "predicted_label": (
                    label_config.high_risk_label
                    if predicted_value
                    else label_config.normal_label
                ),
            }
        )
    evaluation_content = {
        "schema_version": EVALUATION_VERSION,
        "protocol_version": config.protocol_version,
        "candidate_manifest_sha256": config.candidate_manifest_sha256,
        "opening_intent_sha256": opening_intent["sha256"],
        "market_dataset_sha256": market_dataset["sha256"],
        "threshold_artifact_sha256": threshold_artifact["sha256"],
        "test_start": config.test_start.isoformat(),
        "test_end": config.test_end.isoformat(),
        "evaluation_sequence": 1,
        "model_or_threshold_selection_performed": False,
        "rows": evaluated_rows,
    }
    evaluation = {**evaluation_content, "sha256": _hash(evaluation_content)}
    metrics = binary_classification_metrics(
        y_test,
        calibrated_probability,
        config.selected_threshold,
    )
    report = {
        "schema_version": REPORT_VERSION,
        "passed": True,
        "protocol_version": config.protocol_version,
        "evaluation_sequence": 1,
        "candidate_manifest_sha256": config.candidate_manifest_sha256,
        "opening_intent_sha256": opening_intent["sha256"],
        "sealed_test_evaluation_sha256": evaluation["sha256"],
        "market_dataset_sha256": market_dataset["sha256"],
        "threshold_artifact_sha256": threshold_artifact["sha256"],
        "test_period": {
            "start": config.test_start.isoformat(),
            "end": config.test_end.isoformat(),
        },
        "row_count": len(test_rows),
        "ticker_count": len(ticker_counts),
        "ticker_row_counts": dict(sorted(ticker_counts.items())),
        "high_risk_count": int(y_test.sum()),
        "high_risk_prevalence": float(y_test.mean()),
        "selected_model": config.selected_model,
        "selected_calibration": config.selected_calibration,
        "selected_threshold": config.selected_threshold,
        "metrics": metrics,
        "calibration": uniform_calibration_bins(
            y_test,
            calibrated_probability,
            config.calibration_bins,
        ),
        "realized_risk_by_prediction": _realized_risk_summary(evaluated_rows),
        "excluded_row_counts": exclusion_counts,
        "final_model_state_reconstructed": True,
        "model_or_threshold_selection_performed": False,
        "repeat_evaluation_allowed": False,
        "sealed_test_evaluations": 1,
        "raw_rows_in_report": False,
        "contains_secrets": False,
        "contains_private_holdings": False,
    }
    return evaluation, report


def completion_record(
    config: RiskSealedTestConfig,
    opening_intent: dict[str, object],
    evaluation: dict[str, object],
    report: dict[str, object],
) -> dict[str, object]:
    content = {
        "schema_version": "risk-sealed-test-completion-v1",
        "protocol_version": config.protocol_version,
        "evaluation_sequence": 1,
        "candidate_manifest_sha256": config.candidate_manifest_sha256,
        "opening_intent_sha256": opening_intent["sha256"],
        "sealed_test_evaluation_sha256": evaluation["sha256"],
        "report_sha256": _hash(report),
        "repeat_evaluation_allowed": False,
        "completed_at_utc": datetime.now(UTC).isoformat(),
    }
    return {**content, "sha256": _hash(content)}


def _verify_market_and_threshold(
    config: RiskSealedTestConfig,
    market_dataset: dict[str, object],
    threshold_artifact: dict[str, object],
) -> None:
    _verify_hash(market_dataset, "market dataset")
    _verify_hash(threshold_artifact, "threshold artifact")
    if market_dataset["sha256"] != config.market_dataset_sha256:
        raise ValueError("M1 market dataset hash drifted")
    if threshold_artifact["sha256"] != config.threshold_artifact_sha256:
        raise ValueError("M2 threshold artifact hash drifted")
    if threshold_artifact.get("sealed_test_rows_used") != 0:
        raise ValueError("M2 threshold was fit with sealed-test rows")
    market_config = RiskMarketDatasetConfig.model_validate(market_dataset["config"])
    if market_config.test_start != config.test_start or market_config.test_end != config.test_end:
        raise ValueError("M1 and M7 sealed-test periods differ")


def _materialize_test_rows(
    config: RiskSealedTestConfig,
    market_dataset: dict[str, object],
    threshold_artifact: dict[str, object],
    label_config: RiskLabelConfig,
    feature_config: RiskFeatureConfig,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    market_config = RiskMarketDatasetConfig.model_validate(market_dataset["config"])
    drafts, label_exclusions = build_sealed_test_drafts(label_config, market_dataset)
    threshold = Decimal(str(threshold_artifact["threshold"]))
    label_rows = []
    for draft in drafts:
        label_rows.append(
            {
                **draft,
                "risk_threshold": str(threshold_artifact["threshold"]),
                "risk_threshold_sha256": threshold_artifact["sha256"],
                "risk_label": (
                    label_config.high_risk_label
                    if Decimal(str(draft["continuous_risk_outcome"])) >= threshold
                    else label_config.normal_label
                ),
            }
        )
    benchmark_sessions, benchmark_prices = _benchmark_market(market_dataset)
    benchmark_index = {session: index for index, session in enumerate(benchmark_sessions)}
    stock_bars = _stock_market(market_dataset, market_config)
    output = []
    feature_exclusions = Counter()
    for label_row in label_rows:
        ticker = str(label_row["ticker"])
        feature_session = date.fromisoformat(str(label_row["feature_session"]))
        target_session = date.fromisoformat(str(label_row["target_session"]))
        if not config.test_start <= feature_session <= config.test_end:
            raise ValueError("sealed-test feature session is outside frozen period")
        if not config.test_start <= target_session <= config.test_end:
            raise ValueError("sealed-test target session is outside frozen period")
        index = benchmark_index[feature_session]
        if target_session != benchmark_sessions[index + 1]:
            raise ValueError("sealed-test target is not the next benchmark session")
        start = index - feature_config.required_consecutive_sessions + 1
        if start < 0:
            feature_exclusions["insufficient_feature_warmup"] += 1
            continue
        history_sessions = benchmark_sessions[start : index + 1]
        ticker_bars = stock_bars[ticker]
        if any(session not in ticker_bars for session in history_sessions):
            feature_exclusions["missing_consecutive_feature_bar"] += 1
            continue
        history_bars = [ticker_bars[session] for session in history_sessions]
        _verify_m2_feature_state(label_row, history_bars[-21:])
        features = _calculate_features(
            history_bars,
            benchmark_prices[start : index + 1],
            feature_config,
        )
        if set(features) != set(FEATURE_NAMES):
            raise ValueError("sealed-test feature contract mismatch")
        if any(value is None or not math.isfinite(float(value)) for value in features.values()):
            feature_exclusions["null_or_non_finite_feature"] += 1
            continue
        output.append(
            {
                "ticker": ticker,
                "feature_session": label_row["feature_session"],
                "information_cutoff": label_row["information_cutoff"],
                "features": features,
                "split": "test",
                "target": {
                    "target_session": label_row["target_session"],
                    "continuous_risk_outcome": label_row["continuous_risk_outcome"],
                    "next_abs_log_return": label_row["next_abs_log_return"],
                    "next_high_low_log_range": label_row["next_high_low_log_range"],
                    "next_parkinson_volatility": label_row["next_parkinson_volatility"],
                    "risk_label": label_row["risk_label"],
                    "risk_threshold_sha256": threshold_artifact["sha256"],
                },
            }
        )
    ordered = sorted(output, key=lambda row: (str(row["feature_session"]), str(row["ticker"])))
    exclusions = {
        **{f"label_{key}": value for key, value in label_exclusions.items()},
        **{f"feature_{key}": value for key, value in sorted(feature_exclusions.items())},
    }
    return ordered, exclusions


def _reconstruct_logistic(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    config: RiskBaselineConfig,
) -> tuple[np.ndarray, dict[str, object], np.ndarray]:
    scaler = StandardScaler(
        with_mean=config.scaler_with_mean,
        with_std=config.scaler_with_std,
    )
    transformed_train = scaler.fit_transform(x_train)
    transformed_test = scaler.transform(x_test)
    model = LogisticRegression(
        C=config.logistic.c,
        l1_ratio=config.logistic.l1_ratio,
        solver=config.logistic.solver,
        class_weight=config.logistic.class_weight,
        max_iter=config.logistic.max_iter,
        tol=config.logistic.tolerance,
        random_state=config.logistic.random_state,
    )
    model.fit(transformed_train, y_train)
    positive_index = int(np.where(model.classes_ == 1)[0][0])
    train_probability = model.predict_proba(transformed_train)[:, positive_index]
    test_probability = model.predict_proba(transformed_test)[:, positive_index]
    state = {
        "model": "logistic_regression",
        "parameters": model.get_params(deep=False),
        "classes": [int(value) for value in model.classes_],
        "scaler_mean": [float(value) for value in scaler.mean_],
        "scaler_scale": [float(value) for value in scaler.scale_],
        "coefficient": [float(value) for value in model.coef_[0]],
        "intercept": [float(value) for value in model.intercept_],
        "evaluation_probability_sha256": _hash(
            [float(value) for value in train_probability]
        ),
    }
    return test_probability, state, train_probability


def _apply_frozen_platt(
    probabilities: np.ndarray,
    calibrator: dict[str, object],
) -> np.ndarray:
    clip = 0.000001
    clipped = np.clip(probabilities, clip, 1 - clip)
    logits = np.log(clipped / (1 - clipped))
    values = float(calibrator["coefficient"]) * logits + float(calibrator["intercept"])
    return 1.0 / (1.0 + np.exp(-values))


def _realized_risk_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    groups: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row["predicted_label"])].append(row)
    output = {}
    for label in ("NORMAL", "HIGH_RISK"):
        group = groups[label]
        output[label] = {
            "count": len(group),
            "mean_continuous_risk_outcome": _mean_target(group, "continuous_risk_outcome"),
            "median_continuous_risk_outcome": _median_target(
                group, "continuous_risk_outcome"
            ),
            "mean_next_abs_log_return": _mean_target(group, "next_abs_log_return"),
            "mean_next_high_low_log_range": _mean_target(
                group, "next_high_low_log_range"
            ),
            "mean_next_parkinson_volatility": _mean_target(
                group, "next_parkinson_volatility"
            ),
        }
    return output


def _mean_target(rows: list[dict[str, object]], name: str) -> float | None:
    if not rows:
        return None
    return float(np.mean([float(row["target"][name]) for row in rows]))


def _median_target(rows: list[dict[str, object]], name: str) -> float | None:
    if not rows:
        return None
    return float(median(float(row["target"][name]) for row in rows))


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

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from transformers import AutoModel, AutoTokenizer

from research.evaluation.b4_market_reaction_validation import (
    align_reaction_window,
    event_family_id,
    load_protocol,
    ticker_window_id,
)

PRIVATE_ROOT = Path(".tools/datasets/b4-twmd-historical-backfill-v1")
MARKET_PATH = Path(".tools/datasets/risk-market-dataset-v1/dataset.json")
MODEL_PATH = Path(".tools/models/m7-domain-adaptation-pilot-v1/bert-base-chinese")
OUTPUT_ROOT = Path(".tools/evaluations/b4-market-reaction-validation-v2")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_events(root: Path) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for path in sorted((root / "private_batches").glob("*/*.json")):
        events.extend(json.loads(path.read_text(encoding="utf-8"))["events"])
    return events


def _market_maps(payload: dict[str, object]) -> tuple[list[str], dict, dict]:
    benchmark = {row["date"]: float(row["price"]) for row in payload["benchmark_rows"]}
    stocks = {
        (row["ticker"], row["trading_date"]): row for row in payload["stock_rows"]
    }
    return sorted(benchmark), benchmark, stocks


def _lag_features(
    ticker: str,
    anchor: str,
    sessions: list[str],
    benchmark: dict,
    stocks: dict,
) -> list[float] | None:
    try:
        index = sessions.index(anchor)
    except ValueError:
        return None
    if index < 20:
        return None
    dates = sessions[index - 20 : index + 1]
    stock_closes = []
    benchmark_closes = []
    volumes = []
    for day in dates:
        row = stocks.get((ticker, day))
        if row is None or day not in benchmark:
            return None
        stock_closes.append(float(row["adjusted_close"]))
        volumes.append(float(row["volume"]))
        benchmark_closes.append(float(benchmark[day]))
    stock_returns = np.diff(np.log(stock_closes))
    market_returns = np.diff(np.log(benchmark_closes))
    volume_mean = float(np.mean(volumes[:-1]))
    volume_std = float(np.std(volumes[:-1]))
    volume_z = 0.0 if volume_std <= 1e-12 else (volumes[-1] - volume_mean) / volume_std
    return [
        float(stock_returns[-1]),
        float(np.std(stock_returns)),
        float(market_returns[-1]),
        float(np.std(market_returns)),
        float(stock_returns[-1] - market_returns[-1]),
        float(volume_z),
    ]


def build_rows(
    events: list[dict[str, object]], market: dict[str, object]
) -> tuple[list[dict[str, object]], dict[str, int]]:
    protocol = load_protocol()
    sessions, benchmark, stocks = _market_maps(market)
    session_dates = [datetime.fromisoformat(value).date() for value in sessions]
    families: dict[str, dict[str, object]] = {}
    alignment_counts: Counter[str] = Counter()
    for event in events:
        published = datetime.fromisoformat(str(event["publication_timestamp"]))
        family = event_family_id(str(event["ticker"]), str(event["subject"]), published.date())
        existing = families.get(family)
        if existing is None or str(event["publication_timestamp"]) < str(
            existing["publication_timestamp"]
        ):
            families[family] = event
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for event in families.values():
        published = datetime.fromisoformat(str(event["publication_timestamp"]))
        window = align_reaction_window(
            published,
            session_dates,
            protocol,
            timestamp_basis="SOURCE_CONTRACT_ASSUMPTION",
        )
        alignment_counts[window.status] += 1
        if window.status != "ELIGIBLE":
            continue
        assert window.anchor_session and window.reaction_session
        ticker = str(event["ticker"])
        anchor = window.anchor_session.isoformat()
        reaction = window.reaction_session.isoformat()
        if (ticker, anchor) not in stocks or (ticker, reaction) not in stocks:
            alignment_counts["ABSTAIN_MARKET_MATCH"] += 1
            continue
        grouped[ticker_window_id(ticker, window)].append(
            {**event, "anchor": anchor, "reaction": reaction}
        )
    rows: list[dict[str, object]] = []
    for window_id, items in grouped.items():
        first = min(items, key=lambda item: str(item["publication_timestamp"]))
        ticker = str(first["ticker"])
        anchor = str(first["anchor"])
        reaction = str(first["reaction"])
        features = _lag_features(ticker, anchor, sessions, benchmark, stocks)
        if features is None:
            continue
        stock_return = float(stocks[(ticker, reaction)]["adjusted_close"]) / float(
            stocks[(ticker, anchor)]["adjusted_close"]
        ) - 1.0
        market_return = benchmark[reaction] / benchmark[anchor] - 1.0
        classes = Counter(str(item["event_class"]) for item in items)
        dominant_class = sorted(classes, key=lambda value: (-classes[value], value))[0]
        rows.append(
            {
                "window_id": window_id,
                "ticker": ticker,
                "anchor": anchor,
                "reaction": reaction,
                "year": int(str(first["publication_timestamp"])[:4]),
                "market_features": features,
                "event_count": len(items),
                "mean_confidence": float(np.mean([float(item["confidence"]) for item in items])),
                "dominant_event_class": dominant_class,
                "subjects": [str(item["subject"]) for item in items],
                "target": stock_return - market_return,
            }
        )
    rows.sort(key=lambda item: (str(item["reaction"]), str(item["ticker"])))
    return rows, dict(alignment_counts)


def embed_subjects(rows: list[dict[str, object]], cache_path: Path) -> np.ndarray:
    row_hash = hashlib.sha256(
        "\n".join(str(row["window_id"]) for row in rows).encode()
    ).hexdigest()
    if cache_path.exists():
        cached = np.load(cache_path, allow_pickle=False)
        if str(cached["row_hash"]) == row_hash:
            return cached["embeddings"]
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    model = AutoModel.from_pretrained(MODEL_PATH, local_files_only=True).eval()
    vectors: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, len(rows), 32):
            batch_rows = rows[start : start + 32]
            texts = ["；".join(row["subjects"]) for row in batch_rows]
            tokens = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
            hidden = model(**tokens).last_hidden_state
            mask = tokens["attention_mask"].unsqueeze(-1)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            vectors.append(pooled.cpu().numpy().astype(np.float32))
    embeddings = np.concatenate(vectors)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache_path, row_hash=np.array(row_hash), embeddings=embeddings)
    return embeddings


def _metrics(y_true: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    correlation = spearmanr(y_true, prediction).statistic
    return {
        "mae": float(mean_absolute_error(y_true, prediction)),
        "rmse": float(mean_squared_error(y_true, prediction) ** 0.5),
        "r2": float(r2_score(y_true, prediction)),
        "spearman": float(correlation) if np.isfinite(correlation) else 0.0,
    }


def _fit_predict(
    train: np.ndarray,
    test: np.ndarray,
    y: np.ndarray,
    train_mask: np.ndarray,
) -> np.ndarray:
    scaler = StandardScaler().fit(train)
    model = Ridge(alpha=100.0).fit(scaler.transform(train), y[train_mask])
    return model.predict(scaler.transform(test))


def evaluate(rows: list[dict[str, object]], embeddings: np.ndarray) -> dict[str, object]:
    years = np.array([int(row["year"]) for row in rows])
    y = np.array([float(row["target"]) for row in rows])
    market = np.array([row["market_features"] for row in rows], dtype=float)
    meta_numeric = np.array(
        [[float(row["event_count"]), float(row["mean_confidence"])] for row in rows]
    )
    categories = np.array(
        [[str(row["ticker"]), str(row["dominant_event_class"])] for row in rows]
    )
    fold_results = []
    oof: list[dict[str, object]] = []
    magnitude_oof: list[dict[str, object]] = []
    for evaluation_year in (2023, 2024, 2025):
        train_mask = years < evaluation_year
        test_mask = years == evaluation_year
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit(
            categories[train_mask]
        )
        train_categories = encoder.transform(categories[train_mask])
        test_categories = encoder.transform(categories[test_mask])
        market_train, market_test = market[train_mask], market[test_mask]
        metadata_train = np.column_stack((market_train, meta_numeric[train_mask], train_categories))
        metadata_test = np.column_stack((market_test, meta_numeric[test_mask], test_categories))
        text_train = np.column_stack((metadata_train, embeddings[train_mask]))
        text_test = np.column_stack((metadata_test, embeddings[test_mask]))
        predictions = {
            "market_only": _fit_predict(market_train, market_test, y, train_mask),
            "metadata_only": _fit_predict(metadata_train, metadata_test, y, train_mask),
            "bert_text_metadata": _fit_predict(text_train, text_test, y, train_mask),
        }
        magnitude_predictions = {
            "market_only": _fit_predict(market_train, market_test, np.abs(y), train_mask),
            "metadata_only": _fit_predict(
                metadata_train, metadata_test, np.abs(y), train_mask
            ),
            "bert_text_metadata": _fit_predict(
                text_train, text_test, np.abs(y), train_mask
            ),
        }
        metrics = {name: _metrics(y[test_mask], values) for name, values in predictions.items()}
        magnitude_metrics = {
            name: _metrics(np.abs(y[test_mask]), values)
            for name, values in magnitude_predictions.items()
        }
        fold_results.append(
            {
                "evaluation_year": evaluation_year,
                "train_count": int(train_mask.sum()),
                "evaluation_count": int(test_mask.sum()),
                "metrics": metrics,
                "absolute_reaction_metrics": magnitude_metrics,
                "text_minus_metadata_spearman": (
                    metrics["bert_text_metadata"]["spearman"]
                    - metrics["metadata_only"]["spearman"]
                ),
            }
        )
        indices = np.flatnonzero(test_mask)
        for offset, index in enumerate(indices):
            oof.append(
                {
                    "window_id": rows[index]["window_id"],
                    "ticker": rows[index]["ticker"],
                    "year": int(years[index]),
                    "target": float(y[index]),
                    **{name: float(value[offset]) for name, value in predictions.items()},
                }
            )
            magnitude_oof.append(
                {
                    "window_id": rows[index]["window_id"],
                    "ticker": rows[index]["ticker"],
                    "year": int(years[index]),
                    "target": float(abs(y[index])),
                    **{
                        name: float(value[offset])
                        for name, value in magnitude_predictions.items()
                    },
                }
            )
    aggregate = {}
    oof_y = np.array([row["target"] for row in oof])
    for name in ("market_only", "metadata_only", "bert_text_metadata"):
        aggregate[name] = _metrics(oof_y, np.array([row[name] for row in oof]))
    magnitude_aggregate = {}
    magnitude_y = np.array([row["target"] for row in magnitude_oof])
    for name in ("market_only", "metadata_only", "bert_text_metadata"):
        prediction = np.array([row[name] for row in magnitude_oof])
        cutoff = float(np.quantile(prediction, 0.9))
        top = magnitude_y[prediction >= cutoff]
        magnitude_aggregate[name] = {
            **_metrics(magnitude_y, prediction),
            "top_decile_lift_ratio": float(np.mean(top) / np.mean(magnitude_y)),
        }
    increments = [float(fold["text_minus_metadata_spearman"]) for fold in fold_results]
    text_spearmans = [
        float(fold["metrics"]["bert_text_metadata"]["spearman"])
        for fold in fold_results
    ]
    text_mae = aggregate["bert_text_metadata"]["mae"]
    metadata_mae = aggregate["metadata_only"]["mae"]
    gate = {
        "median_outer_spearman_positive": float(np.median(text_spearmans)) > 0,
        "mean_text_increment_at_least_0_02": float(np.mean(increments)) >= 0.02,
        "positive_increment_in_two_thirds_folds": float(np.mean(np.array(increments) > 0)) >= 2 / 3,
        "text_mae_no_more_than_one_percent_worse": text_mae <= metadata_mae * 1.01,
        "worst_fold_spearman_at_least_minus_0_05": min(text_spearmans) >= -0.05,
    }
    ticker_robustness = {}
    for ticker in sorted({str(row["ticker"]) for row in oof}):
        selected = [row for row in oof if row["ticker"] == ticker]
        if len(selected) >= 20:
            ticker_robustness[ticker] = _metrics(
                np.array([row["target"] for row in selected]),
                np.array([row["bert_text_metadata"] for row in selected]),
            )
    return {
        "folds": fold_results,
        "aggregate": aggregate,
        "absolute_reaction_aggregate": magnitude_aggregate,
        "ticker_robustness_bert_text": ticker_robustness,
        "text_increment": {
            "mean_spearman_increment": float(np.mean(increments)),
            "positive_fold_fraction": float(np.mean(np.array(increments) > 0)),
            "gate_checks": gate,
            "all_checks_passed": all(gate.values()),
        },
        "oof": oof,
        "magnitude_oof": magnitude_oof,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run corrected B4 TWMD market-reaction study")
    parser.parse_args()
    events = _load_events(PRIVATE_ROOT)
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))
    rows, alignment = build_rows(events, market)
    embeddings = embed_subjects(rows, OUTPUT_ROOT / "embeddings.npz")
    evaluation = evaluate(rows, embeddings)
    by_ticker = Counter(str(row["ticker"]) for row in rows)
    by_year = Counter(str(row["year"]) for row in rows)
    public = {
        "status": "B4_CORRECTED_FULL_TWMD_BACKFILL_EVALUATED",
        "source_event_count": len(events),
        "usable_window_count": len(rows),
        "ticker_count": len(by_ticker),
        "ticker_counts": dict(sorted(by_ticker.items())),
        "year_counts": dict(sorted(by_year.items())),
        "date_coverage": [
            min(str(row["anchor"]) for row in rows),
            max(str(row["reaction"]) for row in rows),
        ],
        "alignment_counts": alignment,
        "market_dataset_sha256": market["sha256"],
        "twmd_manifest_sha256": _sha256(PRIVATE_ROOT / "manifest.json"),
        "encoder_model_sha256": _sha256(MODEL_PATH / "model.safetensors"),
        "folds": evaluation["folds"],
        "aggregate": evaluation["aggregate"],
        "absolute_reaction_aggregate": evaluation["absolute_reaction_aggregate"],
        "ticker_robustness_bert_text": evaluation["ticker_robustness_bert_text"],
        "text_increment": evaluation["text_increment"],
        "market_reaction_model_maturity": (
            "VALIDATED_RESEARCH_SIGNAL"
            if evaluation["text_increment"]["all_checks_passed"]
            else "AUTOMATED_SIGNAL_ONLY"
        ),
        "linguistic_sentiment": "ABSTAIN_CHINESE_SENTIMENT_NOT_VALIDATED",
        "direction_modeled": False,
        "causal_claim": False,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "oof_predictions.json").write_text(
        json.dumps(evaluation["oof"], ensure_ascii=False, indent=2) + "\n"
    )
    (OUTPUT_ROOT / "absolute_reaction_oof_predictions.json").write_text(
        json.dumps(evaluation["magnitude_oof"], ensure_ascii=False, indent=2) + "\n"
    )
    (OUTPUT_ROOT / "result.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(public, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

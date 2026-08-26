from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research.training.domain_adaptation_feasibility import (
    ModelCandidate,
    _build_batches,
    _evaluate,
    _load_text_sample,
    _peak_rss_bytes,
    _set_seed,
    _verify_corpus,
)

PILOT_VERSION = "m7-domain-adaptation-pilot-v1"
REPORT_VERSION = "m7-domain-adaptation-pilot-report-v1"
DEFAULT_CONFIG = Path("research/configs/m7_domain_adaptation_pilot.v1.json")
DEFAULT_CORPUS_DIR = Path(".tools/corpora/fsc-domain-corpus-v1")
DEFAULT_CACHE_DIR = Path(".tools/huggingface")
DEFAULT_MODEL_DIR = Path(".tools/models/m7-domain-adaptation-pilot-v1")
DEFAULT_OUTPUT = Path("artifacts/m7-domain-adaptation-pilot-report.json")
SAFE_MODEL_ROOT = Path(".tools/models")


class PilotConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    pilot_version: Literal["m7-domain-adaptation-pilot-v1"] = PILOT_VERSION
    required_corpus_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed: int = Field(ge=0, le=2**32 - 1)
    max_length: int = Field(ge=16, le=512)
    train_examples: int = Field(ge=1, le=100_000)
    validation_examples: int = Field(ge=1, le=10_000)
    batch_size: int = Field(ge=1, le=64)
    train_steps: int = Field(ge=1, le=10_000)
    validation_batches: int = Field(ge=1, le=1_000)
    learning_rate: float = Field(gt=0, le=0.01)
    mlm_probability: float = Field(gt=0, lt=1)
    max_gradient_norm: float = Field(gt=0, le=100)
    max_seconds_per_candidate: int = Field(ge=1, le=86_400)
    minimum_relative_validation_improvement: float = Field(ge=0, le=1)
    selection_metric: Literal["final_validation_mlm_loss"]
    candidates: list[ModelCandidate] = Field(min_length=2)

    @field_validator("candidates")
    @classmethod
    def unique_candidates(cls, value: list[ModelCandidate]) -> list[ModelCandidate]:
        ids = [candidate.candidate_id for candidate in value]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate_id values must be unique")
        return value

    @model_validator(mode="after")
    def validate_batch_counts(self) -> PilotConfig:
        if self.train_examples < self.batch_size:
            raise ValueError("train_examples must be at least batch_size")
        required_validation = self.validation_batches * self.batch_size
        if self.validation_examples < required_validation:
            raise ValueError("validation_examples cannot be smaller than evaluated batches")
        return self


def load_config(path: Path) -> PilotConfig:
    return PilotConfig.model_validate_json(path.read_text(encoding="utf-8"))


def run_pilot(
    config: PilotConfig,
    corpus_dir: Path,
    cache_dir: Path,
    model_dir: Path,
    *,
    generated_at: datetime | None = None,
    local_files_only: bool = False,
) -> dict[str, object]:
    observed_at = generated_at or datetime.now(UTC)
    if observed_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    _require_safe_model_output(model_dir)

    corpus_manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    _verify_corpus(corpus_dir, corpus_manifest)
    if corpus_manifest["corpus_sha256"] != config.required_corpus_sha256:
        raise ValueError("corpus SHA-256 does not match the predeclared pilot config")
    train_texts = _load_text_sample(corpus_dir / "train.jsonl", config.train_examples)
    validation_texts = _load_text_sample(
        corpus_dir / "validation.jsonl", config.validation_examples
    )
    if len(train_texts) < config.train_examples:
        raise ValueError("training split is smaller than the predeclared sample")
    if len(validation_texts) < config.validation_examples:
        raise ValueError("validation split is smaller than the predeclared sample")

    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    cache_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for candidate in config.candidates:
        destination = model_dir / candidate.candidate_id
        staging = model_dir / f".{candidate.candidate_id}.staging"
        if destination.exists() or staging.exists():
            raise FileExistsError(
                f"refusing to overwrite existing pilot artifact: {destination}"
            )

        _set_seed(config.seed, torch)
        candidate_started = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(
            candidate.model_id,
            revision=candidate.revision,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
        )
        model = AutoModelForMaskedLM.from_pretrained(
            candidate.model_id,
            revision=candidate.revision,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
        )
        load_seconds = time.perf_counter() - candidate_started
        vocabulary_sha256 = _vocabulary_sha256(tokenizer)
        train_batches = _build_batches(
            tokenizer,
            train_texts,
            config.batch_size,
            config.max_length,
            config.mlm_probability,
            config.seed,
            torch,
        )
        validation_batches = _build_batches(
            tokenizer,
            validation_texts,
            config.batch_size,
            config.max_length,
            config.mlm_probability,
            config.seed + 1,
            torch,
        )[: config.validation_batches]
        initial_loss = _evaluate(model, validation_batches, torch)

        optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)
        train_losses = []
        train_started = time.perf_counter()
        model.train()
        for step in range(config.train_steps):
            if time.perf_counter() - candidate_started > config.max_seconds_per_candidate:
                raise TimeoutError(
                    f"candidate exceeded {config.max_seconds_per_candidate} seconds"
                )
            batch = train_batches[step % len(train_batches)]
            optimizer.zero_grad(set_to_none=True)
            output = model(**batch)
            output.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_gradient_norm)
            optimizer.step()
            train_losses.append(float(output.loss.detach()))
        train_seconds = time.perf_counter() - train_started
        final_loss = _evaluate(model, validation_batches, torch)
        total_seconds = time.perf_counter() - candidate_started
        relative_improvement = (initial_loss - final_loss) / initial_loss
        finite_losses = all(
            math.isfinite(value) for value in [initial_loss, final_loss, *train_losses]
        )
        candidate_passed = (
            finite_losses
            and relative_improvement >= config.minimum_relative_validation_improvement
            and total_seconds <= config.max_seconds_per_candidate
        )

        staging.mkdir()
        model.save_pretrained(staging, safe_serialization=True)
        tokenizer.save_pretrained(staging)
        weight_files = sorted(staging.glob("*.safetensors"))
        if len(weight_files) != 1:
            raise ValueError("pilot must produce exactly one safetensors weight file")
        weight_sha256 = _sha256_file(weight_files[0])
        artifact_metadata = {
            "pilot_version": config.pilot_version,
            "candidate_id": candidate.candidate_id,
            "base_model_id": candidate.model_id,
            "base_revision": candidate.revision,
            "license": candidate.license,
            "corpus_sha256": config.required_corpus_sha256,
            "train_split_sha256": corpus_manifest["split_files"]["train"]["sha256"],
            "seed": config.seed,
            "train_steps": config.train_steps,
            "max_length": config.max_length,
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "mlm_probability": config.mlm_probability,
            "vocabulary_sha256": vocabulary_sha256,
            "weight_sha256": weight_sha256,
            "manual_labels_used": False,
            "sentiment_ground_truth": False,
        }
        (staging / "pilot_metadata.json").write_text(
            json.dumps(artifact_metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, destination)

        results.append(
            {
                "candidate_id": candidate.candidate_id,
                "model_id": candidate.model_id,
                "revision": candidate.revision,
                "license": candidate.license,
                "vocabulary_sha256": vocabulary_sha256,
                "parameter_count": sum(
                    parameter.numel() for parameter in model.parameters()
                ),
                "load_seconds": round(load_seconds, 4),
                "train_seconds": round(train_seconds, 4),
                "total_seconds": round(total_seconds, 4),
                "seconds_per_step": round(train_seconds / config.train_steps, 4),
                "initial_validation_mlm_loss": round(initial_loss, 6),
                "mean_train_mlm_loss": round(sum(train_losses) / len(train_losses), 6),
                "final_validation_mlm_loss": round(final_loss, 6),
                "relative_validation_improvement": round(relative_improvement, 6),
                "finite_losses": finite_losses,
                "candidate_gate_passed": candidate_passed,
                "artifact_directory": str(destination),
                "weight_sha256": weight_sha256,
                "weights_saved": True,
            }
        )
        del optimizer, model, tokenizer, train_batches, validation_batches
        gc.collect()

    eligible = [item for item in results if item["candidate_gate_passed"]]
    comparable_vocabularies = len({item["vocabulary_sha256"] for item in results}) == 1
    recommended = None
    if eligible and comparable_vocabularies:
        recommended = min(
            eligible, key=lambda item: item[config.selection_metric]
        )["candidate_id"]

    return {
        "report_version": REPORT_VERSION,
        "pilot_version": config.pilot_version,
        "generated_at": observed_at.astimezone(UTC).isoformat(),
        "corpus_version": corpus_manifest["corpus_version"],
        "corpus_sha256": corpus_manifest["corpus_sha256"],
        "train_split_sha256": corpus_manifest["split_files"]["train"]["sha256"],
        "validation_split_sha256": corpus_manifest["split_files"]["validation"]["sha256"],
        "sealed_test_read": False,
        "budget": {
            "seed": config.seed,
            "max_length": config.max_length,
            "train_examples": config.train_examples,
            "validation_examples": config.validation_examples,
            "batch_size": config.batch_size,
            "train_steps": config.train_steps,
            "validation_batches": config.validation_batches,
            "learning_rate": config.learning_rate,
            "mlm_probability": config.mlm_probability,
            "max_gradient_norm": config.max_gradient_norm,
            "max_seconds_per_candidate": config.max_seconds_per_candidate,
        },
        "selection_contract": {
            "metric": config.selection_metric,
            "minimum_relative_validation_improvement": (
                config.minimum_relative_validation_improvement
            ),
            "requires_identical_vocabulary_hash": True,
            "comparable_vocabularies": comparable_vocabularies,
        },
        "recommended_representation_candidate": recommended,
        "candidates": results,
        "operational_passed": all(item["finite_losses"] for item in results),
        "device": "cpu",
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "peak_rss_bytes": _peak_rss_bytes(),
        "manual_labels_used": False,
        "manual_review_used": False,
        "sentiment_ground_truth": False,
        "downstream_quality_claim": False,
        "weights_committed": False,
    }


def _vocabulary_sha256(tokenizer: object) -> str:
    vocabulary = tokenizer.get_vocab()
    payload = json.dumps(vocabulary, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_safe_model_output(path: Path) -> None:
    resolved = path.resolve()
    safe_root = (Path.cwd() / SAFE_MODEL_ROOT).resolve()
    if not resolved.is_relative_to(safe_root):
        raise ValueError("pilot model output must be inside .tools/models/")


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the predeclared M7 bounded domain-adaptation pilot"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--local-files-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_pilot(
        load_config(args.config),
        args.corpus_dir,
        args.cache_dir,
        args.model_dir,
        local_files_only=args.local_files_only,
    )
    write_report(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "operational_passed": report["operational_passed"],
                "recommended_representation_candidate": report[
                    "recommended_representation_candidate"
                ],
                "sealed_test_read": False,
                "manual_labels_used": False,
                "weights_committed": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["operational_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

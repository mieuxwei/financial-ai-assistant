from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import platform
import random
import resource
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FEASIBILITY_VERSION = "m7-domain-adaptation-feasibility-v1"
REPORT_VERSION = "m7-domain-adaptation-feasibility-report-v1"
DEFAULT_CONFIG = Path("research/configs/m7_domain_adaptation_feasibility.v1.json")
DEFAULT_CORPUS_DIR = Path(".tools/corpora/fsc-domain-corpus-v1")
DEFAULT_CACHE_DIR = Path(".tools/huggingface")
DEFAULT_OUTPUT = Path("artifacts/m7-domain-adaptation-feasibility-report.json")


class ModelCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    model_id: str = Field(min_length=1, max_length=200)
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    license: str = Field(min_length=1, max_length=100)


class FeasibilityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    feasibility_version: Literal["m7-domain-adaptation-feasibility-v1"] = FEASIBILITY_VERSION
    seed: int = Field(ge=0, le=2**32 - 1)
    max_length: int = Field(ge=16, le=512)
    train_examples: int = Field(ge=1, le=10_000)
    validation_examples: int = Field(ge=1, le=10_000)
    batch_size: int = Field(ge=1, le=64)
    train_steps: int = Field(ge=1, le=10_000)
    validation_batches: int = Field(ge=1, le=1_000)
    learning_rate: float = Field(gt=0, le=0.01)
    mlm_probability: float = Field(gt=0, lt=1)
    candidates: list[ModelCandidate] = Field(min_length=1)

    @field_validator("candidates")
    @classmethod
    def unique_candidates(cls, value: list[ModelCandidate]) -> list[ModelCandidate]:
        ids = [candidate.candidate_id for candidate in value]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate_id values must be unique")
        return value

    @model_validator(mode="after")
    def enough_examples_for_batches(self) -> FeasibilityConfig:
        if self.train_examples < self.batch_size:
            raise ValueError("train_examples must be at least batch_size")
        if self.validation_examples < self.batch_size:
            raise ValueError("validation_examples must be at least batch_size")
        return self


def load_config(path: Path) -> FeasibilityConfig:
    return FeasibilityConfig.model_validate_json(path.read_text(encoding="utf-8"))


def run_feasibility(
    config: FeasibilityConfig,
    corpus_dir: Path,
    cache_dir: Path,
    *,
    generated_at: datetime | None = None,
    local_files_only: bool = False,
) -> dict[str, object]:
    observed_at = generated_at or datetime.now(UTC)
    if observed_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")

    corpus_manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    _verify_corpus(corpus_dir, corpus_manifest)
    train_texts = _load_text_sample(corpus_dir / "train.jsonl", config.train_examples)
    validation_texts = _load_text_sample(
        corpus_dir / "validation.jsonl", config.validation_examples
    )
    if len(train_texts) < config.train_examples:
        raise ValueError("training split is smaller than configured train_examples")
    if len(validation_texts) < config.validation_examples:
        raise ValueError("validation split is smaller than configured validation_examples")

    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    cache_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for candidate in config.candidates:
        _set_seed(config.seed, torch)
        started = time.perf_counter()
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
        load_seconds = time.perf_counter() - started
        parameter_count = sum(parameter.numel() for parameter in model.parameters())
        trainable_parameter_count = sum(
            parameter.numel() for parameter in model.parameters() if parameter.requires_grad
        )

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
        model.train()
        train_losses = []
        train_started = time.perf_counter()
        for step in range(config.train_steps):
            batch = train_batches[step % len(train_batches)]
            optimizer.zero_grad(set_to_none=True)
            output = model(**batch)
            output.loss.backward()
            optimizer.step()
            train_losses.append(float(output.loss.detach()))
        train_seconds = time.perf_counter() - train_started
        final_loss = _evaluate(model, validation_batches, torch)
        total_seconds = time.perf_counter() - started

        results.append(
            {
                "candidate_id": candidate.candidate_id,
                "model_id": candidate.model_id,
                "revision": candidate.revision,
                "license": candidate.license,
                "parameter_count": parameter_count,
                "trainable_parameter_count": trainable_parameter_count,
                "load_seconds": round(load_seconds, 4),
                "train_seconds": round(train_seconds, 4),
                "total_seconds": round(total_seconds, 4),
                "seconds_per_step": round(train_seconds / config.train_steps, 4),
                "initial_validation_mlm_loss": round(initial_loss, 6),
                "mean_train_mlm_loss": round(sum(train_losses) / len(train_losses), 6),
                "final_validation_mlm_loss": round(final_loss, 6),
                "validation_loss_delta": round(final_loss - initial_loss, 6),
                "finite_losses": all(
                    math.isfinite(value)
                    for value in [initial_loss, final_loss, *train_losses]
                ),
                "weights_saved": False,
            }
        )
        del optimizer, model, tokenizer, train_batches, validation_batches
        gc.collect()

    return {
        "report_version": REPORT_VERSION,
        "feasibility_version": config.feasibility_version,
        "generated_at": observed_at.astimezone(UTC).isoformat(),
        "corpus_version": corpus_manifest["corpus_version"],
        "corpus_sha256": corpus_manifest["corpus_sha256"],
        "train_split_sha256": corpus_manifest["split_files"]["train"]["sha256"],
        "validation_split_sha256": corpus_manifest["split_files"]["validation"]["sha256"],
        "sealed_test_read": False,
        "seed": config.seed,
        "max_length": config.max_length,
        "train_examples": config.train_examples,
        "validation_examples": config.validation_examples,
        "batch_size": config.batch_size,
        "train_steps": config.train_steps,
        "validation_batches": config.validation_batches,
        "learning_rate": config.learning_rate,
        "mlm_probability": config.mlm_probability,
        "device": "cpu",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "peak_rss_bytes": _peak_rss_bytes(),
        "candidates": results,
        "overall_passed": all(result["finite_losses"] for result in results),
        "manual_labels_used": False,
        "manual_review_used": False,
        "sentiment_ground_truth": False,
        "downstream_quality_claim": False,
        "model_weights_saved": False,
    }


def _verify_corpus(corpus_dir: Path, manifest: dict[str, object]) -> None:
    if manifest.get("corpus_version") != "fsc-domain-corpus-v1":
        raise ValueError("unexpected corpus version")
    if manifest.get("manual_labels_used") is not False:
        raise ValueError("corpus must not contain manual labels")
    for split in ("train", "validation"):
        path = corpus_dir / f"{split}.jsonl"
        expected = manifest["split_files"][split]["sha256"]
        if _sha256_file(path) != expected:
            raise ValueError(f"{split} split checksum mismatch")


def _load_text_sample(path: Path, limit: int) -> list[str]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            rows.append((str(row["content_sha256"]), str(row["text"])))
    rows.sort(key=lambda item: item[0])
    return [text for _, text in rows[:limit]]


def _build_batches(
    tokenizer: object,
    texts: list[str],
    batch_size: int,
    max_length: int,
    probability: float,
    seed: int,
    torch: object,
) -> list[dict[str, object]]:
    generator = torch.Generator().manual_seed(seed)
    batches = []
    for start in range(0, len(texts), batch_size):
        encoded = tokenizer(
            texts[start : start + batch_size],
            max_length=max_length,
            truncation=True,
            padding="max_length",
            return_special_tokens_mask=True,
            return_tensors="pt",
        )
        special_tokens_mask = encoded.pop("special_tokens_mask").bool()
        input_ids = encoded["input_ids"]
        eligible = ~special_tokens_mask & encoded["attention_mask"].bool()
        masked = torch.rand(input_ids.shape, generator=generator) < probability
        masked &= eligible
        for row_index in range(masked.shape[0]):
            if not masked[row_index].any() and eligible[row_index].any():
                first = int(torch.nonzero(eligible[row_index], as_tuple=False)[0])
                masked[row_index, first] = True
        labels = input_ids.clone()
        labels[~masked] = -100
        replacement_draw = torch.rand(input_ids.shape, generator=generator)
        replace_with_mask = masked & (replacement_draw < 0.8)
        input_ids[replace_with_mask] = tokenizer.mask_token_id
        replace_with_random = masked & (replacement_draw >= 0.8) & (replacement_draw < 0.9)
        random_tokens = torch.randint(
            len(tokenizer), input_ids.shape, generator=generator, dtype=input_ids.dtype
        )
        input_ids[replace_with_random] = random_tokens[replace_with_random]
        batches.append({**encoded, "labels": labels})
    return batches


def _evaluate(model: object, batches: list[dict[str, object]], torch: object) -> float:
    model.eval()
    losses = []
    with torch.no_grad():
        for batch in batches:
            losses.append(float(model(**batch).loss))
    return sum(losses) / len(losses)


def _set_seed(seed: int, torch: object) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded CPU-only M7 domain-adaptation feasibility checks"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--local-files-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_feasibility(
        load_config(args.config),
        args.corpus_dir,
        args.cache_dir,
        local_files_only=args.local_files_only,
    )
    write_report(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "overall_passed": report["overall_passed"],
                "candidate_count": len(report["candidates"]),
                "sealed_test_read": False,
                "manual_labels_used": False,
                "model_weights_saved": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["overall_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

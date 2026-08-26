import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from transformers import BertConfig, BertForMaskedLM, BertTokenizerFast

from research.training.domain_adaptation_pilot import (
    PilotConfig,
    _require_safe_model_output,
    run_pilot,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tiny_model(path: Path) -> None:
    path.mkdir()
    vocabulary = [
        "[PAD]",
        "[UNK]",
        "[CLS]",
        "[SEP]",
        "[MASK]",
        "金",
        "融",
        "法",
        "規",
        "銀",
        "行",
        "保",
        "險",
    ]
    vocabulary_path = path / "vocab.txt"
    vocabulary_path.write_text("\n".join(vocabulary) + "\n", encoding="utf-8")
    tokenizer = BertTokenizerFast(vocab_file=str(vocabulary_path))
    tokenizer.save_pretrained(path)
    model = BertForMaskedLM(
        BertConfig(
            vocab_size=len(tokenizer),
            hidden_size=16,
            num_hidden_layers=1,
            num_attention_heads=2,
            intermediate_size=32,
            max_position_embeddings=32,
        )
    )
    model.save_pretrained(path)


def _corpus(path: Path) -> str:
    path.mkdir()
    rows = {
        "train": [
            {"content_sha256": "a" * 64, "text": "金融法規"},
            {"content_sha256": "b" * 64, "text": "銀行法規"},
        ],
        "validation": [
            {"content_sha256": "c" * 64, "text": "保險法規"},
            {"content_sha256": "d" * 64, "text": "金融銀行"},
        ],
    }
    split_files = {}
    for split, split_rows in rows.items():
        target = path / f"{split}.jsonl"
        target.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in split_rows) + "\n",
            encoding="utf-8",
        )
        split_files[split] = {"sha256": _sha256(target)}
    corpus_sha256 = "e" * 64
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "corpus_version": "fsc-domain-corpus-v1",
                "corpus_sha256": corpus_sha256,
                "manual_labels_used": False,
                "split_files": split_files,
            }
        ),
        encoding="utf-8",
    )
    return corpus_sha256


def _config(model_path: Path, corpus_sha256: str) -> PilotConfig:
    candidate = {
        "model_id": str(model_path),
        "license": "test-only",
    }
    return PilotConfig.model_validate(
        {
            "required_corpus_sha256": corpus_sha256,
            "seed": 7,
            "max_length": 16,
            "train_examples": 2,
            "validation_examples": 2,
            "batch_size": 2,
            "train_steps": 2,
            "validation_batches": 1,
            "learning_rate": 0.001,
            "mlm_probability": 0.2,
            "max_gradient_norm": 1.0,
            "max_seconds_per_candidate": 60,
            "minimum_relative_validation_improvement": 0,
            "selection_metric": "final_validation_mlm_loss",
            "candidates": [
                {
                    **candidate,
                    "candidate_id": "tiny-one",
                    "revision": "0" * 40,
                },
                {
                    **candidate,
                    "candidate_id": "tiny-two",
                    "revision": "1" * 40,
                },
            ],
        }
    )


def test_pilot_saves_ignored_style_artifacts_without_labels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    model_path = tmp_path / "tiny-model"
    corpus_path = tmp_path / "corpus"
    _tiny_model(model_path)
    corpus_sha256 = _corpus(corpus_path)
    output_dir = tmp_path / ".tools/models/pilot"

    report = run_pilot(
        _config(model_path, corpus_sha256),
        corpus_path,
        tmp_path / "cache",
        output_dir,
        generated_at=datetime(2026, 8, 26, tzinfo=UTC),
        local_files_only=True,
    )

    assert report["operational_passed"] is True
    assert report["sealed_test_read"] is False
    assert report["manual_labels_used"] is False
    assert report["sentiment_ground_truth"] is False
    assert report["recommended_representation_candidate"] in {"tiny-one", "tiny-two"}
    assert all(candidate["weights_saved"] for candidate in report["candidates"])
    assert (output_dir / "tiny-one/model.safetensors").is_file()
    assert (output_dir / "tiny-two/pilot_metadata.json").is_file()
    assert "金融法規" not in json.dumps(report, ensure_ascii=False)

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        run_pilot(
            _config(model_path, corpus_sha256),
            corpus_path,
            tmp_path / "cache",
            output_dir,
            local_files_only=True,
        )


def test_pilot_output_guard_rejects_public_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inside .tools/models"):
        _require_safe_model_output(tmp_path / "public-model")

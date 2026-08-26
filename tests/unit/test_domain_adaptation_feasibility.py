import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from transformers import BertConfig, BertForMaskedLM, BertTokenizerFast

from research.training.domain_adaptation_feasibility import (
    FeasibilityConfig,
    run_feasibility,
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


def _corpus(path: Path) -> None:
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
        payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in split_rows) + "\n"
        target.write_text(payload, encoding="utf-8")
        split_files[split] = {"sha256": _sha256(target)}
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "corpus_version": "fsc-domain-corpus-v1",
                "corpus_sha256": "e" * 64,
                "manual_labels_used": False,
                "split_files": split_files,
            }
        ),
        encoding="utf-8",
    )


def _config(model_path: Path) -> FeasibilityConfig:
    return FeasibilityConfig.model_validate(
        {
            "seed": 7,
            "max_length": 16,
            "train_examples": 2,
            "validation_examples": 2,
            "batch_size": 2,
            "train_steps": 1,
            "validation_batches": 1,
            "learning_rate": 0.0001,
            "mlm_probability": 0.2,
            "candidates": [
                {
                    "candidate_id": "tiny-bert",
                    "model_id": str(model_path),
                    "revision": "0" * 40,
                    "license": "test-only",
                }
            ],
        }
    )


def test_feasibility_run_uses_no_labels_or_sealed_test(tmp_path: Path) -> None:
    model_path = tmp_path / "tiny-model"
    corpus_path = tmp_path / "corpus"
    _tiny_model(model_path)
    _corpus(corpus_path)

    report = run_feasibility(
        _config(model_path),
        corpus_path,
        tmp_path / "cache",
        generated_at=datetime(2026, 8, 26, tzinfo=UTC),
        local_files_only=True,
    )

    assert report["overall_passed"] is True
    assert report["sealed_test_read"] is False
    assert report["manual_labels_used"] is False
    assert report["sentiment_ground_truth"] is False
    assert report["model_weights_saved"] is False
    assert report["candidates"][0]["finite_losses"] is True
    assert "金融法規" not in json.dumps(report, ensure_ascii=False)


def test_feasibility_rejects_changed_corpus_split(tmp_path: Path) -> None:
    model_path = tmp_path / "tiny-model"
    corpus_path = tmp_path / "corpus"
    _tiny_model(model_path)
    _corpus(corpus_path)
    with (corpus_path / "train.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")

    with pytest.raises(ValueError, match="checksum mismatch"):
        run_feasibility(
            _config(model_path),
            corpus_path,
            tmp_path / "cache",
            local_files_only=True,
        )

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Callable
from datetime import UTC, date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from pipelines.news.b2_dataset import DEFAULT_CONFIG, B2Contract, load_b2_contract
from pipelines.news.b2_forward import B2ForwardEventRunner
from pipelines.news.r2_archive import R2ForwardArchive, R2Settings

TAIPEI = ZoneInfo("Asia/Taipei")
PHASE_TIME = {
    "next_morning": time(8, 0),
    "current": time(16, 30),
    "evening": time(21, 30),
}
RunnerFactory = Callable[[B2Contract, Path], B2ForwardEventRunner]


def canonical_observed_at(phase: str, collection_date: date) -> datetime:
    if phase not in PHASE_TIME:
        raise ValueError(f"unsupported reconciliation phase: {phase}")
    return datetime.combine(collection_date, PHASE_TIME[phase], tzinfo=TAIPEI).astimezone(UTC)


def execute_r2_collection(
    *,
    contract: B2Contract,
    archive: R2ForwardArchive,
    phase: str,
    observed_at: datetime,
    runner_factory: RunnerFactory | None = None,
) -> tuple[dict[str, object], bool]:
    archive.verify_access()
    existing = archive.load_manifest(phase=phase, observed_at=observed_at)
    if existing is not None:
        return existing, True
    factory = runner_factory or (lambda selected, root: B2ForwardEventRunner(selected, root=root))
    with tempfile.TemporaryDirectory(prefix="financial-ai-forward-") as directory:
        root = Path(directory)
        manifest = factory(contract, root).run(
            phase=phase,
            observed_at=observed_at,
            scheduler_deployed=True,
        )
        archive.upload_run(root=root, manifest=manifest)
    return manifest, False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect one bounded TWSE/TPEx forward run and archive it privately in R2"
    )
    parser.add_argument(
        "--phase",
        choices=("current", "evening", "next_morning"),
        required=True,
    )
    parser.add_argument(
        "--collection-date",
        type=date.fromisoformat,
        default=None,
        help="Asia/Taipei YYYY-MM-DD; defaults to today's Taipei date",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    collection_date = args.collection_date or datetime.now(TAIPEI).date()
    observed_at = canonical_observed_at(args.phase, collection_date)
    settings = R2Settings.from_env()
    archive = R2ForwardArchive(settings)
    manifest, reused = execute_r2_collection(
        contract=load_b2_contract(args.config),
        archive=archive,
        phase=args.phase,
        observed_at=observed_at,
    )
    safe_summary = {
        "run_id": manifest["run_id"],
        "phase": manifest["phase"],
        "status": manifest["status"],
        "successful_source_count": manifest["successful_source_count"],
        "manifest_sha256": manifest["manifest_sha256"],
        "reused_remote_manifest": reused,
        "automatic_retraining": False,
    }
    print(json.dumps(safe_summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

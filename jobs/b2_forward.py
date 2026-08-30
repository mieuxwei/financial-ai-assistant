from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from pipelines.news.b2_dataset import DEFAULT_CONFIG, load_b2_contract
from pipelines.news.b2_forward import DEFAULT_PRIVATE_ROOT, B2ForwardEventRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one private, immutable TWSE/TPEx B2 forward collection phase"
    )
    parser.add_argument(
        "--phase",
        choices=("current", "evening", "next_morning"),
        required=True,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    parser.add_argument(
        "--observed-at",
        type=datetime.fromisoformat,
        help="Timezone-aware ISO timestamp; omit during normal manual collection",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    contract = load_b2_contract(args.config)
    manifest = B2ForwardEventRunner(contract, root=args.root).run(
        phase=args.phase,
        observed_at=args.observed_at,
    )
    safe_summary = {
        "run_id": manifest["run_id"],
        "phase": manifest["phase"],
        "status": manifest["status"],
        "source_count": manifest["source_count"],
        "successful_source_count": manifest["successful_source_count"],
        "manifest_sha256": manifest["manifest_sha256"],
        "scheduler_deployed": False,
        "automatic_retraining": False,
    }
    print(json.dumps(safe_summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

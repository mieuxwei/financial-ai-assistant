from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipelines.news.b2_dataset import DEFAULT_CONFIG, build_fsc_b2_snapshot, load_b2_contract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the private B2 normalized FSC snapshot")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    contract = load_b2_contract(args.config)
    report = build_fsc_b2_snapshot(contract)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

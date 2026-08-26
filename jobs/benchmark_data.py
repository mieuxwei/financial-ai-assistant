from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from pipelines.market_data.finmind_benchmark import (
    fetch_taiex_total_return,
    write_benchmark_snapshot,
)

DEFAULT_OUTPUT = Path(".tools/datasets/benchmarks/finmind-taiex-total-return.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch a checksummed FinMind TAIEX benchmark")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.output.resolve().is_relative_to((Path.cwd() / ".tools").resolve()):
        raise ValueError("benchmark snapshot output must stay inside .tools/")
    snapshot = fetch_taiex_total_return(args.start, args.end)
    write_benchmark_snapshot(args.output, snapshot)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "record_count": len(snapshot["rows"]),
                "sha256": snapshot["sha256"],
                "contains_secrets": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if snapshot["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

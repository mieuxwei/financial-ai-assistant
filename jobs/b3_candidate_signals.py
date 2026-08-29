from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.planning.b3_protocol import DEFAULT_CONFIG, audit_b3_evidence, load_protocol

DEFAULT_OUTPUT = Path("artifacts/b3-domain-and-candidate-signals.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze and audit B3 candidate evidence.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = audit_b3_evidence(load_protocol(args.config))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "promoted_candidate": report["promoted_candidate"],
                "new_training_performed": False,
                "new_sentiment_classifier_trained": False,
                "next_executable_unit": report["next_executable_unit"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

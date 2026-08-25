import json
from pathlib import Path

from pipelines.features.types import FeatureDataset


def write_feature_dataset(path: Path, dataset: FeatureDataset) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dataset.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

from datetime import date
from pathlib import Path

import httpx
import pytest

from pipelines.market_data.finmind_benchmark import (
    fetch_taiex_total_return,
    write_benchmark_snapshot,
)


def test_finmind_benchmark_snapshot_is_sorted_and_hashed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["dataset"] == "TaiwanStockTotalReturnIndex"
        assert request.url.params["data_id"] == "TAIEX"
        return httpx.Response(
            200,
            json={
                "status": 200,
                "data": [
                    {"date": "2026-08-25", "stock_id": "TAIEX", "price": 120.5},
                    {"date": "2026-08-24", "stock_id": "TAIEX", "price": 120.0},
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        snapshot = fetch_taiex_total_return(
            date(2026, 8, 24), date(2026, 8, 26), client=client
        )

    assert [row["date"] for row in snapshot["rows"]] == ["2026-08-24", "2026-08-25"]
    assert snapshot["raw_content_stored"] is False
    assert len(snapshot["sha256"]) == 64


def test_benchmark_snapshot_refuses_different_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "benchmark.json"
    first = {"sha256": "a" * 64, "rows": []}
    write_benchmark_snapshot(target, first)
    write_benchmark_snapshot(target, first)

    with pytest.raises(FileExistsError):
        write_benchmark_snapshot(target, {"sha256": "b" * 64, "rows": []})

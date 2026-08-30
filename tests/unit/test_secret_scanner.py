import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCANNER = ROOT / "scripts/check_secrets.py"


def _scan(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCANNER), str(path)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_secret_scanner_allows_runtime_object_reference(tmp_path: Path) -> None:
    (tmp_path / "safe.py").write_text(
        "access_" "token=session.access_token\n", encoding="utf-8"
    )
    result = _scan(tmp_path)
    assert result.returncode == 0


def test_secret_scanner_still_rejects_assigned_secret_value(tmp_path: Path) -> None:
    (tmp_path / "unsafe.py").write_text(
        "access_" "token='actual-secret-value-123456'\n", encoding="utf-8"
    )
    result = _scan(tmp_path)
    assert result.returncode == 1
    assert "Potential secret" in result.stdout

from pathlib import Path

WORKFLOW = Path(".github/workflows/forward-event-collection.yml")


def test_forward_workflow_has_frozen_schedules_and_manual_dispatch() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'cron: "0 0 * * *"' in text
    assert 'cron: "30 8 * * *"' in text
    assert 'cron: "30 13 * * *"' in text
    assert "workflow_dispatch:" in text
    assert "cancel-in-progress: false" in text
    assert "timeout-minutes: 10" in text


def test_forward_workflow_uses_only_r2_secrets_and_never_uploads_raw_artifacts() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for name in (
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME",
        "R2_ENDPOINT",
    ):
        assert f"secrets.{name}" in text
    assert "upload-artifact" not in text
    assert "automatic_retraining" not in text
    assert "jobs.b2_forward_r2" in text
    for forbidden in ("TWMD", "FinMind", "Yahoo", "Gemini", "Perplexity", "GDELT"):
        assert forbidden not in text

"""Tests for redacted exports."""

from __future__ import annotations

from pathlib import Path

from agent_control_plane.cli import main
from agent_control_plane.models import RedactionConfig
from agent_control_plane.records import RunRecorder
from agent_control_plane.redaction import redact_replay_bundle, redact_run_record


def _recorded_run() -> RunRecorder:
    recorder = RunRecorder()
    recorder.start_run(
        task="redaction test",
        actor="redactor",
        environment="test",
        allowed_tools=["crm_read"],
        blocked_tools=[],
        policy_version="v1.0",
    )
    action = recorder.propose_action(
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
        payload={"fields": ["name"]},
        reason="Inspect customer record.",
    )
    recorder.evaluate_action(action)
    recorder.complete_run("final output")
    return recorder


def test_payloads_redacted_by_default() -> None:
    record = _recorded_run().to_run_record()

    redacted = redact_run_record(record)

    assert redacted.actions[0].payload == {"redacted": True}


def test_targets_redacted_when_enabled() -> None:
    bundle = _recorded_run().generate_replay_bundle()

    redacted = redact_replay_bundle(
        bundle,
        RedactionConfig(redact_targets=True, replacement="MASKED"),
    )

    assert redacted.actions[0].target == "MASKED"


def test_final_output_redacted_when_enabled() -> None:
    record = _recorded_run().to_run_record()

    redacted = redact_run_record(
        record,
        RedactionConfig(redact_final_output=True),
    )

    assert redacted.final_output == "[REDACTED]"


def test_original_object_unchanged() -> None:
    record = _recorded_run().to_run_record()

    redacted = redact_run_record(
        record,
        RedactionConfig(redact_targets=True, redact_reasons=True),
    )

    assert redacted.actions[0].target == "[REDACTED]"
    assert record.actions[0].target == "customer:1"
    assert record.decisions[0].reason != "[REDACTED]"


def test_cli_writes_redacted_output(tmp_path: Path) -> None:
    recorder = _recorded_run()
    run_path = tmp_path / "run.json"
    out_path = tmp_path / "redacted.json"
    run_path.write_text(
        recorder.to_run_record().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "redact-run",
            str(run_path),
            "--out",
            str(out_path),
            "--targets",
            "--final-output",
        ]
    )

    assert exit_code == 0
    assert out_path.exists()

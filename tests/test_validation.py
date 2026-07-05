"""Tests for semantic validation reports."""

from __future__ import annotations

from agent_control_plane.validation import validate_run_record
from agent_control_plane.records import RunRecorder


def _build_run_record(*, completed: bool = True):
    recorder = RunRecorder()
    recorder.start_run(
        task="validation test",
        actor="validation-agent",
        environment="test",
        allowed_tools=["crm_read"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )
    action = recorder.propose_action(
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
    )
    recorder.evaluate_action(action)
    if completed:
        recorder.complete_run("Validation complete.")
    return recorder.to_run_record()


def test_valid_run_record_returns_valid_report() -> None:
    report = validate_run_record(_build_run_record())

    assert report.valid is True
    assert report.checked_object_type == "RunRecord"
    assert report.issues == []


def test_mismatched_action_run_id_creates_error() -> None:
    record = _build_run_record().model_copy(deep=True)
    record.actions[0].run_id = "other-run"

    report = validate_run_record(record)

    assert report.valid is False
    assert any(issue.code == "action_run_id_mismatch" for issue in report.issues)


def test_missing_action_reference_in_decision_creates_error() -> None:
    record = _build_run_record().model_copy(deep=True)
    record.decisions[0].action_id = "missing-action"

    report = validate_run_record(record)

    assert report.valid is False
    assert any(issue.code == "decision_action_missing" for issue in report.issues)


def test_blocked_action_without_block_decision_creates_error() -> None:
    recorder = RunRecorder()
    recorder.start_run(
        task="blocked validation test",
        actor="validation-agent",
        environment="test",
        allowed_tools=["crm_read", "email_send"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )
    action = recorder.propose_action(
        tool_name="email_send",
        action_type="external_send",
        target="customer@example.com",
    )
    recorder.evaluate_action(action)
    recorder.complete_run("Validation complete.")
    record = recorder.to_run_record().model_copy(deep=True)
    record.decisions[0].result = "allow"

    report = validate_run_record(record)

    assert report.valid is False
    assert any(
        issue.code == "blocked_action_without_block_decision"
        for issue in report.issues
    )


def test_completed_run_with_no_final_output_creates_warning_but_is_valid() -> None:
    record = _build_run_record().model_copy(deep=True)
    record.final_output = None

    report = validate_run_record(record)

    assert report.valid is True
    assert any(
        issue.code == "completed_run_missing_final_output"
        and issue.severity == "warning"
        for issue in report.issues
    )

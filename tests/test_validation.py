"""Tests for replay and run-record validation."""

from __future__ import annotations

from agent_control_plane.models import BlockedAction
from agent_control_plane.records import RunRecorder
from agent_control_plane.replay import generate_replay_bundle
from agent_control_plane.validation import validate_replay_bundle, validate_run_record


def _valid_run_record():
    recorder = RunRecorder()
    recorder.start_run(
        task="validation test",
        actor="validator",
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
    recorder.complete_run("done")
    return recorder.to_run_record()


def test_valid_run_record_report_is_valid() -> None:
    report = validate_run_record(_valid_run_record())

    assert report.valid is True
    assert report.issues == []


def test_mismatched_run_id_produces_error() -> None:
    record = _valid_run_record()
    record.actions[0].run_id = "other-run"

    report = validate_run_record(record)

    assert report.valid is False
    assert any(issue.code == "run_id_mismatch" for issue in report.issues)


def test_decision_referencing_missing_action_produces_error() -> None:
    record = _valid_run_record()
    record.decisions[0].action_id = "missing-action"

    report = validate_run_record(record)

    assert report.valid is False
    assert any(issue.code == "missing_action_reference" for issue in report.issues)


def test_blocked_action_without_block_decision_produces_error() -> None:
    record = _valid_run_record()
    record.blocked_actions.append(
        BlockedAction(
            blocked_id="blocked-1",
            action_id=record.actions[0].action_id,
            run_id=record.run_id,
            reason="forced",
            policy_name="forced_policy",
        )
    )

    report = validate_run_record(record)

    assert report.valid is False
    assert any(
        issue.code == "blocked_action_without_decision" for issue in report.issues
    )


def test_warning_only_report_returns_valid_true() -> None:
    record = _valid_run_record()
    record.final_output = None

    report = validate_run_record(record)

    assert report.valid is True
    assert any(issue.severity == "warning" for issue in report.issues)


def test_replay_bundle_validation_checks_trace_fingerprint() -> None:
    record = _valid_run_record()
    replay_bundle = generate_replay_bundle(record)
    replay_bundle.policy_traces[0].deterministic_fingerprint = "bad"

    report = validate_replay_bundle(replay_bundle)

    assert report.valid is False
    assert any(issue.code == "trace_fingerprint_mismatch" for issue in report.issues)

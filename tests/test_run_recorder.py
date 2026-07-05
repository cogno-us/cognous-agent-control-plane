"""Tests for RunRecorder action evaluation constraints."""

from __future__ import annotations

import pytest

from agent_control_plane.models import ActionProposal
from agent_control_plane.records import RunRecorder


def _make_started_recorder() -> RunRecorder:
    recorder = RunRecorder()
    recorder.start_run(
        task="RunRecorder test",
        actor="test-agent",
        environment="test",
        allowed_tools=["crm_read"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )
    return recorder


def test_evaluate_action_rejects_foreign_run_action() -> None:
    recorder = _make_started_recorder()
    action = ActionProposal(
        action_id="foreign-action",
        run_id="other-run",
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
    )

    with pytest.raises(ValueError, match="different run"):
        recorder.evaluate_action(action)


def test_evaluate_action_rejects_unrecorded_action() -> None:
    recorder = _make_started_recorder()
    run_id = recorder.to_run_record().run_id
    action = ActionProposal(
        action_id="unrecorded-action",
        run_id=run_id,
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
    )

    with pytest.raises(ValueError, match="not proposed in this run"):
        recorder.evaluate_action(action)


def test_evaluate_action_allows_proposed_action() -> None:
    recorder = _make_started_recorder()
    action = recorder.propose_action(
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
    )

    decision, blocked = recorder.evaluate_action(action)

    assert decision.result == "allow"
    assert blocked is None

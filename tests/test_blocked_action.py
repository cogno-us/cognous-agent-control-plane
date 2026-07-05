"""Tests for blocked-action record creation."""

from __future__ import annotations

from agent_control_plane.records import RunRecorder


def _make_recorder(
    allowed_tools: list[str] | None = None,
    blocked_tools: list[str] | None = None,
) -> RunRecorder:
    recorder = RunRecorder()
    recorder.start_run(
        task="Test task",
        actor="test-agent",
        environment="test",
        allowed_tools=allowed_tools or ["crm_read"],
        blocked_tools=blocked_tools or ["email_send"],
        policy_version="v1.0",
    )
    return recorder


class TestBlockedActionRecord:
    def test_blocked_action_record_created(self) -> None:
        """When a policy decision is 'block', a BlockedAction record is created."""
        recorder = _make_recorder()
        action = recorder.propose_action(
            tool_name="email_send",
            action_type="external_send",
            target="recipient@example.com",
        )
        decision, blocked = recorder.evaluate_action(action)

        assert decision.result == "block"
        assert blocked is not None
        assert blocked.action_id == action.action_id
        assert blocked.run_id == action.run_id

        run_record = recorder.to_run_record()
        assert len(run_record.blocked_actions) == 1
        assert run_record.blocked_actions[0].blocked_id == blocked.blocked_id

    def test_allowed_action_has_no_blocked_record(self) -> None:
        """An allowed action must NOT produce a BlockedAction record."""
        recorder = _make_recorder(allowed_tools=["crm_read"])
        action = recorder.propose_action(
            tool_name="crm_read",
            action_type="read",
            target="customer:42",
        )
        decision, blocked = recorder.evaluate_action(action)

        assert decision.result == "allow"
        assert blocked is None

        run_record = recorder.to_run_record()
        assert len(run_record.blocked_actions) == 0

    def test_multiple_blocks_accumulated(self) -> None:
        recorder = _make_recorder(blocked_tools=["email_send", "file_delete"])
        for tool, target in [
            ("email_send", "user@example.com"),
            ("file_delete", "/etc/passwd"),
        ]:
            action = recorder.propose_action(
                tool_name=tool,
                action_type="external_send",
                target=target,
            )
            recorder.evaluate_action(action)

        run_record = recorder.to_run_record()
        assert len(run_record.blocked_actions) == 2

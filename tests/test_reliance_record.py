"""Tests for RelianceRecord creation and linkage."""

from __future__ import annotations

from agent_control_plane.records import RunRecorder


def _make_recorder() -> RunRecorder:
    recorder = RunRecorder()
    recorder.start_run(
        task="Reliance test task",
        actor="test-agent",
        environment="test",
        allowed_tools=["crm_read", "notes_search"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )
    return recorder


class TestRelianceRecord:
    def test_reliance_record_created(self) -> None:
        """RelianceRecord is created and linked to the action."""
        recorder = _make_recorder()
        action = recorder.propose_action(
            tool_name="crm_read",
            action_type="read",
            target="customer:99",
        )
        recorder.evaluate_action(action)
        reliance = recorder.record_reliance(
            source_name="crm_read",
            source_type="tool",
            scope="customer record fields: name, email",
            referenced_action_id=action.action_id,
        )

        run_record = recorder.to_run_record()
        assert len(run_record.reliance_records) == 1
        assert run_record.reliance_records[0].reliance_id == reliance.reliance_id
        assert run_record.reliance_records[0].referenced_action_id == action.action_id
        assert run_record.reliance_records[0].source_type == "tool"

    def test_reliance_record_without_action_link(self) -> None:
        """RelianceRecord can be created without a referenced action."""
        recorder = _make_recorder()
        reliance = recorder.record_reliance(
            source_name="user_prompt",
            source_type="user_input",
            scope="initial task description",
        )
        assert reliance.referenced_action_id is None

        run_record = recorder.to_run_record()
        assert len(run_record.reliance_records) == 1

    def test_multiple_reliance_records(self) -> None:
        recorder = _make_recorder()
        for source, stype, scope in [
            ("crm_read", "tool", "customer data"),
            ("notes_search", "tool", "internal notes"),
            ("user_prompt", "user_input", "task description"),
        ]:
            recorder.record_reliance(source_name=source, source_type=stype, scope=scope)  # type: ignore[arg-type]

        run_record = recorder.to_run_record()
        assert len(run_record.reliance_records) == 3

    def test_reliance_run_id_matches_run(self) -> None:
        recorder = _make_recorder()
        run_id = recorder._run_id
        reliance = recorder.record_reliance(
            source_name="crm_read", source_type="tool", scope="data"
        )
        assert reliance.run_id == run_id

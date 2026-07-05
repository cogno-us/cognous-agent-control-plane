"""Tests for ReplayBundle construction and completeness."""

from __future__ import annotations

from agent_control_plane.records import RunRecorder
from agent_control_plane.replay import from_json, generate_replay_bundle, to_json


def _build_full_run() -> RunRecorder:
    recorder = RunRecorder()
    recorder.start_run(
        task="Full replay test run",
        actor="test-agent",
        environment="test",
        allowed_tools=["crm_read", "notes_search"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )
    recorder.add_authority_record(
        actor="test-agent",
        scope=["read"],
        source="test_policy",
    )
    action_allowed = recorder.propose_action(
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
    )
    recorder.evaluate_action(action_allowed)
    recorder.record_reliance(
        source_name="crm_read",
        source_type="tool",
        scope="customer record",
        referenced_action_id=action_allowed.action_id,
    )
    action_blocked = recorder.propose_action(
        tool_name="email_send",
        action_type="external_send",
        target="user@example.com",
    )
    recorder.evaluate_action(action_blocked)
    recorder.complete_run("Run complete.")
    return recorder


class TestReplayBundle:
    def test_replay_bundle_contains_all_records(self) -> None:
        """ReplayBundle must include frame, actions, decisions, authority,
        reliance, and blocked actions."""
        recorder = _build_full_run()
        run_record = recorder.to_run_record()
        bundle = generate_replay_bundle(run_record)

        assert bundle.run_id == run_record.run_id
        assert bundle.frame.frame_id == run_record.frame.frame_id
        assert len(bundle.actions) == len(run_record.actions)
        assert len(bundle.decisions) == len(run_record.decisions)
        assert len(bundle.policy_traces) == len(run_record.policy_traces)
        assert len(bundle.authority_records) == len(run_record.authority_records)
        assert len(bundle.reliance_records) == len(run_record.reliance_records)
        assert len(bundle.blocked_actions) == len(run_record.blocked_actions)
        assert bundle.final_output == run_record.final_output

    def test_replay_bundle_via_recorder_helper(self) -> None:
        recorder = _build_full_run()
        bundle = recorder.generate_replay_bundle()

        run_record = recorder.to_run_record()
        assert run_record.replay_bundle_id == bundle.replay_bundle_id

    def test_replay_bundle_json_round_trip(self) -> None:
        recorder = _build_full_run()
        run_record = recorder.to_run_record()
        bundle = generate_replay_bundle(run_record)

        json_str = to_json(bundle)
        restored = from_json(json_str)

        assert restored.replay_bundle_id == bundle.replay_bundle_id
        assert restored.run_id == bundle.run_id
        assert len(restored.actions) == len(bundle.actions)
        assert len(restored.blocked_actions) == len(bundle.blocked_actions)
        assert len(restored.policy_traces) == len(bundle.policy_traces)
        assert len(restored.reliance_records) == len(bundle.reliance_records)
        assert restored.final_output == bundle.final_output

    def test_replay_bundle_has_blocked_actions(self) -> None:
        recorder = _build_full_run()
        run_record = recorder.to_run_record()
        bundle = generate_replay_bundle(run_record)

        assert len(bundle.blocked_actions) == 1
        assert bundle.blocked_actions[0].action_id == run_record.blocked_actions[0].action_id

"""Tests for deterministic policy gate behaviour and JSON round-trip."""

from __future__ import annotations

import json

from agent_control_plane.models import ActionProposal, AuthorityRecord, Frame
from agent_control_plane.policy_gate import PolicyGate
from agent_control_plane.records import RunRecorder


def _make_frame() -> Frame:
    return Frame(
        frame_id="frame-det",
        task="determinism test",
        actor="test-agent",
        environment="test",
        allowed_tools=["crm_read", "notes_search"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )


def _make_action(tool_name: str = "crm_read", action_type: str = "read") -> ActionProposal:
    return ActionProposal(
        action_id="action-det",
        run_id="run-det",
        tool_name=tool_name,
        action_type=action_type,
        target="resource:det",
    )


def _make_authority(scope: list[str]) -> AuthorityRecord:
    return AuthorityRecord(
        authority_id="auth-det",
        run_id="run-det",
        actor="test-agent",
        scope=scope,
        source="test",
    )


class TestDeterminism:
    def test_policy_gate_deterministic(self) -> None:
        """Same inputs twice must return identical result and fingerprint."""
        gate = PolicyGate()
        frame = _make_frame()
        action = _make_action()
        authority = _make_authority(["read"])

        decision_1 = gate.evaluate(action, frame, [authority])
        decision_2 = gate.evaluate(action, frame, [authority])

        assert decision_1.result == decision_2.result
        assert decision_1.deterministic_fingerprint == decision_2.deterministic_fingerprint

    def test_fingerprint_changes_with_different_inputs(self) -> None:
        """Changing any input must change the fingerprint."""
        gate = PolicyGate()
        frame = _make_frame()
        action_read = _make_action("crm_read", "read")
        action_write = _make_action("crm_read", "write")

        fp_read = gate.evaluate(action_read, frame, []).deterministic_fingerprint
        fp_write = gate.evaluate(action_write, frame, []).deterministic_fingerprint
        assert fp_read != fp_write

    def test_fingerprint_stable_across_authority_insertion_order(self) -> None:
        """Fingerprint must not change when authority scopes are provided in
        different order."""
        gate = PolicyGate()
        frame = _make_frame()
        action = _make_action()

        auth_a = _make_authority(["read", "write"])
        auth_b = _make_authority(["write", "read"])

        fp_a = gate.evaluate(action, frame, [auth_a]).deterministic_fingerprint
        fp_b = gate.evaluate(action, frame, [auth_b]).deterministic_fingerprint
        assert fp_a == fp_b


class TestJsonRoundTrip:
    def test_json_export_round_trip(self) -> None:
        """Export a run to JSON, reload it, and check essential fields survive."""
        recorder = RunRecorder()
        recorder.start_run(
            task="Round-trip test",
            actor="test-agent",
            environment="test",
            allowed_tools=["crm_read"],
            blocked_tools=["email_send"],
            policy_version="v1.0",
        )
        recorder.add_authority_record(
            actor="test-agent",
            scope=["read"],
            source="test",
        )
        action = recorder.propose_action(
            tool_name="crm_read",
            action_type="read",
            target="customer:1",
        )
        recorder.evaluate_action(action)
        recorder.complete_run("Test complete.")

        import tempfile, pathlib
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "run.json"
            recorder.export_json(path)

            raw = json.loads(path.read_text())

        original = recorder.to_run_record()

        assert raw["run_id"] == original.run_id
        assert raw["task"] == original.task
        assert raw["completed"] is True
        assert raw["final_output"] == "Test complete."
        assert len(raw["actions"]) == len(original.actions)
        assert len(raw["decisions"]) == len(original.decisions)
        assert raw["frame"]["frame_id"] == original.frame.frame_id
        assert raw["decisions"][0]["deterministic_fingerprint"] == (
            original.decisions[0].deterministic_fingerprint
        )

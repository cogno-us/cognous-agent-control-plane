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

        decision_1 = gate.evaluate(
            action,
            frame,
            [authority],
            now="2026-01-01T00:00:00+00:00",
        )
        decision_2 = gate.evaluate(
            action,
            frame,
            [authority],
            now="2026-01-01T00:00:00+00:00",
        )

        assert decision_1.result == decision_2.result
        assert decision_1.deterministic_fingerprint == decision_2.deterministic_fingerprint
        assert decision_1.decision_id != decision_2.decision_id

    def test_fingerprint_changes_with_different_inputs(self) -> None:
        """Changing any input must change the fingerprint."""
        gate = PolicyGate()
        frame = _make_frame()
        action_read = _make_action("crm_read", "read")
        action_write = _make_action("crm_read", "write")

        fp_read = gate.evaluate(
            action_read,
            frame,
            [],
            now="2026-01-01T00:00:00+00:00",
        ).deterministic_fingerprint
        fp_write = gate.evaluate(
            action_write,
            frame,
            [],
            now="2026-01-01T00:00:00+00:00",
        ).deterministic_fingerprint
        assert fp_read != fp_write

    def test_fingerprint_stable_across_authority_insertion_order(self) -> None:
        """Fingerprint must not change when active authority record order changes."""
        gate = PolicyGate()
        frame = _make_frame()
        action = _make_action()

        auth_a = AuthorityRecord(
            authority_id="auth-a",
            run_id="run-det",
            actor="test-agent",
            scope=["read"],
            source="test",
        )
        auth_b = AuthorityRecord(
            authority_id="auth-b",
            run_id="run-det",
            actor="test-agent",
            scope=["write"],
            source="test",
        )

        fp_a = gate.evaluate(
            action,
            frame,
            [auth_a, auth_b],
            now="2026-01-01T00:00:00+00:00",
        ).deterministic_fingerprint
        fp_b = gate.evaluate(
            action,
            frame,
            [auth_b, auth_a],
            now="2026-01-01T00:00:00+00:00",
        ).deterministic_fingerprint
        assert fp_a == fp_b

    def test_fingerprint_uses_active_authority_only(self) -> None:
        gate = PolicyGate()
        frame = _make_frame()
        action = _make_action("notes_search", "write")
        active = AuthorityRecord(
            authority_id="auth-active",
            run_id="run-det",
            actor="test-agent",
            scope=["write"],
            source="test",
            expires_at="2026-06-01T00:00:00+00:00",
        )
        expired = AuthorityRecord(
            authority_id="auth-expired",
            run_id="run-det",
            actor="test-agent",
            scope=["external_send"],
            source="test",
            expires_at="2025-01-01T00:00:00+00:00",
        )

        fp_with_expired = gate.evaluate(
            action,
            frame,
            [active, expired],
            now="2026-01-01T00:00:00+00:00",
        ).deterministic_fingerprint
        fp_active_only = gate.evaluate(
            action,
            frame,
            [active],
            now="2026-01-01T00:00:00+00:00",
        ).deterministic_fingerprint

        assert fp_with_expired == fp_active_only

    def test_fingerprint_changes_when_authority_expires_across_now_timestamps(self) -> None:
        gate = PolicyGate()
        frame = _make_frame().model_copy(
            update={"allowed_tools": ("crm_read", "notes_search", "email_send")}
        )
        action = _make_action("email_send", "external_send")
        authority = AuthorityRecord(
            authority_id="auth-expiring",
            run_id="run-det",
            actor="test-agent",
            scope=["external_send"],
            source="test",
            expires_at="2026-01-02T00:00:00+00:00",
        )

        active_fp = gate.evaluate(
            action,
            frame,
            [authority],
            now="2026-01-01T00:00:00+00:00",
        ).deterministic_fingerprint
        expired_fp = gate.evaluate(
            action,
            frame,
            [authority],
            now="2026-01-03T00:00:00+00:00",
        ).deterministic_fingerprint

        assert active_fp != expired_fp


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

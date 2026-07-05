"""Tests for the deterministic policy gate – allow and escalate cases."""

from __future__ import annotations

import pytest

from agent_control_plane.models import ActionProposal, AuthorityRecord, Frame
from agent_control_plane.policy_gate import PolicyGate


def _make_frame(
    allowed_tools: list[str] | None = None,
    blocked_tools: list[str] | None = None,
    policy_version: str = "v1.0",
) -> Frame:
    return Frame(
        frame_id="frame-1",
        task="test task",
        actor="test-agent",
        environment="test",
        allowed_tools=allowed_tools or [],
        blocked_tools=blocked_tools or [],
        policy_version=policy_version,
    )


def _make_action(
    tool_name: str,
    action_type: str,
    target: str = "resource:1",
    run_id: str = "run-1",
) -> ActionProposal:
    return ActionProposal(
        action_id="action-1",
        run_id=run_id,
        tool_name=tool_name,
        action_type=action_type,
        target=target,
    )


def _make_authority(scope: list[str], run_id: str = "run-1") -> AuthorityRecord:
    return AuthorityRecord(
        authority_id="auth-1",
        run_id=run_id,
        actor="test-agent",
        scope=scope,
        source="test",
    )


class TestPolicyGateAllowRead:
    def test_policy_gate_allows_read_for_allowed_tool(self) -> None:
        gate = PolicyGate()
        frame = _make_frame(allowed_tools=["crm_read"])
        action = _make_action("crm_read", "read")
        decision = gate.evaluate(action, frame, [])
        assert decision.result == "allow"
        assert decision.action_id == "action-1"
        assert decision.deterministic_fingerprint  # non-empty


class TestPolicyGateBlocksBlockedTool:
    def test_policy_gate_blocks_blocked_tool(self) -> None:
        gate = PolicyGate()
        frame = _make_frame(allowed_tools=["crm_read"], blocked_tools=["email_send"])
        action = _make_action("email_send", "external_send")
        decision = gate.evaluate(action, frame, [])
        assert decision.result == "block"

    def test_blocked_tool_takes_priority_over_allowed(self) -> None:
        """A tool that appears in both lists is blocked."""
        gate = PolicyGate()
        frame = _make_frame(
            allowed_tools=["dangerous_tool"],
            blocked_tools=["dangerous_tool"],
        )
        action = _make_action("dangerous_tool", "read")
        decision = gate.evaluate(action, frame, [])
        assert decision.result == "block"


class TestPolicyGateEscalatesUnknownTool:
    def test_policy_gate_escalates_unknown_tool(self) -> None:
        gate = PolicyGate()
        frame = _make_frame(allowed_tools=["crm_read"])
        action = _make_action("unknown_tool", "read")
        decision = gate.evaluate(action, frame, [])
        assert decision.result == "escalate"


class TestExternalSendAuthority:
    def test_external_send_requires_authority(self) -> None:
        gate = PolicyGate()
        frame = _make_frame(allowed_tools=["email_send"])
        action = _make_action("email_send", "external_send")
        # Without authority
        decision = gate.evaluate(action, frame, [])
        assert decision.result == "block"

    def test_external_send_with_authority_is_allowed(self) -> None:
        gate = PolicyGate()
        frame = _make_frame(allowed_tools=["email_send"])
        action = _make_action("email_send", "external_send")
        authority = _make_authority(["external_send"])
        decision = gate.evaluate(action, frame, [authority])
        assert decision.result == "allow"

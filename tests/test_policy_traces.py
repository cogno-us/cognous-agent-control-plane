"""Tests for policy evaluation traces."""

from __future__ import annotations

from agent_control_plane.models import ActionProposal, AuthorityRecord, Frame
from agent_control_plane.policy_gate import PolicyGate
from agent_control_plane.records import RunRecorder


def _frame(
    *,
    allowed_tools: list[str] | None = None,
    blocked_tools: list[str] | None = None,
) -> Frame:
    return Frame(
        frame_id="frame-1",
        task="trace-test",
        actor="trace-agent",
        environment="test",
        allowed_tools=allowed_tools or [],
        blocked_tools=blocked_tools or [],
        policy_version="v1.0",
    )


def _action(tool_name: str, action_type: str) -> ActionProposal:
    return ActionProposal(
        action_id="action-1",
        run_id="run-1",
        tool_name=tool_name,
        action_type=action_type,
        target="resource:1",
    )


def _authority(scope: list[str]) -> AuthorityRecord:
    return AuthorityRecord(
        authority_id="auth-1",
        run_id="run-1",
        actor="trace-agent",
        scope=scope,
        source="test",
    )


def test_evaluate_with_trace_returns_decision_and_trace() -> None:
    gate = PolicyGate()

    decision, trace = gate.evaluate_with_trace(
        _action("crm_read", "read"),
        _frame(allowed_tools=["crm_read"]),
        [],
    )

    assert decision.result == "allow"
    assert decision.trace_id == trace.trace_id
    assert trace.final_result == decision.result
    assert trace.deterministic_fingerprint == decision.deterministic_fingerprint


def test_trace_lists_rules_in_order() -> None:
    gate = PolicyGate()

    _decision, trace = gate.evaluate_with_trace(
        _action("crm_read", "read"),
        _frame(allowed_tools=["crm_read"]),
        [],
    )

    assert [rule.rule_name for rule in trace.rules_evaluated] == [
        "blocked_tool_policy",
        "unknown_tool_policy",
        "external_send_authority_policy",
        "read_allowed_tool_policy",
        "write_authority_policy",
        "default_escalation_policy",
    ]


def test_trace_marks_allowed_read_rule() -> None:
    gate = PolicyGate()

    _decision, trace = gate.evaluate_with_trace(
        _action("crm_read", "read"),
        _frame(allowed_tools=["crm_read"]),
        [],
    )

    matched_rules = [rule for rule in trace.rules_evaluated if rule.matched]
    assert len(matched_rules) == 1
    assert matched_rules[0].rule_name == "read_allowed_tool_policy"
    assert matched_rules[0].result == "allow"


def test_trace_marks_blocked_tool_rule() -> None:
    gate = PolicyGate()

    _decision, trace = gate.evaluate_with_trace(
        _action("email_send", "external_send"),
        _frame(allowed_tools=["email_send"], blocked_tools=["email_send"]),
        [],
    )

    matched_rules = [rule for rule in trace.rules_evaluated if rule.matched]
    assert matched_rules[0].rule_name == "blocked_tool_policy"
    assert matched_rules[0].result == "block"


def test_trace_marks_unknown_tool_rule() -> None:
    gate = PolicyGate()

    _decision, trace = gate.evaluate_with_trace(
        _action("unknown_tool", "read"),
        _frame(allowed_tools=["crm_read"]),
        [],
    )

    matched_rules = [rule for rule in trace.rules_evaluated if rule.matched]
    assert matched_rules[0].rule_name == "unknown_tool_policy"
    assert matched_rules[0].result == "escalate"


def test_run_recorder_stores_policy_traces() -> None:
    recorder = RunRecorder()
    recorder.start_run(
        task="trace recorder",
        actor="trace-agent",
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

    traces = recorder.get_policy_traces()
    assert len(traces) == 1
    assert traces[0].action_id == action.action_id


def test_replay_bundle_includes_policy_traces() -> None:
    recorder = RunRecorder()
    recorder.start_run(
        task="trace replay",
        actor="trace-agent",
        environment="test",
        allowed_tools=["email_send"],
        blocked_tools=[],
        policy_version="v1.0",
    )
    recorder.add_authority_record(
        actor="trace-agent",
        scope=["external_send"],
        source="test",
    )
    action = recorder.propose_action(
        tool_name="email_send",
        action_type="external_send",
        target="customer@example.com",
    )
    recorder.evaluate_action(action)

    bundle = recorder.generate_replay_bundle()

    assert len(bundle.policy_traces) == 1
    assert bundle.policy_traces[0].action_id == action.action_id

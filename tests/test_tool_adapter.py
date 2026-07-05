"""Tests for tool adapter execution."""

from __future__ import annotations

from agent_control_plane.records import RunRecorder
from agent_control_plane.tools import execute_with_control


class RecordingAdapter:
    name = "crm_read"
    action_type = "read"

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute(self, target: str, payload: dict) -> dict:
        self.calls.append((target, payload))
        return {"target": target, "payload": payload}


class FailingAdapter:
    name = "crm_read"
    action_type = "read"

    def execute(self, target: str, payload: dict) -> dict:
        raise RuntimeError("adapter failed")


def _make_recorder() -> RunRecorder:
    recorder = RunRecorder()
    recorder.start_run(
        task="tool adapter test",
        actor="adapter-agent",
        environment="test",
        allowed_tools=["crm_read", "email_send"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )
    return recorder


def test_allowed_action_calls_adapter() -> None:
    recorder = _make_recorder()
    adapter = RecordingAdapter()

    decision, result = execute_with_control(
        recorder,
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
        payload={"fields": ["name"]},
        adapter=adapter,
    )

    assert decision.result == "allow"
    assert result is not None and result.executed is True
    assert result.result == {"target": "customer:1", "payload": {"fields": ["name"]}}
    assert adapter.calls == [("customer:1", {"fields": ["name"]})]


def test_blocked_action_does_not_call_adapter() -> None:
    recorder = _make_recorder()
    adapter = RecordingAdapter()

    decision, result = execute_with_control(
        recorder,
        tool_name="email_send",
        action_type="external_send",
        target="customer@example.com",
        payload={"subject": "Hi"},
        adapter=adapter,
    )

    assert decision.result == "block"
    assert result is None
    assert adapter.calls == []


def test_adapter_exception_returns_tool_execution_error() -> None:
    recorder = _make_recorder()

    decision, result = execute_with_control(
        recorder,
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
        adapter=FailingAdapter(),
    )

    assert decision.result == "allow"
    assert result is not None
    assert result.executed is True
    assert result.error == "adapter failed"
    assert result.result == {}


def test_allowed_adapter_execution_creates_reliance_record() -> None:
    recorder = _make_recorder()

    decision, result = execute_with_control(
        recorder,
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
        adapter=RecordingAdapter(),
    )
    run_record = recorder.to_run_record()

    assert decision.result == "allow"
    assert result is not None and result.executed is True
    assert len(run_record.reliance_records) == 1
    assert run_record.reliance_records[0].source_name == "crm_read"

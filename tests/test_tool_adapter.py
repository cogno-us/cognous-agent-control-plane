"""Tests for tool adapter execution helpers."""

from __future__ import annotations

from agent_control_plane.models import ToolExecutionResult
from agent_control_plane.records import RunRecorder
from agent_control_plane.tools import execute_with_control


class RecordingAdapter:
    name = "crm_read"
    action_type = "read"

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute(self, target: str, payload: dict) -> ToolExecutionResult:
        self.calls.append((target, payload))
        return ToolExecutionResult(
            action_id="placeholder",
            run_id="placeholder",
            executed=True,
            result={"ok": True, "target": target},
        )


class FailingAdapter:
    name = "crm_read"
    action_type = "read"

    def execute(self, target: str, payload: dict) -> ToolExecutionResult:
        raise RuntimeError("adapter failed")


def _recorder() -> RunRecorder:
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


def test_blocked_action_does_not_call_adapter() -> None:
    recorder = _recorder()
    adapter = RecordingAdapter()

    decision, result = execute_with_control(
        recorder,
        tool_name="email_send",
        action_type="external_send",
        target="customer@example.com",
        adapter=adapter,
    )

    assert decision.result == "block"
    assert result is None
    assert adapter.calls == []


def test_allowed_action_calls_adapter() -> None:
    recorder = _recorder()
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
    assert result is not None
    assert result.executed is True
    assert adapter.calls == [("customer:1", {"fields": ["name"]})]


def test_reliance_record_created_after_allowed_execution() -> None:
    recorder = _recorder()

    execute_with_control(
        recorder,
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
        adapter=RecordingAdapter(),
    )

    run_record = recorder.to_run_record()
    assert len(run_record.reliance_records) == 1
    assert run_record.reliance_records[0].source_name == "crm_read"


def test_adapter_exception_is_captured() -> None:
    recorder = _recorder()

    decision, result = execute_with_control(
        recorder,
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
        adapter=FailingAdapter(),
    )

    assert decision.result == "allow"
    assert result is not None
    assert result.error == "adapter failed"

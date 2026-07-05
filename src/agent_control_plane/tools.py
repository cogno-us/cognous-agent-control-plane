"""Tool adapter execution helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from agent_control_plane.models import PolicyDecision, ToolExecutionResult

if TYPE_CHECKING:
    from agent_control_plane.records import RunRecorder


class ToolAdapter(Protocol):
    """Minimal adapter contract for executing an allowed tool action."""

    name: str
    action_type: str

    def execute(self, target: str, payload: dict) -> dict: ...


def execute_with_control(
    recorder: "RunRecorder",
    *,
    tool_name: str,
    action_type: str,
    target: str,
    payload: dict | None = None,
    reason: str | None = None,
    adapter: ToolAdapter | None = None,
) -> tuple[PolicyDecision, ToolExecutionResult | None]:
    """Propose, evaluate, and optionally execute an action through a tool adapter."""

    action = recorder.propose_action(
        tool_name=tool_name,
        action_type=action_type,
        target=target,
        payload=payload or {},
        reason=reason,
    )
    decision, _blocked = recorder.evaluate_action(action)

    if decision.result != "allow":
        return decision, None

    if adapter is None:
        return (
            decision,
            ToolExecutionResult(
                action_id=action.action_id,
                run_id=action.run_id,
                executed=False,
                error="No adapter provided.",
            ),
        )

    try:
        result = adapter.execute(target, payload or {})
    except Exception as exc:
        return (
            decision,
            ToolExecutionResult(
                action_id=action.action_id,
                run_id=action.run_id,
                executed=True,
                result={},
                error=str(exc),
            ),
        )

    recorder.record_reliance(
        source_name=tool_name,
        source_type="tool",
        scope=f"Executed {action_type} on {target}",
        referenced_action_id=action.action_id,
    )
    return (
        decision,
        ToolExecutionResult(
            action_id=action.action_id,
            run_id=action.run_id,
            executed=True,
            result=result,
        ),
    )

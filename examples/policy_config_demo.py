"""Policy configuration example."""

from __future__ import annotations

from pathlib import Path

from agent_control_plane import (
    PolicyGate,
    frame_from_policy_config,
    load_policy_config,
)
from agent_control_plane.models import ActionProposal

CONFIG_PATH = Path("examples/policy_config.json")


def _make_action(tool_name: str, action_type: str, target: str) -> ActionProposal:
    return ActionProposal(
        action_id=f"{tool_name}-{action_type}",
        run_id="policy-config-demo",
        tool_name=tool_name,
        action_type=action_type,
        target=target,
    )


def run_demo(config_path: str | Path = CONFIG_PATH) -> dict[str, object]:
    """Load a policy config and evaluate a few representative actions."""

    config = load_policy_config(config_path)
    frame = frame_from_policy_config(
        config,
        task="Policy config demonstration",
        actor="demo-agent",
        environment="sandbox",
    )
    gate = PolicyGate()

    allowed_action = _make_action("crm_read", "read", "customer:42")
    authority_required_action = _make_action(
        "email_send",
        "external_send",
        "customer@example.com",
    )
    escalated_action = _make_action("unknown_tool", "read", "resource:unknown")

    allowed_decision = gate.evaluate(allowed_action, frame, [])
    blocked_decision = gate.evaluate(authority_required_action, frame, [])
    escalated_decision = gate.evaluate(escalated_action, frame, [])

    print(f"allow     {allowed_action.tool_name} -> {allowed_decision.result}")
    print(
        f"authority {authority_required_action.tool_name} "
        f"-> {blocked_decision.result}"
    )
    print(f"default   {escalated_action.tool_name} -> {escalated_decision.result}")

    return {
        "config": config,
        "frame": frame,
        "allowed_decision": allowed_decision,
        "blocked_decision": blocked_decision,
        "escalated_decision": escalated_decision,
    }


def main() -> None:
    run_demo()


if __name__ == "__main__":
    main()

"""Mock agent integration example."""

from __future__ import annotations

from pathlib import Path

from agent_control_plane import RunRecorder

OUTPUT_PATH = Path("examples/output/framework_demo_run_record.json")


class MockAgent:
    """Simple stand-in for an agent framework adapter."""

    def intended_actions(self) -> list[dict[str, object]]:
        return [
            {
                "tool_name": "crm_read",
                "action_type": "read",
                "target": "customer:42",
                "payload": {"fields": ["name", "account_status"]},
                "reason": "Gather customer details for the reply.",
            },
            {
                "tool_name": "email_send",
                "action_type": "external_send",
                "target": "customer@example.com",
                "payload": {"subject": "Account summary"},
                "reason": "Send the drafted response to the customer.",
            },
        ]


def run_demo(output_path: str | Path = OUTPUT_PATH) -> dict[str, object]:
    """Record a mock agent run beside the control plane."""

    recorder = RunRecorder()
    recorder.start_run(
        task="Review a customer account and decide whether to send a reply.",
        actor="mock-agent",
        environment="sandbox",
        allowed_tools=["crm_read"],
        blocked_tools=["email_send"],
        policy_version="framework-demo-v1",
    )

    agent = MockAgent()
    decisions: list[str] = []
    executed_actions: list[str] = []

    for proposed in agent.intended_actions():
        action = recorder.propose_action(**proposed)
        decision, _blocked = recorder.evaluate_action(action)
        decisions.append(decision.result)
        print(f"{action.tool_name} -> {decision.result}")

        if decision.result == "allow":
            executed_actions.append(action.tool_name)
            recorder.record_reliance(
                source_name=action.tool_name,
                source_type="tool",
                scope=f"Executed {action.action_type} on {action.target}",
                referenced_action_id=action.action_id,
            )

    recorder.complete_run("Prepared a response draft and blocked external send.")
    exported_path = recorder.export_json(output_path)
    replay_bundle = recorder.generate_replay_bundle()

    return {
        "decisions": decisions,
        "executed_actions": executed_actions,
        "run_record": recorder.to_run_record(),
        "replay_bundle": replay_bundle,
        "output_path": exported_path,
    }


def main() -> None:
    result = run_demo()
    run_record = result["run_record"]
    replay_bundle = result["replay_bundle"]
    print(f"exported  {result['output_path']}")
    print(f"actions   {len(run_record.actions)}")
    print(f"decisions {len(run_record.decisions)}")
    print(f"blocked   {len(run_record.blocked_actions)}")
    print(f"reliance  {len(run_record.reliance_records)}")
    print(f"bundle    {replay_bundle.replay_bundle_id}")


if __name__ == "__main__":
    main()

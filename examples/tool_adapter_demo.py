"""Tool adapter example with policy-gated execution."""

from __future__ import annotations

from agent_control_plane import RunRecorder, ToolExecutionResult, execute_with_control


class MockCrmAdapter:
    """Minimal adapter that returns a mock CRM record."""

    name = "crm_read"
    action_type = "read"

    def execute(self, target: str, payload: dict) -> ToolExecutionResult:
        return ToolExecutionResult(
            action_id="adapter-action",
            run_id="adapter-run",
            executed=True,
            result={
                "target": target,
                "fields": payload.get("fields", []),
                "status": "ok",
            },
        )


def run_demo() -> dict[str, object]:
    recorder = RunRecorder()
    recorder.start_run(
        task="Look up a customer and decide whether an email can be sent.",
        actor="tool-demo-agent",
        environment="sandbox",
        allowed_tools=["crm_read", "email_send"],
        blocked_tools=["email_send"],
        policy_version="tool-adapter-demo-v1",
    )

    decision_allow, crm_result = execute_with_control(
        recorder,
        tool_name="crm_read",
        action_type="read",
        target="customer:42",
        payload={"fields": ["name", "email"]},
        reason="Load customer details.",
        adapter=MockCrmAdapter(),
    )
    decision_block, blocked_result = execute_with_control(
        recorder,
        tool_name="email_send",
        action_type="external_send",
        target="customer@example.com",
        payload={"subject": "Account update"},
        reason="Attempt delivery.",
    )

    return {
        "allowed_decision": decision_allow,
        "allowed_result": crm_result,
        "blocked_decision": decision_block,
        "blocked_result": blocked_result,
        "run_record": recorder.to_run_record(),
    }


def main() -> None:
    result = run_demo()
    print(f"crm_read   -> {result['allowed_decision'].result}")
    print(f"email_send -> {result['blocked_decision'].result}")


if __name__ == "__main__":
    main()

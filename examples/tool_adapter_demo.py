"""Tool adapter execution example."""

from __future__ import annotations

from pathlib import Path

from agent_control_plane import RunRecorder, execute_with_control

OUTPUT_PATH = Path("examples/output/tool_adapter_demo_run_record.json")


class MockCRMAdapter:
    name = "crm_read"
    action_type = "read"

    def execute(self, target: str, payload: dict) -> dict:
        return {
            "target": target,
            "fields": payload.get("fields", []),
            "account_status": "active",
        }


class MockEmailAdapter:
    name = "email_send"
    action_type = "external_send"

    def execute(self, target: str, payload: dict) -> dict:
        return {"target": target, "payload": payload, "sent": True}


def run_demo(output_path: str | Path = OUTPUT_PATH) -> dict[str, object]:
    """Run one allowed adapter call and one blocked adapter call."""

    recorder = RunRecorder()
    recorder.start_run(
        task="Read a customer record and decide whether an email can be sent.",
        actor="tool-demo-agent",
        environment="sandbox",
        allowed_tools=["crm_read", "email_send"],
        blocked_tools=["email_send"],
        policy_version="tool-demo-v1",
    )

    read_decision, read_result = execute_with_control(
        recorder,
        tool_name="crm_read",
        action_type="read",
        target="customer:42",
        payload={"fields": ["name", "account_status"]},
        reason="Retrieve the customer record before drafting a response.",
        adapter=MockCRMAdapter(),
    )
    send_decision, send_result = execute_with_control(
        recorder,
        tool_name="email_send",
        action_type="external_send",
        target="customer@example.com",
        payload={"subject": "Status update"},
        reason="Attempt external send after review.",
        adapter=MockEmailAdapter(),
    )

    recorder.complete_run("Read completed; external send blocked by policy gate.")
    exported_path = recorder.export_json(output_path)
    replay_bundle = recorder.generate_replay_bundle()

    print(f"crm_read    -> {read_decision.result} (executed={read_result.executed if read_result else False})")
    print(f"email_send  -> {send_decision.result} (executed={send_result.executed if send_result else False})")
    print(f"run record  -> {exported_path}")
    print(f"replay      -> {replay_bundle.replay_bundle_id}")

    return {
        "read_decision": read_decision,
        "read_result": read_result,
        "send_decision": send_decision,
        "send_result": send_result,
        "run_record": recorder.to_run_record(),
        "replay_bundle": replay_bundle,
        "output_path": exported_path,
    }


def main() -> None:
    run_demo()


if __name__ == "__main__":
    main()

"""Tool policy demonstration.

Shows allow, block, and escalate outcomes with fingerprints.

Run from the repository root::

    python examples/tool_policy_demo.py
"""

from __future__ import annotations

from agent_control_plane.models import ActionProposal, AuthorityRecord, Frame
from agent_control_plane.policy_gate import PolicyGate


def _action(tool: str, action_type: str, target: str = "resource:demo") -> ActionProposal:
    return ActionProposal(
        action_id=f"action-{tool}-{action_type}",
        run_id="demo-run",
        tool_name=tool,
        action_type=action_type,
        target=target,
    )


def main() -> None:
    gate = PolicyGate()

    frame = Frame(
        frame_id="frame-demo",
        task="Tool policy demonstration",
        actor="demo-agent",
        environment="sandbox",
        allowed_tools=["crm_read", "notes_search", "email_send"],
        blocked_tools=["file_delete", "admin_exec"],
        policy_version="v1.0",
    )

    authority_read = AuthorityRecord(
        authority_id="auth-read",
        run_id="demo-run",
        actor="demo-agent",
        scope=["read"],
        source="demo_policy",
    )

    authority_write = AuthorityRecord(
        authority_id="auth-write",
        run_id="demo-run",
        actor="demo-agent",
        scope=["read", "write"],
        source="demo_policy",
    )

    authority_send = AuthorityRecord(
        authority_id="auth-send",
        run_id="demo-run",
        actor="demo-agent",
        scope=["read", "external_send"],
        source="demo_policy",
    )

    scenarios: list[tuple[str, ActionProposal, list[AuthorityRecord]]] = [
        # (description, action, authority_records)
        ("ALLOW – crm_read / read", _action("crm_read", "read"), [authority_read]),
        ("ALLOW – notes_search / read", _action("notes_search", "read"), [authority_read]),
        ("ALLOW – email_send / external_send (with authority)", _action("email_send", "external_send"), [authority_send]),
        ("BLOCK – file_delete (blocked tool)", _action("file_delete", "write"), [authority_write]),
        ("BLOCK – admin_exec (blocked tool)", _action("admin_exec", "read"), []),
        ("BLOCK – email_send / external_send (no authority)", _action("email_send", "external_send"), [authority_read]),
        ("ESCALATE – unknown_tool / read", _action("unknown_tool", "read"), [authority_read]),
        ("ESCALATE – crm_read / write (no write authority)", _action("crm_read", "write"), [authority_read]),
        ("ESCALATE – crm_read / delete (unknown action type)", _action("crm_read", "delete"), [authority_write]),
    ]

    print("=" * 72)
    print("Agent Control Plane – Tool Policy Demo")
    print("=" * 72)

    for description, action, authorities in scenarios:
        decision = gate.evaluate(action, frame, authorities)
        label = {
            "allow": "✓ ALLOW   ",
            "block": "✗ BLOCK   ",
            "escalate": "⚠ ESCALATE",
        }[decision.result]
        print(
            f"\n{label}  {description}\n"
            f"          policy  : {decision.policy_name}\n"
            f"          reason  : {decision.reason}\n"
            f"          fp      : {decision.deterministic_fingerprint[:32]}…"
        )

    print("\n" + "=" * 72)
    print("Demo complete.")


if __name__ == "__main__":
    main()

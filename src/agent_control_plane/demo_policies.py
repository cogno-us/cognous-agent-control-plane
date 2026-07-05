"""Demo policy configurations for getting started quickly.

These helpers create pre-configured :class:`~agent_control_plane.records.RunRecorder`
instances for common scenarios so that users can explore the library without
writing boilerplate.
"""

from __future__ import annotations

from agent_control_plane.records import RunRecorder


def read_only_recorder(
    *,
    task: str = "Read-only agent task",
    actor: str = "demo-agent",
    environment: str = "sandbox",
    allowed_tools: list[str] | None = None,
    blocked_tools: list[str] | None = None,
    policy_version: str = "v1.0",
) -> RunRecorder:
    """Return a :class:`~agent_control_plane.records.RunRecorder` configured for
    read-only access with a pre-added read authority record.

    Args:
        task: Task description.
        actor: Actor identifier.
        environment: Environment string.
        allowed_tools: Allowed tools (defaults to ``["crm_read", "notes_search"]``).
        blocked_tools: Blocked tools (defaults to ``["email_send", "file_write"]``).
        policy_version: Policy version string.

    Returns:
        A started :class:`RunRecorder` with read authority.
    """
    if allowed_tools is None:
        allowed_tools = ["crm_read", "notes_search"]
    if blocked_tools is None:
        blocked_tools = ["email_send", "file_write"]

    recorder = RunRecorder()
    recorder.start_run(
        task=task,
        actor=actor,
        environment=environment,
        allowed_tools=allowed_tools,
        blocked_tools=blocked_tools,
        policy_version=policy_version,
    )
    recorder.add_authority_record(
        actor=actor,
        scope=["read"],
        source="demo_policy_config",
    )
    return recorder


def write_enabled_recorder(
    *,
    task: str = "Read-write agent task",
    actor: str = "demo-agent",
    environment: str = "sandbox",
    allowed_tools: list[str] | None = None,
    blocked_tools: list[str] | None = None,
    policy_version: str = "v1.0",
) -> RunRecorder:
    """Return a :class:`~agent_control_plane.records.RunRecorder` configured with
    both read and write authority.

    Args:
        task: Task description.
        actor: Actor identifier.
        environment: Environment string.
        allowed_tools: Allowed tools (defaults to ``["crm_read", "crm_write", "notes_search"]``).
        blocked_tools: Blocked tools (defaults to ``["email_send"]``).
        policy_version: Policy version string.

    Returns:
        A started :class:`RunRecorder` with read and write authority.
    """
    if allowed_tools is None:
        allowed_tools = ["crm_read", "crm_write", "notes_search"]
    if blocked_tools is None:
        blocked_tools = ["email_send"]

    recorder = RunRecorder()
    recorder.start_run(
        task=task,
        actor=actor,
        environment=environment,
        allowed_tools=allowed_tools,
        blocked_tools=blocked_tools,
        policy_version=policy_version,
    )
    recorder.add_authority_record(
        actor=actor,
        scope=["read", "write"],
        source="demo_policy_config",
    )
    return recorder

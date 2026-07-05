"""Frame factory helpers.

The Frame model lives in ``models``.  This module provides a convenience
factory so callers do not need to manage UUIDs directly.
"""

from __future__ import annotations

import uuid

from agent_control_plane.models import Frame


def create_frame(
    *,
    task: str,
    actor: str,
    environment: str,
    allowed_tools: list[str],
    blocked_tools: list[str],
    policy_version: str,
) -> Frame:
    """Create a new :class:`~agent_control_plane.models.Frame` with a generated ID.

    Args:
        task: Human-readable task description.
        actor: Identifier of the agent or user executing the task.
        environment: Deployment environment, e.g. ``"production"``.
        allowed_tools: Explicit allow-list of tool names.
        blocked_tools: Explicit block-list of tool names.
        policy_version: Version string of the active policy set.

    Returns:
        A fully populated :class:`Frame` instance.
    """
    return Frame(
        frame_id=str(uuid.uuid4()),
        task=task,
        actor=actor,
        environment=environment,
        allowed_tools=list(allowed_tools),
        blocked_tools=list(blocked_tools),
        policy_version=policy_version,
    )

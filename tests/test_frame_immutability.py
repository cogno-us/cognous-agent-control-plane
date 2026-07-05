"""Tests for Frame immutability."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_control_plane.models import Frame


def test_frame_is_frozen() -> None:
    frame = Frame(
        frame_id="frame-immut",
        task="immutability test",
        actor="test-agent",
        environment="test",
        allowed_tools=["crm_read"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )

    with pytest.raises(ValidationError, match="frozen"):
        frame.allowed_tools = ("notes_search",)

    with pytest.raises(ValidationError, match="frozen"):
        frame.policy_version = "v2.0"

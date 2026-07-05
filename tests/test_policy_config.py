"""Tests for lightweight policy configuration helpers."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from agent_control_plane.policy_config import (
    frame_from_policy_config,
    load_policy_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_policy_config_from_json() -> None:
    config = load_policy_config(REPO_ROOT / "examples/policy_config.json")

    assert config.policy_version == "v1.1"
    assert config.allowed_tools == ["crm_read", "email_send", "notes_write"]
    assert config.blocked_tools == ["file_delete"]
    assert config.authority_required["external_send"] == ["external_send"]


def test_frame_from_policy_config_uses_expected_fields() -> None:
    config = load_policy_config(REPO_ROOT / "examples/policy_config.json")

    frame = frame_from_policy_config(
        config,
        task="Config-derived frame",
        actor="demo-agent",
        environment="sandbox",
    )

    assert frame.policy_version == "v1.1"
    assert frame.allowed_tools == ("crm_read", "email_send", "notes_write")
    assert frame.blocked_tools == ("file_delete",)
    assert frame.actor == "demo-agent"


def test_load_policy_config_rejects_malformed_json(tmp_path: Path) -> None:
    bad_config = tmp_path / "bad_policy.json"
    bad_config.write_text("{not-json}", encoding="utf-8")

    with pytest.raises(ValueError, match="Failed to parse policy config JSON"):
        load_policy_config(bad_config)


def test_load_policy_config_rejects_missing_required_fields(tmp_path: Path) -> None:
    bad_config = tmp_path / "bad_policy.json"
    bad_config.write_text('{"allowed_tools": ["crm_read"]}', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid policy config"):
        load_policy_config(bad_config)


def test_policy_config_demo_evaluates_allow_block_and_escalate() -> None:
    module = runpy.run_path(str(REPO_ROOT / "examples/policy_config_demo.py"))

    result = module["run_demo"]()

    assert result["allowed_decision"].result == "allow"
    assert result["blocked_decision"].result == "block"
    assert result["escalated_decision"].result == "escalate"

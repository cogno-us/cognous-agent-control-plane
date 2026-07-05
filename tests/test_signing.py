"""Tests for replay bundle signing helpers."""

from __future__ import annotations

from agent_control_plane.records import RunRecorder
from agent_control_plane.signing import (
    sign_replay_bundle,
    verify_signed_replay_bundle,
)


def _build_replay_bundle():
    recorder = RunRecorder()
    recorder.start_run(
        task="Signing test run",
        actor="test-agent",
        environment="test",
        allowed_tools=["crm_read"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )
    action = recorder.propose_action(
        tool_name="crm_read",
        action_type="read",
        target="customer:1",
    )
    recorder.evaluate_action(action)
    recorder.complete_run("Summary complete.")
    return recorder.generate_replay_bundle()


def test_sign_replay_bundle_produces_signature() -> None:
    signed_bundle = sign_replay_bundle(_build_replay_bundle(), "secret-key")

    assert signed_bundle.signature
    assert signed_bundle.signature_algorithm == "HMAC-SHA256"


def test_verify_signed_replay_bundle_for_unmodified_bundle() -> None:
    signed_bundle = sign_replay_bundle(_build_replay_bundle(), "secret-key")

    assert verify_signed_replay_bundle(signed_bundle, "secret-key") is True


def test_verify_signed_replay_bundle_fails_after_bundle_change() -> None:
    signed_bundle = sign_replay_bundle(_build_replay_bundle(), "secret-key")
    tampered_bundle = signed_bundle.replay_bundle.model_copy(
        update={"final_output": "Tampered output."}
    )
    tampered_signed_bundle = signed_bundle.model_copy(
        update={"replay_bundle": tampered_bundle}
    )

    assert verify_signed_replay_bundle(tampered_signed_bundle, "secret-key") is False


def test_verify_signed_replay_bundle_fails_with_wrong_secret() -> None:
    signed_bundle = sign_replay_bundle(_build_replay_bundle(), "secret-key")

    assert verify_signed_replay_bundle(signed_bundle, "wrong-secret") is False

"""Tests for the acp CLI."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from agent_control_plane.cli import main
from agent_control_plane.records import RunRecorder


def _build_run_and_replay_json(tmp_path: Path) -> tuple[Path, Path]:
    recorder = RunRecorder()
    recorder.start_run(
        task="CLI validation run",
        actor="cli-agent",
        environment="test",
        allowed_tools=["crm_read"],
        blocked_tools=["email_send"],
        policy_version="v1.0",
    )
    action = recorder.propose_action(
        tool_name="crm_read",
        action_type="read",
        target="customer:7",
    )
    recorder.evaluate_action(action)
    recorder.complete_run("CLI test complete.")

    run_path = tmp_path / "run_record.json"
    run_path.write_text(
        json.dumps(recorder.to_run_record().model_dump(mode="json")),
        encoding="utf-8",
    )

    replay_path = tmp_path / "replay_bundle.json"
    replay_path.write_text(
        json.dumps(recorder.generate_replay_bundle().model_dump(mode="json")),
        encoding="utf-8",
    )
    return run_path, replay_path


def _invoke_cli(*args: str) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = main(args)
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_validate_run_returns_zero_for_valid_record(tmp_path: Path) -> None:
    run_path, _ = _build_run_and_replay_json(tmp_path)

    exit_code, stdout, _ = _invoke_cli("validate-run", str(run_path))

    assert exit_code == 0
    assert "valid" in stdout


def test_validate_run_returns_non_zero_for_invalid_record(tmp_path: Path) -> None:
    run_path = tmp_path / "invalid_run_record.json"
    run_path.write_text("{}", encoding="utf-8")

    exit_code, _, stderr = _invoke_cli("validate-run", str(run_path))

    assert exit_code == 1
    assert "Validation failed" in stderr


def test_validate_replay_returns_zero_for_valid_bundle(tmp_path: Path) -> None:
    _, replay_path = _build_run_and_replay_json(tmp_path)

    exit_code, stdout, _ = _invoke_cli("validate-replay", str(replay_path))

    assert exit_code == 0
    assert "valid" in stdout


def test_sign_replay_writes_signed_bundle(tmp_path: Path) -> None:
    _, replay_path = _build_run_and_replay_json(tmp_path)
    signed_path = tmp_path / "signed_replay_bundle.json"

    exit_code, stdout, _ = _invoke_cli(
        "sign-replay",
        str(replay_path),
        "--secret",
        "secret-key",
        "--out",
        str(signed_path),
    )

    assert exit_code == 0
    assert signed_path.exists()
    assert "Signed replay bundle written" in stdout


def test_verify_signed_replay_succeeds_with_correct_secret(tmp_path: Path) -> None:
    _, replay_path = _build_run_and_replay_json(tmp_path)
    signed_path = tmp_path / "signed_replay_bundle.json"
    _invoke_cli(
        "sign-replay",
        str(replay_path),
        "--secret",
        "secret-key",
        "--out",
        str(signed_path),
    )

    exit_code, stdout, _ = _invoke_cli(
        "verify-signed-replay",
        str(signed_path),
        "--secret",
        "secret-key",
    )

    assert exit_code == 0
    assert "valid" in stdout


def test_verify_signed_replay_fails_with_wrong_secret(tmp_path: Path) -> None:
    _, replay_path = _build_run_and_replay_json(tmp_path)
    signed_path = tmp_path / "signed_replay_bundle.json"
    _invoke_cli(
        "sign-replay",
        str(replay_path),
        "--secret",
        "secret-key",
        "--out",
        str(signed_path),
    )

    exit_code, _, stderr = _invoke_cli(
        "verify-signed-replay",
        str(signed_path),
        "--secret",
        "wrong-secret",
    )

    assert exit_code == 1
    assert "verification failed" in stderr

"""Command-line utilities for exported run records and replay bundles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TypeVar

from pydantic import BaseModel, ValidationError

from agent_control_plane.models import (
    RedactionConfig,
    ReplayBundle,
    RunRecord,
    SignedReplayBundle,
    ValidationReport,
)
from agent_control_plane.redaction import redact_replay_bundle, redact_run_record
from agent_control_plane.signing import (
    sign_replay_bundle,
    verify_signed_replay_bundle,
)
from agent_control_plane.validation import validate_replay_bundle, validate_run_record

ModelT = TypeVar("ModelT", bound=BaseModel)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="acp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_run = subparsers.add_parser("validate-run")
    validate_run.add_argument("path")

    validate_replay = subparsers.add_parser("validate-replay")
    validate_replay.add_argument("path")

    redact_run = subparsers.add_parser("redact-run")
    redact_run.add_argument("path")
    redact_run.add_argument("--out", required=True)
    redact_run.add_argument("--targets", action="store_true")
    redact_run.add_argument("--final-output", action="store_true")
    redact_run.add_argument("--reasons", action="store_true")
    redact_run.add_argument("--replacement", default="[REDACTED]")

    redact_replay = subparsers.add_parser("redact-replay")
    redact_replay.add_argument("path")
    redact_replay.add_argument("--out", required=True)
    redact_replay.add_argument("--targets", action="store_true")
    redact_replay.add_argument("--final-output", action="store_true")
    redact_replay.add_argument("--reasons", action="store_true")
    redact_replay.add_argument("--replacement", default="[REDACTED]")

    sign_replay = subparsers.add_parser("sign-replay")
    sign_replay.add_argument("path")
    sign_replay.add_argument("--secret", required=True)
    sign_replay.add_argument("--out", required=True)

    verify_signed = subparsers.add_parser("verify-signed-replay")
    verify_signed.add_argument("path")
    verify_signed.add_argument("--secret", required=True)

    return parser


def _load_json_model(path: str | Path, model_type: type[ModelT]) -> ModelT:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {file_path}: {exc}") from exc
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Validation failed for {file_path}: {exc}") from exc


def _write_json_model(path: str | Path, model: BaseModel) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def _print_validation_report(report: ValidationReport) -> int:
    warnings = [issue for issue in report.issues if issue.severity == "warning"]
    errors = [issue for issue in report.issues if issue.severity == "error"]
    status = "valid" if report.valid else "invalid"
    print(
        f"{report.checked_object_type} {report.checked_id} is {status} "
        f"({len(errors)} errors, {len(warnings)} warnings)."
    )
    for issue in warnings + errors:
        location = f" [{issue.path}]" if issue.path else ""
        stream = sys.stderr if issue.severity == "error" else sys.stdout
        print(
            f"{issue.severity.upper()} {issue.code}{location}: {issue.message}",
            file=stream,
        )
    return 0 if report.valid else 1


def _redaction_config_from_args(args: argparse.Namespace) -> RedactionConfig:
    return RedactionConfig(
        redact_payloads=True,
        redact_targets=args.targets,
        redact_final_output=args.final_output,
        redact_reasons=args.reasons,
        replacement=args.replacement,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        if args.command == "validate-run":
            report = validate_run_record(_load_json_model(args.path, RunRecord))
            return _print_validation_report(report)

        if args.command == "validate-replay":
            report = validate_replay_bundle(_load_json_model(args.path, ReplayBundle))
            return _print_validation_report(report)

        if args.command == "redact-run":
            record = _load_json_model(args.path, RunRecord)
            redacted = redact_run_record(record, _redaction_config_from_args(args))
            output_path = _write_json_model(args.out, redacted)
            print(f"Redacted run record written to {output_path}.")
            return 0

        if args.command == "redact-replay":
            bundle = _load_json_model(args.path, ReplayBundle)
            redacted = redact_replay_bundle(bundle, _redaction_config_from_args(args))
            output_path = _write_json_model(args.out, redacted)
            print(f"Redacted replay bundle written to {output_path}.")
            return 0

        if args.command == "sign-replay":
            bundle = _load_json_model(args.path, ReplayBundle)
            signed_bundle = sign_replay_bundle(bundle, args.secret)
            output_path = _write_json_model(args.out, signed_bundle)
            print(f"Signed replay bundle written to {output_path}.")
            return 0

        if args.command == "verify-signed-replay":
            signed_bundle = _load_json_model(args.path, SignedReplayBundle)
            if verify_signed_replay_bundle(signed_bundle, args.secret):
                print("Signed replay bundle is valid.")
                return 0
            print("Signed replay bundle verification failed.", file=sys.stderr)
            return 1
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help(sys.stderr)
    return 2

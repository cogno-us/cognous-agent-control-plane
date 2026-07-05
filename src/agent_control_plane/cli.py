"""Command-line utilities for exported run records and replay bundles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TypeVar

from pydantic import BaseModel, ValidationError

from agent_control_plane.models import ReplayBundle, RunRecord, SignedReplayBundle
from agent_control_plane.signing import (
    sign_replay_bundle,
    verify_signed_replay_bundle,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="acp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_run = subparsers.add_parser("validate-run")
    validate_run.add_argument("path")

    validate_replay = subparsers.add_parser("validate-replay")
    validate_replay.add_argument("path")

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


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        if args.command == "validate-run":
            _load_json_model(args.path, RunRecord)
            print("Run record is valid.")
            return 0

        if args.command == "validate-replay":
            _load_json_model(args.path, ReplayBundle)
            print("Replay bundle is valid.")
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

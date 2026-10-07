#!/usr/bin/env python3
"""Validate one proposed Decision Input Commitment Record.

This tool checks only the proposed sidecar profile. Success is not proof that
current Control Plane runtime enforcement implements the profile, that a source
was authenticated, or that an external assertion is true.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def _load_profile():
    module_path = Path(__file__).parents[1] / "src" / "agent_control_plane" / "decision_input_profile.py"
    spec = importlib.util.spec_from_file_location("decision_input_profile", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="JSON file containing one proposed-profile record")
    args = parser.parse_args()
    profile = _load_profile()
    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
        result = profile.verify_record(record)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "code": "INPUT_INVALID", "message": str(exc)}, sort_keys=True))
        return 2
    except profile.ProfileValidationError as exc:
        print(json.dumps({"valid": False, "code": exc.code, "message": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

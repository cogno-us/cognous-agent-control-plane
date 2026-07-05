"""Tests for the mock framework integration example."""

from __future__ import annotations

import runpy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_framework_integration_demo_runs_without_credentials(tmp_path: Path) -> None:
    module = runpy.run_path(str(REPO_ROOT / "examples/framework_integration_demo.py"))

    result = module["run_demo"](tmp_path / "framework_demo_run_record.json")
    run_record = result["run_record"]

    assert result["decisions"] == ["allow", "block"]
    assert result["executed_actions"] == ["crm_read"]
    assert result["replay_bundle"].run_id == run_record.run_id
    assert len(run_record.actions) == 2
    assert len(run_record.decisions) == 2
    assert len(run_record.blocked_actions) == 1
    assert len(run_record.reliance_records) == 1
    assert Path(result["output_path"]).exists()

"""Helpers for producing redacted public-safe exports.

Fingerprints are preserved during redaction and may still correspond to
pre-redaction inputs.
"""

from __future__ import annotations

from agent_control_plane.models import (
    RedactionConfig,
    ReplayBundle,
    RunRecord,
)


def _config(config: RedactionConfig | None) -> RedactionConfig:
    return config or RedactionConfig()


def redact_run_record(
    record: RunRecord,
    config: RedactionConfig | None = None,
) -> RunRecord:
    """Return a redacted copy of a run record."""

    redaction = _config(config)
    clone = record.model_copy(deep=True)

    for action in clone.actions:
        if redaction.redact_payloads:
            action.payload = {"redacted": True}
        if redaction.redact_targets:
            action.target = redaction.replacement
        if redaction.redact_reasons and action.reason is not None:
            action.reason = redaction.replacement

    if redaction.redact_reasons:
        for decision in clone.decisions:
            decision.reason = redaction.replacement
        for blocked in clone.blocked_actions:
            blocked.reason = redaction.replacement
        for trace in clone.policy_traces:
            for rule in trace.rules_evaluated:
                rule.reason = redaction.replacement

    if redaction.redact_final_output and clone.final_output is not None:
        clone.final_output = redaction.replacement

    return clone


def redact_replay_bundle(
    bundle: ReplayBundle,
    config: RedactionConfig | None = None,
) -> ReplayBundle:
    """Return a redacted copy of a replay bundle."""

    redaction = _config(config)
    clone = bundle.model_copy(deep=True)

    for action in clone.actions:
        if redaction.redact_payloads:
            action.payload = {"redacted": True}
        if redaction.redact_targets:
            action.target = redaction.replacement
        if redaction.redact_reasons and action.reason is not None:
            action.reason = redaction.replacement

    if redaction.redact_reasons:
        for decision in clone.decisions:
            decision.reason = redaction.replacement
        for blocked in clone.blocked_actions:
            blocked.reason = redaction.replacement
        for trace in clone.policy_traces:
            for rule in trace.rules_evaluated:
                rule.reason = redaction.replacement

    if redaction.redact_final_output and clone.final_output is not None:
        clone.final_output = redaction.replacement

    return clone

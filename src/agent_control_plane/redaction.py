"""Privacy-safe redaction helpers for exported objects.

Fingerprints are preserved as recorded and continue to reflect the original
decision inputs rather than the redacted payloads.
"""

from __future__ import annotations

from agent_control_plane.models import RedactionConfig, ReplayBundle, RunRecord


def redact_run_record(
    record: RunRecord,
    config: RedactionConfig | None = None,
) -> RunRecord:
    """Return a deep redacted copy of a run record."""

    redacted = record.model_copy(deep=True)
    _apply_redaction(redacted, config or RedactionConfig())
    return redacted


def redact_replay_bundle(
    bundle: ReplayBundle,
    config: RedactionConfig | None = None,
) -> ReplayBundle:
    """Return a deep redacted copy of a replay bundle."""

    redacted = bundle.model_copy(deep=True)
    _apply_redaction(redacted, config or RedactionConfig())
    return redacted


def _apply_redaction(record_or_bundle: RunRecord | ReplayBundle, config: RedactionConfig) -> None:
    for action in record_or_bundle.actions:
        if config.redact_payloads:
            action.payload = {"redacted": True}
        if config.redact_targets:
            action.target = config.replacement
        if config.redact_reasons and action.reason is not None:
            action.reason = config.replacement

    if config.redact_reasons:
        for decision in record_or_bundle.decisions:
            decision.reason = config.replacement
        for blocked in record_or_bundle.blocked_actions:
            blocked.reason = config.replacement
        for trace in record_or_bundle.policy_traces:
            for rule in trace.rules_evaluated:
                rule.reason = config.replacement

    if config.redact_final_output and record_or_bundle.final_output is not None:
        record_or_bundle.final_output = config.replacement

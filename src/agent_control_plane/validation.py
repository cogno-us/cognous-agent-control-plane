"""Semantic validation for run records and replay bundles."""

from __future__ import annotations

from agent_control_plane.models import (
    ActionProposal,
    AuthorityRecord,
    BlockedAction,
    PolicyDecision,
    PolicyEvaluationTrace,
    ReplayBundle,
    RelianceRecord,
    RunRecord,
    ValidationIssue,
    ValidationReport,
)


class _ValidationCollector:
    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def error(self, code: str, message: str, path: str | None = None) -> None:
        self.issues.append(
            ValidationIssue(severity="error", code=code, message=message, path=path)
        )

    def warning(self, code: str, message: str, path: str | None = None) -> None:
        self.issues.append(
            ValidationIssue(severity="warning", code=code, message=message, path=path)
        )

    def report(self, checked_object_type: str, checked_id: str) -> ValidationReport:
        return ValidationReport(
            valid=not any(issue.severity == "error" for issue in self.issues),
            checked_object_type=checked_object_type,  # type: ignore[arg-type]
            checked_id=checked_id,
            issues=self.issues,
        )


def validate_run_record(record: RunRecord) -> ValidationReport:
    """Validate internal consistency for a run record."""

    collector = _ValidationCollector()
    _validate_run_consistency(
        collector,
        run_id=record.run_id,
        frame_actor=record.frame.actor,
        actions=record.actions,
        decisions=record.decisions,
        blocked_actions=record.blocked_actions,
        reliance_records=record.reliance_records,
        authority_records=record.authority_records,
        policy_traces=record.policy_traces,
    )
    if record.completed and record.final_output is None:
        collector.warning(
            "completed_run_missing_final_output",
            "Completed run record has no final_output.",
            "final_output",
        )
    return collector.report("RunRecord", record.run_id)


def validate_replay_bundle(bundle: ReplayBundle) -> ValidationReport:
    """Validate internal consistency for a replay bundle."""

    collector = _ValidationCollector()
    _validate_run_consistency(
        collector,
        run_id=bundle.run_id,
        frame_actor=bundle.frame.actor,
        actions=bundle.actions,
        decisions=bundle.decisions,
        blocked_actions=bundle.blocked_actions,
        reliance_records=bundle.reliance_records,
        authority_records=bundle.authority_records,
        policy_traces=bundle.policy_traces,
    )
    if bundle.final_output is None:
        collector.warning(
            "replay_missing_final_output",
            "Replay bundle has no final_output.",
            "final_output",
        )
    return collector.report("ReplayBundle", bundle.replay_bundle_id)


def _validate_run_consistency(
    collector: _ValidationCollector,
    *,
    run_id: str,
    frame_actor: str,
    actions: list[ActionProposal],
    decisions: list[PolicyDecision],
    blocked_actions: list[BlockedAction],
    reliance_records: list[RelianceRecord],
    authority_records: list[AuthorityRecord],
    policy_traces: list[PolicyEvaluationTrace],
) -> None:
    action_ids = {action.action_id for action in actions}
    decision_by_action: dict[str, list[PolicyDecision]] = {}
    trace_by_id = {trace.trace_id: trace for trace in policy_traces}

    for index, action in enumerate(actions):
        if action.run_id != run_id:
            collector.error(
                "action_run_id_mismatch",
                f"Action {action.action_id} has run_id {action.run_id!r}, expected {run_id!r}.",
                f"actions[{index}].run_id",
            )

    for index, decision in enumerate(decisions):
        if decision.run_id != run_id:
            collector.error(
                "decision_run_id_mismatch",
                f"Policy decision {decision.decision_id} has run_id {decision.run_id!r}, expected {run_id!r}.",
                f"decisions[{index}].run_id",
            )
        if decision.action_id not in action_ids:
            collector.error(
                "decision_action_missing",
                f"Policy decision {decision.decision_id} references unknown action {decision.action_id!r}.",
                f"decisions[{index}].action_id",
            )
        decision_by_action.setdefault(decision.action_id, []).append(decision)
        if decision.trace_id is not None:
            trace = trace_by_id.get(decision.trace_id)
            if trace is None:
                collector.error(
                    "decision_trace_missing",
                    f"Policy decision {decision.decision_id} references unknown trace {decision.trace_id!r}.",
                    f"decisions[{index}].trace_id",
                )
            elif trace.deterministic_fingerprint != decision.deterministic_fingerprint:
                collector.error(
                    "decision_trace_fingerprint_mismatch",
                    "Policy decision and referenced evaluation trace have different deterministic fingerprints.",
                    f"decisions[{index}].trace_id",
                )

    for index, blocked in enumerate(blocked_actions):
        if blocked.run_id != run_id:
            collector.error(
                "blocked_action_run_id_mismatch",
                f"Blocked action {blocked.blocked_id} has run_id {blocked.run_id!r}, expected {run_id!r}.",
                f"blocked_actions[{index}].run_id",
            )
        if blocked.action_id not in action_ids:
            collector.error(
                "blocked_action_missing_action",
                f"Blocked action {blocked.blocked_id} references unknown action {blocked.action_id!r}.",
                f"blocked_actions[{index}].action_id",
            )
        matching_decisions = decision_by_action.get(blocked.action_id, [])
        if not any(decision.result == "block" for decision in matching_decisions):
            collector.error(
                "blocked_action_without_block_decision",
                f"Blocked action {blocked.blocked_id} does not correspond to a block policy decision.",
                f"blocked_actions[{index}]",
            )

    for index, reliance in enumerate(reliance_records):
        if reliance.run_id != run_id:
            collector.error(
                "reliance_run_id_mismatch",
                f"Reliance record {reliance.reliance_id} has run_id {reliance.run_id!r}, expected {run_id!r}.",
                f"reliance_records[{index}].run_id",
            )
        if (
            reliance.referenced_action_id is not None
            and reliance.referenced_action_id not in action_ids
        ):
            collector.error(
                "reliance_action_missing",
                f"Reliance record {reliance.reliance_id} references unknown action {reliance.referenced_action_id!r}.",
                f"reliance_records[{index}].referenced_action_id",
            )

    for index, authority in enumerate(authority_records):
        if authority.run_id != run_id:
            collector.error(
                "authority_run_id_mismatch",
                f"Authority record {authority.authority_id} has run_id {authority.run_id!r}, expected {run_id!r}.",
                f"authority_records[{index}].run_id",
            )
        if authority.actor != frame_actor:
            collector.warning(
                "authority_actor_mismatch",
                f"Authority record {authority.authority_id} actor {authority.actor!r} does not match frame actor {frame_actor!r}.",
                f"authority_records[{index}].actor",
            )

    for index, trace in enumerate(policy_traces):
        if trace.run_id != run_id:
            collector.error(
                "policy_trace_run_id_mismatch",
                f"Policy evaluation trace {trace.trace_id} has run_id {trace.run_id!r}, expected {run_id!r}.",
                f"policy_traces[{index}].run_id",
            )
        if trace.action_id not in action_ids:
            collector.error(
                "policy_trace_action_missing",
                f"Policy evaluation trace {trace.trace_id} references unknown action {trace.action_id!r}.",
                f"policy_traces[{index}].action_id",
            )

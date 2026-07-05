"""Validation helpers for run records and replay bundles."""

from __future__ import annotations

from collections.abc import Iterable

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


def _issue(
    severity: str,
    code: str,
    message: str,
    path: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
        path=path,
    )


def _validate_run_ids(
    items: Iterable[object],
    *,
    expected_run_id: str,
    path_prefix: str,
    issues: list[ValidationIssue],
) -> None:
    for index, item in enumerate(items):
        run_id = getattr(item, "run_id", None)
        if run_id != expected_run_id:
            issues.append(
                _issue(
                    "error",
                    "run_id_mismatch",
                    f"Expected run_id '{expected_run_id}' but found '{run_id}'.",
                    f"{path_prefix}[{index}].run_id",
                )
            )


def _validate_action_references(
    actions: list[ActionProposal],
    decisions: list[PolicyDecision],
    blocked_actions: list[BlockedAction],
    reliance_records: list[RelianceRecord],
    policy_traces: list[PolicyEvaluationTrace],
    *,
    issues: list[ValidationIssue],
) -> None:
    action_ids = {action.action_id for action in actions}
    decisions_by_action = {decision.action_id: decision for decision in decisions}
    traces_by_id = {trace.trace_id: trace for trace in policy_traces}

    for index, decision in enumerate(decisions):
        if decision.action_id not in action_ids:
            issues.append(
                _issue(
                    "error",
                    "missing_action_reference",
                    f"Decision references unknown action_id '{decision.action_id}'.",
                    f"decisions[{index}].action_id",
                )
            )
        if decision.trace_id is not None and decision.trace_id not in traces_by_id:
            issues.append(
                _issue(
                    "error",
                    "missing_trace_reference",
                    f"Decision references unknown trace_id '{decision.trace_id}'.",
                    f"decisions[{index}].trace_id",
                )
            )

    for index, blocked in enumerate(blocked_actions):
        if blocked.action_id not in action_ids:
            issues.append(
                _issue(
                    "error",
                    "missing_action_reference",
                    f"Blocked action references unknown action_id '{blocked.action_id}'.",
                    f"blocked_actions[{index}].action_id",
                )
            )
            continue
        decision = decisions_by_action.get(blocked.action_id)
        if decision is None or decision.result != "block":
            issues.append(
                _issue(
                    "error",
                    "blocked_action_without_decision",
                    "Blocked action does not correspond to a blocking policy decision.",
                    f"blocked_actions[{index}]",
                )
            )

    for index, reliance in enumerate(reliance_records):
        if (
            reliance.referenced_action_id is not None
            and reliance.referenced_action_id not in action_ids
        ):
            issues.append(
                _issue(
                    "error",
                    "missing_action_reference",
                    (
                        "Reliance record references unknown action_id "
                        f"'{reliance.referenced_action_id}'."
                    ),
                    f"reliance_records[{index}].referenced_action_id",
                )
            )

    for index, trace in enumerate(policy_traces):
        if trace.action_id not in action_ids:
            issues.append(
                _issue(
                    "error",
                    "missing_action_reference",
                    f"Policy trace references unknown action_id '{trace.action_id}'.",
                    f"policy_traces[{index}].action_id",
                )
            )
            continue
        decision = decisions_by_action.get(trace.action_id)
        if decision is None:
            issues.append(
                _issue(
                    "error",
                    "trace_without_decision",
                    "Policy trace does not correspond to a policy decision.",
                    f"policy_traces[{index}]",
                )
            )
            continue
        if decision.trace_id is not None and decision.trace_id != trace.trace_id:
            issues.append(
                _issue(
                    "error",
                    "trace_id_mismatch",
                    "Policy trace identifier does not match the linked decision.",
                    f"policy_traces[{index}].trace_id",
                )
            )
        if trace.final_result != decision.result:
            issues.append(
                _issue(
                    "error",
                    "trace_result_mismatch",
                    "Policy trace final result does not match the decision result.",
                    f"policy_traces[{index}].final_result",
                )
            )
        if trace.deterministic_fingerprint != decision.deterministic_fingerprint:
            issues.append(
                _issue(
                    "error",
                    "trace_fingerprint_mismatch",
                    "Policy trace fingerprint does not match the decision fingerprint.",
                    f"policy_traces[{index}].deterministic_fingerprint",
                )
            )


def _validate_authority_actors(
    frame_actor: str,
    authority_records: list[AuthorityRecord],
    *,
    issues: list[ValidationIssue],
) -> None:
    for index, authority in enumerate(authority_records):
        if authority.actor != frame_actor:
            issues.append(
                _issue(
                    "warning",
                    "authority_actor_mismatch",
                    (
                        f"Authority actor '{authority.actor}' does not match frame "
                        f"actor '{frame_actor}'."
                    ),
                    f"authority_records[{index}].actor",
                )
            )


def validate_run_record(record: RunRecord) -> ValidationReport:
    """Validate internal consistency of a run record."""

    issues: list[ValidationIssue] = []
    _validate_run_ids(record.actions, expected_run_id=record.run_id, path_prefix="actions", issues=issues)
    _validate_run_ids(record.decisions, expected_run_id=record.run_id, path_prefix="decisions", issues=issues)
    _validate_run_ids(
        record.policy_traces,
        expected_run_id=record.run_id,
        path_prefix="policy_traces",
        issues=issues,
    )
    _validate_run_ids(
        record.blocked_actions,
        expected_run_id=record.run_id,
        path_prefix="blocked_actions",
        issues=issues,
    )
    _validate_run_ids(
        record.reliance_records,
        expected_run_id=record.run_id,
        path_prefix="reliance_records",
        issues=issues,
    )
    _validate_run_ids(
        record.authority_records,
        expected_run_id=record.run_id,
        path_prefix="authority_records",
        issues=issues,
    )
    _validate_action_references(
        record.actions,
        record.decisions,
        record.blocked_actions,
        record.reliance_records,
        record.policy_traces,
        issues=issues,
    )
    _validate_authority_actors(
        record.frame.actor,
        record.authority_records,
        issues=issues,
    )
    if record.completed and not record.final_output:
        issues.append(
            _issue(
                "warning",
                "missing_final_output",
                "Completed runs should include final_output.",
                "final_output",
            )
        )

    return ValidationReport(
        valid=not any(issue.severity == "error" for issue in issues),
        checked_object_type="RunRecord",
        checked_id=record.run_id,
        issues=issues,
    )


def validate_replay_bundle(bundle: ReplayBundle) -> ValidationReport:
    """Validate internal consistency of a replay bundle."""

    issues: list[ValidationIssue] = []
    _validate_run_ids(bundle.actions, expected_run_id=bundle.run_id, path_prefix="actions", issues=issues)
    _validate_run_ids(bundle.decisions, expected_run_id=bundle.run_id, path_prefix="decisions", issues=issues)
    _validate_run_ids(
        bundle.policy_traces,
        expected_run_id=bundle.run_id,
        path_prefix="policy_traces",
        issues=issues,
    )
    _validate_run_ids(
        bundle.blocked_actions,
        expected_run_id=bundle.run_id,
        path_prefix="blocked_actions",
        issues=issues,
    )
    _validate_run_ids(
        bundle.reliance_records,
        expected_run_id=bundle.run_id,
        path_prefix="reliance_records",
        issues=issues,
    )
    _validate_run_ids(
        bundle.authority_records,
        expected_run_id=bundle.run_id,
        path_prefix="authority_records",
        issues=issues,
    )
    _validate_action_references(
        bundle.actions,
        bundle.decisions,
        bundle.blocked_actions,
        bundle.reliance_records,
        bundle.policy_traces,
        issues=issues,
    )
    _validate_authority_actors(
        bundle.frame.actor,
        bundle.authority_records,
        issues=issues,
    )

    return ValidationReport(
        valid=not any(issue.severity == "error" for issue in issues),
        checked_object_type="ReplayBundle",
        checked_id=bundle.replay_bundle_id,
        issues=issues,
    )

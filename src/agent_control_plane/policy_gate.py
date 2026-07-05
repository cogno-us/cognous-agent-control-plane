"""Deterministic policy gate for Agent Control Plane.

The :class:`PolicyGate` evaluates an :class:`~agent_control_plane.models.ActionProposal`
against a :class:`~agent_control_plane.models.Frame` and a list of
:class:`~agent_control_plane.models.AuthorityRecord` objects and produces a
:class:`~agent_control_plane.models.PolicyDecision`.

Policy rules (evaluated in order)
----------------------------------
1. If ``action.tool_name`` is in ``frame.blocked_tools``  → **block**
2. If ``action.tool_name`` is not in ``frame.allowed_tools`` → **escalate**
3. If ``action.action_type == "external_send"`` and no authority scope
   includes ``"external_send"`` → **block**
4. If ``action.action_type == "read"`` and tool is allowed → **allow**
5. If ``action.action_type == "write"`` and an authority scope includes
   ``"write"`` → **allow**
6. Otherwise → **escalate**

Fingerprint
-----------
A stable SHA-256 hex digest is computed from canonical JSON containing:
``tool_name``, ``action_type``, ``target``, sorted ``allowed_tools``,
sorted ``blocked_tools``, ``policy_version``, and sorted active authority
scopes.  Identical inputs produce the same result and
``deterministic_fingerprint``.  The ``decision_id`` and ``decided_at``
fields are generated per evaluation.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from agent_control_plane.models import (
    ActionProposal,
    AuthorityRecord,
    Frame,
    PolicyDecision,
    PolicyEvaluationTrace,
    PolicyRuleEvaluation,
)

if TYPE_CHECKING:
    pass


class PolicyGate:
    """Evaluates action proposals against a policy frame.

    The gate is stateless; all inputs required for a decision are passed
    explicitly to :meth:`evaluate`.  Identical inputs always produce the
    same result and ``deterministic_fingerprint``.  The ``decision_id`` and
    ``decided_at`` fields are generated per evaluation.
    """

    def evaluate(
        self,
        action: ActionProposal,
        frame: Frame,
        authority_records: list[AuthorityRecord],
        *,
        now: str | datetime | None = None,
    ) -> PolicyDecision:
        """Evaluate an action proposal and return a policy decision.

        Args:
            action: The proposed action to evaluate.
            frame: The execution frame active for the current run.
            authority_records: Authority records granting scoped permissions.
            now: Optional evaluation time used to filter active authority
                records. Strings must be ISO-8601; naive datetimes are
                treated as UTC.

        Returns:
            A :class:`~agent_control_plane.models.PolicyDecision` with
            ``result`` set to ``"allow"``, ``"block"``, or ``"escalate"``.
        """
        decision, _trace = self.evaluate_with_trace(
            action,
            frame,
            authority_records,
            now=now,
        )
        return decision

    def evaluate_with_trace(
        self,
        action: ActionProposal,
        frame: Frame,
        authority_records: list[AuthorityRecord],
        *,
        now: str | datetime | None = None,
    ) -> tuple[PolicyDecision, PolicyEvaluationTrace]:
        """Evaluate an action proposal and return the decision plus trace."""
        evaluation_time = self._parse_time(now) if now is not None else self._now_utc()
        active_scopes = self._active_authority_scopes(
            action,
            frame,
            authority_records,
            evaluation_time,
        )
        fingerprint = self._fingerprint(action, frame, active_scopes)
        result, policy_name, reason, rule_evaluations = self._apply_rules(
            action,
            frame,
            active_scopes,
        )
        trace_id = str(uuid.uuid4())
        evaluated_at = evaluation_time.isoformat()

        decision = PolicyDecision(
            decision_id=str(uuid.uuid4()),
            action_id=action.action_id,
            run_id=action.run_id,
            result=result,
            policy_name=policy_name,
            reason=reason,
            trace_id=trace_id,
            decided_at=evaluated_at,
            deterministic_fingerprint=fingerprint,
        )
        trace = PolicyEvaluationTrace(
            trace_id=trace_id,
            run_id=action.run_id,
            action_id=action.action_id,
            evaluated_at=evaluated_at,
            rules_evaluated=rule_evaluations,
            final_result=result,
            deterministic_fingerprint=fingerprint,
        )
        return decision, trace

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_rules(
        self,
        action: ActionProposal,
        frame: Frame,
        active_scopes: set[str],
    ) -> tuple[str, str, str, list[PolicyRuleEvaluation]]:
        """Return decision metadata and the ordered rule evaluations."""

        rules: list[PolicyRuleEvaluation] = []
        final_result: str | None = None
        final_policy_name: str | None = None
        final_reason: str | None = None

        def add_rule(
            rule_name: str,
            matched: bool,
            result: str,
            reason: str,
        ) -> None:
            nonlocal final_result, final_policy_name, final_reason
            rules.append(
                PolicyRuleEvaluation(
                    rule_name=rule_name,
                    matched=matched,
                    result=result,  # type: ignore[arg-type]
                    reason=reason,
                )
            )
            if matched:
                final_result = result
                final_policy_name = rule_name
                final_reason = reason

        blocked_tool = action.tool_name in frame.blocked_tools
        add_rule(
            "blocked_tool_policy",
            blocked_tool,
            "block" if blocked_tool else "none",
            (
                f"Tool '{action.tool_name}' is explicitly blocked in this frame."
                if blocked_tool
                else f"Tool '{action.tool_name}' is not explicitly blocked."
            ),
        )

        unknown_tool = not blocked_tool and action.tool_name not in frame.allowed_tools
        add_rule(
            "unknown_tool_policy",
            unknown_tool,
            "escalate" if unknown_tool else "none",
            (
                f"Tool '{action.tool_name}' is not in the allowed-tools list and requires manual review."
                if unknown_tool
                else f"Tool '{action.tool_name}' is present in the allowed-tools list."
            ),
        )

        external_send_matched = (
            final_result is None and action.action_type == "external_send"
        )
        external_send_allowed = "external_send" in active_scopes
        add_rule(
            "external_send_authority_policy",
            external_send_matched,
            (
                "allow"
                if external_send_matched and external_send_allowed
                else "block"
                if external_send_matched
                else "none"
            ),
            (
                "Authority for 'external_send' is present; action allowed."
                if external_send_matched and external_send_allowed
                else (
                    "Action type 'external_send' requires an authority record with scope 'external_send', which was not found."
                    if external_send_matched
                    else f"Action type '{action.action_type}' does not require this rule."
                )
            ),
        )

        read_matched = final_result is None and action.action_type == "read"
        add_rule(
            "read_allowed_tool_policy",
            read_matched,
            "allow" if read_matched else "none",
            (
                f"Tool '{action.tool_name}' is allowed and action type is 'read'."
                if read_matched
                else f"Action type '{action.action_type}' does not match 'read'."
            ),
        )

        write_matched = final_result is None and action.action_type == "write"
        write_allowed = "write" in active_scopes
        add_rule(
            "write_authority_policy",
            write_matched,
            (
                "allow"
                if write_matched and write_allowed
                else "escalate"
                if write_matched
                else "none"
            ),
            (
                "Authority for 'write' is present; action allowed."
                if write_matched and write_allowed
                else (
                    "Action type 'write' requires an authority record with scope 'write', which was not found; escalating for review."
                    if write_matched
                    else f"Action type '{action.action_type}' does not match 'write'."
                )
            ),
        )

        default_matched = final_result is None
        add_rule(
            "default_escalation_policy",
            default_matched,
            "escalate" if default_matched else "none",
            (
                f"Action type '{action.action_type}' does not match any explicit allow or block rule; escalating for review."
                if default_matched
                else "An earlier rule already determined the final result."
            ),
        )

        return (
            final_result or "escalate",
            final_policy_name or "default_escalation_policy",
            final_reason
            or (
                f"Action type '{action.action_type}' does not match any explicit "
                "allow or block rule; escalating for review."
            ),
            rules,
        )

    def _fingerprint(
        self,
        action: ActionProposal,
        frame: Frame,
        active_scopes: set[str],
    ) -> str:
        """Return a stable SHA-256 hex fingerprint of the decision inputs.

        The fingerprint is computed from a canonical JSON object whose keys
        are sorted so that serialisation is deterministic regardless of
        insertion order.
        """
        canonical: dict = {
            "tool_name": action.tool_name,
            "action_type": action.action_type,
            "target": action.target,
            "allowed_tools": sorted(frame.allowed_tools),
            "blocked_tools": sorted(frame.blocked_tools),
            "policy_version": frame.policy_version,
            "authority_scopes": sorted(active_scopes),
        }

        serialised = json.dumps(canonical, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialised.encode()).hexdigest()

    def _active_authority_scopes(
        self,
        action: ActionProposal,
        frame: Frame,
        authority_records: list[AuthorityRecord],
        now: datetime,
    ) -> set[str]:
        """Return scopes from active authority records matching this evaluation."""

        scopes: set[str] = set()
        for record in authority_records:
            if record.run_id != action.run_id:
                continue
            if record.actor != frame.actor:
                continue
            if record.expires_at is not None and self._parse_time(record.expires_at) <= now:
                continue
            scopes.update(record.scope)
        return scopes

    def _now_utc(self) -> datetime:
        """Return the current UTC time."""

        return datetime.now(timezone.utc)

    def _parse_time(self, value: str | datetime) -> datetime:
        """Parse a time value and normalise it to UTC."""

        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

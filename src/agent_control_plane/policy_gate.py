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
sorted ``blocked_tools``, ``policy_version``, and sorted authority scopes.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import TYPE_CHECKING

from agent_control_plane.models import (
    ActionProposal,
    AuthorityRecord,
    Frame,
    PolicyDecision,
)

if TYPE_CHECKING:
    pass


class PolicyGate:
    """Evaluates action proposals against a policy frame.

    The gate is stateless; all inputs required for a decision are passed
    explicitly to :meth:`evaluate`.  This makes the gate deterministic:
    identical inputs always produce identical outputs.
    """

    def evaluate(
        self,
        action: ActionProposal,
        frame: Frame,
        authority_records: list[AuthorityRecord],
    ) -> PolicyDecision:
        """Evaluate an action proposal and return a policy decision.

        Args:
            action: The proposed action to evaluate.
            frame: The execution frame active for the current run.
            authority_records: Authority records granting scoped permissions.

        Returns:
            A :class:`~agent_control_plane.models.PolicyDecision` with
            ``result`` set to ``"allow"``, ``"block"``, or ``"escalate"``.
        """
        fingerprint = self._fingerprint(action, frame, authority_records)
        result, policy_name, reason = self._apply_rules(action, frame, authority_records)

        return PolicyDecision(
            decision_id=str(uuid.uuid4()),
            action_id=action.action_id,
            run_id=action.run_id,
            result=result,
            policy_name=policy_name,
            reason=reason,
            deterministic_fingerprint=fingerprint,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_rules(
        self,
        action: ActionProposal,
        frame: Frame,
        authority_records: list[AuthorityRecord],
    ) -> tuple[str, str, str]:
        """Return (result, policy_name, reason) by applying rules in order."""

        # Rule 1 – blocked tool
        if action.tool_name in frame.blocked_tools:
            return (
                "block",
                "blocked_tool_policy",
                f"Tool '{action.tool_name}' is explicitly blocked in this frame.",
            )

        # Rule 2 – unknown tool (not in allow-list)
        if action.tool_name not in frame.allowed_tools:
            return (
                "escalate",
                "unknown_tool_policy",
                (
                    f"Tool '{action.tool_name}' is not in the allowed-tools list "
                    "and requires manual review."
                ),
            )

        # Collect all authority scopes
        scopes: set[str] = set()
        for rec in authority_records:
            scopes.update(rec.scope)

        # Rule 3 – external_send requires explicit authority
        if action.action_type == "external_send":
            if "external_send" not in scopes:
                return (
                    "block",
                    "external_send_authority_policy",
                    (
                        "Action type 'external_send' requires an authority record "
                        "with scope 'external_send', which was not found."
                    ),
                )
            return (
                "allow",
                "external_send_authority_policy",
                "Authority for 'external_send' is present; action allowed.",
            )

        # Rule 4 – read with allowed tool
        if action.action_type == "read":
            return (
                "allow",
                "read_allowed_tool_policy",
                f"Tool '{action.tool_name}' is allowed and action type is 'read'.",
            )

        # Rule 5 – write with write authority
        if action.action_type == "write":
            if "write" in scopes:
                return (
                    "allow",
                    "write_authority_policy",
                    "Authority for 'write' is present; action allowed.",
                )
            return (
                "escalate",
                "write_authority_policy",
                (
                    "Action type 'write' requires an authority record with scope "
                    "'write', which was not found; escalating for review."
                ),
            )

        # Rule 6 – fallback escalate
        return (
            "escalate",
            "default_escalation_policy",
            (
                f"Action type '{action.action_type}' does not match any explicit "
                "allow or block rule; escalating for review."
            ),
        )

    def _fingerprint(
        self,
        action: ActionProposal,
        frame: Frame,
        authority_records: list[AuthorityRecord],
    ) -> str:
        """Return a stable SHA-256 hex fingerprint of the decision inputs.

        The fingerprint is computed from a canonical JSON object whose keys
        are sorted so that serialisation is deterministic regardless of
        insertion order.
        """
        # Collect all authority scopes (sorted for determinism)
        scopes: list[str] = sorted(
            {s for rec in authority_records for s in rec.scope}
        )

        canonical: dict = {
            "tool_name": action.tool_name,
            "action_type": action.action_type,
            "target": action.target,
            "allowed_tools": sorted(frame.allowed_tools),
            "blocked_tools": sorted(frame.blocked_tools),
            "policy_version": frame.policy_version,
            "authority_scopes": scopes,
        }

        serialised = json.dumps(canonical, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialised.encode()).hexdigest()

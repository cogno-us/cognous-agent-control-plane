"""Core data models for Agent Control Plane.

All models use Pydantic v2 for validation and serialisation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Frame
# ---------------------------------------------------------------------------


class Frame(BaseModel):
    """Execution context that defines what the agent is permitted to do.

    A Frame is created at the start of a run and is immutable for the
    duration of that run.  It records the actor, environment, policy
    version, and the explicit allow/block lists for tools.
    """

    frame_id: str = Field(description="Unique identifier for this frame.")
    task: str = Field(description="The task description associated with this frame.")
    actor: str = Field(description="Identifier of the actor (agent, user, service).")
    environment: str = Field(description="Deployment environment, e.g. 'production'.")
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Tools explicitly permitted in this frame.",
    )
    blocked_tools: list[str] = Field(
        default_factory=list,
        description="Tools explicitly blocked in this frame.",
    )
    policy_version: str = Field(
        description="Version string of the policy set in effect."
    )
    created_at: str = Field(
        default_factory=_now_iso,
        description="ISO-8601 timestamp when this frame was created.",
    )


# ---------------------------------------------------------------------------
# ActionProposal
# ---------------------------------------------------------------------------


class ActionProposal(BaseModel):
    """A proposed action that the agent wishes to execute.

    The action is recorded before any tool is called.  The policy gate
    evaluates the proposal and returns a PolicyDecision.
    """

    action_id: str = Field(description="Unique identifier for this action proposal.")
    run_id: str = Field(description="Run that this proposal belongs to.")
    tool_name: str = Field(description="Name of the tool the agent wants to call.")
    action_type: str = Field(
        description=(
            "Semantic type of the action, e.g. 'read', 'write', 'external_send'."
        )
    )
    target: str = Field(
        description="Target resource or endpoint the action operates on."
    )
    payload: dict = Field(
        default_factory=dict,
        description="Arguments or payload the agent wants to pass to the tool.",
    )
    proposed_at: str = Field(
        default_factory=_now_iso,
        description="ISO-8601 timestamp when this proposal was created.",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional explanation from the agent for why this action is needed.",
    )


# ---------------------------------------------------------------------------
# PolicyDecision
# ---------------------------------------------------------------------------

DecisionResult = Literal["allow", "block", "escalate"]


class PolicyDecision(BaseModel):
    """The outcome of a policy gate evaluation for one ActionProposal.

    The ``deterministic_fingerprint`` field is a stable SHA-256 hash
    derived from the inputs so that the same action + frame + authority
    always produces the same fingerprint, enabling audit verification.
    """

    decision_id: str = Field(description="Unique identifier for this decision.")
    action_id: str = Field(
        description="The ActionProposal this decision applies to."
    )
    run_id: str = Field(description="Run that this decision belongs to.")
    result: DecisionResult = Field(
        description="Policy outcome: 'allow', 'block', or 'escalate'."
    )
    policy_name: str = Field(description="Name of the policy rule that was applied.")
    reason: str = Field(description="Human-readable explanation of the decision.")
    decided_at: str = Field(
        default_factory=_now_iso,
        description="ISO-8601 timestamp when this decision was made.",
    )
    deterministic_fingerprint: str = Field(
        description=(
            "Stable SHA-256 hex digest of the canonical decision inputs.  "
            "Identical inputs always produce the same fingerprint."
        )
    )


# ---------------------------------------------------------------------------
# BlockedAction
# ---------------------------------------------------------------------------


class BlockedAction(BaseModel):
    """Record of an action that was blocked by the policy gate.

    Created automatically whenever a PolicyDecision has result == 'block'.
    """

    blocked_id: str = Field(description="Unique identifier for this blocked-action record.")
    action_id: str = Field(description="The ActionProposal that was blocked.")
    run_id: str = Field(description="Run that this blocked action belongs to.")
    reason: str = Field(description="Why this action was blocked.")
    policy_name: str = Field(description="Policy rule that triggered the block.")
    blocked_at: str = Field(
        default_factory=_now_iso,
        description="ISO-8601 timestamp when this block was recorded.",
    )


# ---------------------------------------------------------------------------
# AuthorityRecord
# ---------------------------------------------------------------------------


class AuthorityRecord(BaseModel):
    """Records the authority granted to an actor for a specific scope.

    Authority records are consulted by the policy gate to decide whether
    privileged action types (e.g. 'write', 'external_send') are permitted.
    """

    authority_id: str = Field(description="Unique identifier for this authority record.")
    run_id: str = Field(description="Run that this authority applies to.")
    actor: str = Field(description="The actor being granted authority.")
    scope: list[str] = Field(
        description="List of permission scopes granted, e.g. ['read', 'write']."
    )
    expires_at: Optional[str] = Field(
        default=None,
        description="Optional ISO-8601 timestamp when this authority expires.",
    )
    source: str = Field(
        description="Where the authority was granted from, e.g. 'user_consent', 'policy_config'."
    )
    created_at: str = Field(
        default_factory=_now_iso,
        description="ISO-8601 timestamp when this record was created.",
    )


# ---------------------------------------------------------------------------
# RelianceRecord
# ---------------------------------------------------------------------------

SourceType = Literal["tool", "database", "file", "api", "user_input", "model_output", "other"]


class RelianceRecord(BaseModel):
    """Records a dependency on an external source or tool during a run.

    Captures which external sources the agent relied on so that auditors
    can trace the origin of information used to produce the final output.
    """

    reliance_id: str = Field(description="Unique identifier for this reliance record.")
    run_id: str = Field(description="Run that this reliance record belongs to.")
    source_name: str = Field(description="Name of the source or tool relied upon.")
    source_type: SourceType = Field(
        description="Category of the source: tool, database, file, api, user_input, model_output, or other."
    )
    scope: str = Field(
        description="Description of what was accessed or consumed from this source."
    )
    referenced_action_id: Optional[str] = Field(
        default=None,
        description="Optional action_id of the ActionProposal that triggered this reliance.",
    )
    created_at: str = Field(
        default_factory=_now_iso,
        description="ISO-8601 timestamp when this record was created.",
    )


# ---------------------------------------------------------------------------
# RunRecord
# ---------------------------------------------------------------------------


class RunRecord(BaseModel):
    """Complete record of a single agent run.

    Aggregates the frame, all proposed actions, all policy decisions,
    authority records, reliance records, and blocked actions produced
    during the run.
    """

    run_id: str = Field(description="Unique identifier for this run.")
    task: str = Field(description="Top-level task description for the run.")
    created_at: str = Field(
        default_factory=_now_iso,
        description="ISO-8601 timestamp when the run was started.",
    )
    frame: Frame = Field(description="Execution frame active for this run.")
    actions: list[ActionProposal] = Field(
        default_factory=list,
        description="All action proposals made during the run.",
    )
    decisions: list[PolicyDecision] = Field(
        default_factory=list,
        description="All policy decisions made during the run.",
    )
    authority_records: list[AuthorityRecord] = Field(
        default_factory=list,
        description="Authority records active during the run.",
    )
    reliance_records: list[RelianceRecord] = Field(
        default_factory=list,
        description="External-source reliance records from the run.",
    )
    blocked_actions: list[BlockedAction] = Field(
        default_factory=list,
        description="Actions that were blocked during the run.",
    )
    completed: bool = Field(
        default=False,
        description="Whether the run has been marked as completed.",
    )
    final_output: Optional[str] = Field(
        default=None,
        description="Final output produced by the agent at the end of the run.",
    )
    replay_bundle_id: Optional[str] = Field(
        default=None,
        description="ID of the ReplayBundle generated for this run, if any.",
    )


# ---------------------------------------------------------------------------
# ReplayBundle
# ---------------------------------------------------------------------------


class ReplayBundle(BaseModel):
    """A self-contained, replayable snapshot of a completed run.

    Contains everything needed to reconstruct what happened during a run:
    the frame, all proposals, decisions, authority, reliance, and blocked
    action records.
    """

    replay_bundle_id: str = Field(description="Unique identifier for this replay bundle.")
    run_id: str = Field(description="The run this bundle was generated from.")
    generated_at: str = Field(
        default_factory=_now_iso,
        description="ISO-8601 timestamp when this bundle was generated.",
    )
    frame: Frame = Field(description="Execution frame for the run.")
    actions: list[ActionProposal] = Field(
        default_factory=list,
        description="All action proposals from the run.",
    )
    decisions: list[PolicyDecision] = Field(
        default_factory=list,
        description="All policy decisions from the run.",
    )
    authority_records: list[AuthorityRecord] = Field(
        default_factory=list,
        description="Authority records active during the run.",
    )
    reliance_records: list[RelianceRecord] = Field(
        default_factory=list,
        description="External-source reliance records from the run.",
    )
    blocked_actions: list[BlockedAction] = Field(
        default_factory=list,
        description="Actions that were blocked during the run.",
    )
    final_output: Optional[str] = Field(
        default=None,
        description="Final output produced by the agent.",
    )

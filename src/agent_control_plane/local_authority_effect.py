"""Opt-in local authority/effect execution-claim contract.

This module does not change the legacy BoundedAuthorizationWorkflow execution
path. It materializes a claim only from a persisted authorized decision plus a
fresh resolution of the same trusted workflow. The claim is not authority by
itself: a participating local authority/effect store must provision it and own
all later invalidating state changes for the profile.
"""
from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from agent_control_plane.bounded import (
    BoundedAuthorizationWorkflow,
    RuntimeDecision,
    RuntimeProposal,
    _iso,
    _parse,
    commitment,
)

LOCAL_AUTHORITY_EFFECT_PROFILE = "urn:cognous:profiles:local-authority-effect:0.1.0-proposed"


class ApprovalProjection(BaseModel):
    approval_ref: str
    role_id: str
    approver: str
    status: Literal["active", "revoked", "unknown"]
    grant_id: str
    grant_revision: str
    proposal_commitment: str
    policy_versions: list[dict]
    observed_at: str


class PolicyProjection(BaseModel):
    ref: str
    version: str
    status: Literal["active", "superseded", "unknown"]
    observed_at: str


class EvidenceProjection(BaseModel):
    obligation_id: str
    source_ref: str
    required: bool
    kind: str
    max_age_seconds: int
    unknown_behavior: str
    state: Literal["current", "stale", "unknown"]
    observed_at: str


class LocalExecutionClaim(BaseModel):
    """Exact execution claim for one participating local atomic profile.

    Possession of this object is not sufficient for execution. The executor must
    locate the same claim in the declared authoritative local store and consume
    it there in the same transaction that commits the protected effect.
    """

    profile: str = LOCAL_AUTHORITY_EFFECT_PROFILE
    claim_id: str
    decision_id: str
    effect_id: str
    institution_id: str
    authority_domain: str
    actor: str
    principal: str
    grant_id: str
    grant_revision: str
    manifest_id: str
    manifest_version: str
    manifest_digest: str
    action_id: str
    adapter_id: str
    target: str
    payload_commitment: str
    requested_permissions: list[str]
    amount: float
    unit: str
    effects: int
    authority_context_id: str
    requirement_id: str
    requirement_commitment: str
    operation_commitment: str
    approval_state: list[ApprovalProjection]
    approval_state_commitment: str
    policy_state: list[PolicyProjection]
    policy_state_commitment: str
    evidence_state: list[EvidenceProjection]
    evidence_state_commitment: str
    authority_state_commitment: str
    budget_id: str
    max_effects: int
    not_before: str
    expires_at: str
    issued_at: str
    decision_input_commitment: str | None = None
    decision_input_profile_version: str | None = None
    source: Literal["trusted_control_plane_workflow"] = "trusted_control_plane_workflow"
    authorizing_by_possession: bool = False
    claim_commitment: str


def _utc(value: str) -> datetime:
    parsed = _parse(value)
    return parsed.astimezone(timezone.utc)


def _operation_payload(proposal: RuntimeProposal, decision: RuntimeDecision) -> dict[str, Any]:
    binding = decision.binding
    if binding is None:
        raise PermissionError("authorized decision is missing an authorization binding")
    return {
        "actor": proposal.actor,
        "principal": proposal.principal,
        "manifest_id": proposal.manifest_id,
        "manifest_version": proposal.manifest_version,
        "manifest_digest": proposal.manifest_digest,
        "action_id": proposal.action_id,
        "adapter_id": proposal.adapter_id,
        "target": proposal.target,
        "payload_commitment": proposal.payload_commitment,
        "requested_permissions": list(proposal.requested_permissions),
        "amount": proposal.amount,
        "unit": proposal.unit,
        "effects": proposal.effects,
        "authority_context_id": proposal.authority_context_ref,
        "requirement_id": proposal.requirement_id,
        "grant_id": binding.grant_id,
        "grant_revision": binding.grant_revision,
    }


def materialize_local_execution_claim(
    workflow: BoundedAuthorizationWorkflow,
    proposal: RuntimeProposal,
    decision: RuntimeDecision,
    *,
    now: datetime,
    claim_id: str | None = None,
    budget_id: str | None = None,
    expires_at: str | None = None,
    decision_input_commitment: str | None = None,
    decision_input_profile_version: str | None = None,
) -> LocalExecutionClaim:
    """Materialize one exact claim from trusted current Control Plane state.

    This helper intentionally performs a fresh workflow resolution. It does not
    close the later check/effect race by itself. The returned claim becomes
    enforceable only when an opt-in local store is declared authoritative for
    subsequent grant/approval/policy/evidence mutations and consumes this claim
    atomically with the effect.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("claim issuance time must be timezone-aware")
    now = now.astimezone(timezone.utc)

    persisted = workflow.records.decision(decision.decision_id)
    if persisted is None or persisted != decision:
        raise PermissionError("decision is not the immutable persisted decision")
    if decision.result != "authorized" or decision.binding is None:
        raise PermissionError("decision is not authorized")

    frozen = proposal.model_copy(deep=True)
    reasons, current = workflow._resolve(frozen, now)
    if reasons or current is None or current != decision.binding:
        raise PermissionError("authorization-critical inputs changed before claim issuance")

    context = workflow.resolver.authority_context(proposal.authority_context_ref or "")
    if not isinstance(context, dict):
        raise PermissionError("authority context unavailable at claim issuance")
    institution = context.get("institution") or {}
    grant = context.get("grant") or {}
    requirement = context.get("requirement") or {}

    approvals: list[ApprovalProjection] = []
    for ref in grant.get("approval_refs", []):
        value = workflow.resolver.approval_status(ref)
        if value is None:
            raise PermissionError("approval state unavailable at claim issuance")
        approvals.append(ApprovalProjection(
            approval_ref=value.approval_ref,
            role_id=value.role_id,
            approver=value.approver,
            status=value.status,
            grant_id=value.grant_id,
            grant_revision=value.grant_revision,
            proposal_commitment=value.proposal_commitment,
            policy_versions=copy.deepcopy(value.policy_versions),
            observed_at=value.observed_at,
        ))

    policies: list[PolicyProjection] = []
    for item in grant.get("policy_versions", []):
        value = workflow.resolver.policy_status(item["ref"])
        if value is None:
            raise PermissionError("policy state unavailable at claim issuance")
        policies.append(PolicyProjection(
            ref=value.ref,
            version=value.version,
            status=value.status,
            observed_at=value.observed_at,
        ))

    evidence: list[EvidenceProjection] = []
    for obligation in requirement.get("evidence", []):
        value = workflow.resolver.evidence_status(obligation["obligation_id"])
        if value is None:
            if obligation.get("required") or obligation.get("unknown_behavior") == "hold_effect":
                raise PermissionError("decision-relevant evidence state unavailable at claim issuance")
            continue
        evidence.append(EvidenceProjection(
            obligation_id=value.obligation_id,
            source_ref=value.source_ref,
            required=bool(obligation.get("required")),
            kind=str(obligation.get("kind", "")),
            max_age_seconds=int(obligation.get("max_age_seconds", 0)),
            unknown_behavior=str(obligation.get("unknown_behavior", "")),
            state=value.state,
            observed_at=value.observed_at,
        ))

    start_candidates = [_utc(grant["not_before"])]
    if proposal.not_before:
        start_candidates.append(_utc(proposal.not_before))
    end_candidates = [_utc(grant["expires_at"])]
    if proposal.expires_at:
        end_candidates.append(_utc(proposal.expires_at))
    if expires_at:
        end_candidates.append(_utc(expires_at))
    not_before_dt = max(start_candidates)
    expires_at_dt = min(end_candidates)
    if expires_at_dt <= not_before_dt or expires_at_dt <= now:
        raise PermissionError("execution claim has no usable validity interval")

    approval_dump = [item.model_dump(mode="json") for item in approvals]
    policy_dump = [item.model_dump(mode="json") for item in policies]
    evidence_dump = [item.model_dump(mode="json") for item in evidence]
    operation_commitment = commitment(_operation_payload(proposal, decision))
    authority_state = {
        "grant_id": current.grant_id,
        "grant_revision": current.grant_revision,
        "requirement_commitment": current.requirement_commitment,
        "approvals": approval_dump,
        "policies": policy_dump,
        "evidence": evidence_dump,
    }

    raw = {
        "profile": LOCAL_AUTHORITY_EFFECT_PROFILE,
        "claim_id": claim_id or str(uuid.uuid4()),
        "decision_id": decision.decision_id,
        "effect_id": decision.effect_id,
        "institution_id": institution.get("institution_id"),
        "authority_domain": institution.get("authority_domain"),
        "actor": proposal.actor,
        "principal": proposal.principal,
        "grant_id": current.grant_id,
        "grant_revision": current.grant_revision,
        "manifest_id": proposal.manifest_id,
        "manifest_version": proposal.manifest_version,
        "manifest_digest": proposal.manifest_digest,
        "action_id": proposal.action_id,
        "adapter_id": proposal.adapter_id,
        "target": proposal.target,
        "payload_commitment": proposal.payload_commitment,
        "requested_permissions": list(proposal.requested_permissions),
        "amount": proposal.amount,
        "unit": proposal.unit,
        "effects": proposal.effects,
        "authority_context_id": current.authority_context_id,
        "requirement_id": current.requirement_id,
        "requirement_commitment": current.requirement_commitment,
        "operation_commitment": operation_commitment,
        "approval_state": approval_dump,
        "approval_state_commitment": commitment(approval_dump),
        "policy_state": policy_dump,
        "policy_state_commitment": commitment(policy_dump),
        "evidence_state": evidence_dump,
        "evidence_state_commitment": commitment(evidence_dump),
        "authority_state_commitment": commitment(authority_state),
        "budget_id": budget_id or f"grant:{current.grant_id}",
        "max_effects": current.effective_max_effects,
        "not_before": _iso(not_before_dt),
        "expires_at": _iso(expires_at_dt),
        "issued_at": _iso(now),
        "decision_input_commitment": decision_input_commitment,
        "decision_input_profile_version": decision_input_profile_version,
        "source": "trusted_control_plane_workflow",
        "authorizing_by_possession": False,
    }
    raw["claim_commitment"] = commitment(raw)
    return LocalExecutionClaim.model_validate(raw)


def verify_local_execution_claim(claim: LocalExecutionClaim | dict[str, Any]) -> bool:
    value = (
        claim.model_dump(mode="json", exclude_none=False)
        if isinstance(claim, LocalExecutionClaim)
        else copy.deepcopy(claim)
    )
    supplied = value.pop("claim_commitment", None)
    if value.get("profile") != LOCAL_AUTHORITY_EFFECT_PROFILE:
        return False
    if value.get("source") != "trusted_control_plane_workflow":
        return False
    if value.get("authorizing_by_possession") is not False:
        return False
    return supplied == commitment(value)

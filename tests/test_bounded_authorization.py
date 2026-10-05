"""Acceptance tests for the bounded authorization-to-effect pilot."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from agent_control_plane.bounded import (
    ApprovalStatus,
    BoundedAuthorizationWorkflow,
    BoundedRecordStore,
    ConflictStatus,
    EvidenceStatus,
    GrantStatus,
    IdentityStatus,
    LocalRefundDestination,
    MandateStatus,
    PolicyStatus,
    RuntimeProposal,
    SyntheticResolver,
    commitment,
)

NOW = datetime(2026, 10, 5, 19, 0, tzinfo=timezone.utc)
PROFILE = "urn:cognous:alvorada:public-stack-profile:0.1.0"
INSTITUTION = "urn:cognous:institution:synthetic-customer-service"
ACTOR = "urn:cognous:identity:refund-agent-1"
PRINCIPAL = "urn:cognous:principal:refund-service"
ISSUER = "urn:cognous:principal:synthetic-governor"
ISSUER_ROLE = "urn:cognous:role:refund-governor"
POLICY_REF = "urn:cognous:policy:refund-policy"
POLICY_VERSION = "1.0"


FIXTURE = Path(__file__).parent / "fixtures" / "refund_integration_v1_1.manifest.json"


def manifest():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))

def proposal(tier="T1", *, correlation_id="case-1"):
    m = manifest()
    if tier == "T1":
        action_id = "urn:cognous:action:refund-issue-routine-v1"
        target = "urn:cognous:synthetic-account:customer-001"
        payload = {"customer_id": "customer-001", "refund_reason": "duplicate"}
        perm = "refund.issue.routine"
        amount = 50.0
        requirement = "urn:cognous:authority-requirement:refund-routine-v1"
    else:
        action_id = "urn:cognous:action:refund-issue-high-v1"
        target = "urn:cognous:synthetic-account:customer-002"
        payload = {
            "customer_id": "customer-002",
            "refund_reason": "service failure",
            "case_reference": "case-002",
        }
        perm = "refund.issue.high"
        amount = 500.0
        requirement = "urn:cognous:authority-requirement:refund-high-v1"
    return RuntimeProposal(
        manifest_id=m["manifest_id"],
        manifest_version=m["manifest_version"],
        manifest_digest=commitment(m),
        actor=ACTOR,
        principal=PRINCIPAL,
        action_id=action_id,
        adapter_id="urn:cognous:adapter:synthetic-refund-v1",
        target=target,
        payload=payload,
        payload_commitment=commitment(payload),
        requested_permissions=[perm],
        amount=amount,
        unit="USD",
        effects=1,
        authority_context_ref=PROFILE,
        requirement_id=requirement,
        correlation_id=correlation_id,
        run_id="run-1",
        evidence_refs=["urn:cognous:evidence:refund-entitlement"],
    )


def authority_context(p, *, tier="T1", with_grant=True, delegated=False):
    role = (
        "urn:cognous:role:customer-service-supervisor"
        if tier == "T1"
        else "urn:cognous:role:refund-authorizer"
    )
    action_name = "refund_issue_routine" if tier == "T1" else "refund_issue_high_consequence"
    grant_id = "urn:cognous:grant:routine-1" if tier == "T1" else "urn:cognous:grant:high-1"
    evidence = [{
        "obligation_id": "urn:cognous:evidence:refund-entitlement",
        "kind": "authorization",
        "source_ref": "urn:cognous:source:entitlement",
        "max_age_seconds": 300,
        "required": True,
        "unknown_behavior": "hold_effect",
    }]
    if tier == "T2":
        evidence.append({
            "obligation_id": "urn:cognous:evidence:refund-approval",
            "kind": "authorization",
            "source_ref": "urn:cognous:source:approval",
            "max_age_seconds": 300,
            "required": True,
            "unknown_behavior": "hold_effect",
        })
    evidence.append({
        "obligation_id": "urn:cognous:evidence:optional-context",
        "kind": "context",
        "source_ref": "urn:cognous:source:optional",
        "max_age_seconds": 300,
        "required": False,
        "unknown_behavior": "preserve_if_other_basis_suffices",
    })
    context = {
        "schema_version": "0.1.0",
        "interface_status": "proposed_pending_governor_review",
        "context_id": "urn:cognous:authority-context:pilot-1",
        "institution": {
            "institution_id": INSTITUTION,
            "authority_domain": "customer-refunds",
            "authority_basis_ref": "urn:cognous:authority-basis:synthetic",
            "authority_mode": "principle_inspired",
        },
        "principal": PRINCIPAL,
        "acting_identity": ACTOR,
        "accountable_human_role": {
            "role_id": "urn:cognous:role:accountable-human",
            "human_principal": "urn:cognous:principal:human-1",
            "mandate_ref": "urn:cognous:mandate:human-1",
        },
        "requirement": {
            "requirement_id": p.requirement_id,
            "governing_sources": [{
                "ref": "urn:cognous:policy:refund-policy",
                "version": POLICY_VERSION,
                "provision": "refund",
                "standing": "local_policy",
            }],
            "permissions": [{
                "action": action_name,
                "targets": [p.target],
                "data_scopes": list(p.requested_permissions),
                "max_amount": 100.0 if tier == "T1" else 1000.0,
                "unit": "USD",
                "max_effects": 1,
            }],
            "approvals": [{"role_id": role, "independent_of_actor": True}],
            "evidence": evidence,
            "consequence": {
                "tier": tier,
                "rationale": "Synthetic test tier.",
                "profile_ref": f"urn:cognous:consequence:{tier}",
            },
        },
        "conflicts": {
            "precedence_refs": ["urn:cognous:policy:refund-policy"],
            "incompatible_role_pairs": [],
            "escalation_ref": "urn:cognous:procedure:escalation",
            "appeal_ref": "urn:cognous:procedure:appeal",
            "continuity_ref": "urn:cognous:procedure:continuity",
            "remedy_ref": "urn:cognous:procedure:remedy",
        },
        "supporting_evidence_refs": [],
        "change": {"kind": "none", "proposal_ref": None, "adoption_record_ref": None},
    }
    if with_grant:
        context["grant"] = {
            "grant_id": grant_id,
            "revision": "1",
            "requirement_id": p.requirement_id,
            "issuer": ISSUER,
            "issuer_role": ISSUER_ROLE,
            "issuance_record_ref": "urn:cognous:issuance:1",
            "grantee": PRINCIPAL,
            "acting_identity": ACTOR,
            "issued_at": (NOW - timedelta(hours=1)).isoformat(),
            "not_before": (NOW - timedelta(minutes=30)).isoformat(),
            "expires_at": (NOW + timedelta(hours=1)).isoformat(),
            "status_ref": "urn:cognous:status:grant-1",
            "policy_versions": [{"ref": POLICY_REF, "version": POLICY_VERSION}],
            "permissions": [{
                "action": action_name,
                "targets": [p.target],
                "data_scopes": list(p.requested_permissions),
                "max_amount": 100.0 if tier == "T1" else 1000.0,
                "unit": "USD",
                "max_effects": 1,
            }],
            "delegation": {
                "parent_grant_id": "urn:cognous:grant:parent" if delegated else None,
                "may_delegate": False,
                "remaining_depth": 0,
            },
            "approval_refs": [f"urn:cognous:approval:{tier.lower()}-1"],
        }
    return context


def resolver_for(p, *, tier="T1", with_grant=True, delegated=False):
    ctx = authority_context(p, tier=tier, with_grant=with_grant, delegated=delegated)
    statuses = {}
    approvals = {}
    if with_grant:
        grant = ctx["grant"]
        statuses[grant["grant_id"]] = GrantStatus(
            grant_id=grant["grant_id"],
            revision=grant["revision"],
            status="active",
            observed_at=NOW.isoformat(),
            version="status-v1",
            authority_basis_ref="urn:cognous:authority-basis:synthetic",
        )
        role = ctx["requirement"]["approvals"][0]["role_id"]
        approval_ref = grant["approval_refs"][0]
        approvals[approval_ref] = ApprovalStatus(
            approval_ref=approval_ref,
            role_id=role,
            approver="urn:cognous:principal:reviewer-1",
            grant_id=grant["grant_id"],
            grant_revision=grant["revision"],
            proposal_commitment=commitment(p.model_dump(mode="json", exclude_none=False)),
            policy_versions=copy.deepcopy(grant["policy_versions"]),
            observed_at=NOW.isoformat(),
        )
    return SyntheticResolver(
        contexts={PROFILE: ctx},
        statuses=statuses,
        identities={
            ACTOR: IdentityStatus(
                identity=ACTOR,
                principal=PRINCIPAL,
                authenticated=True,
                delegation_valid=True,
                observed_at=NOW.isoformat(),
                chain=["urn:cognous:grant:parent"] if delegated else [],
            )
        },
        mandates={
            f"{ISSUER}|{ISSUER_ROLE}": MandateStatus(
                issuer=ISSUER,
                issuer_role=ISSUER_ROLE,
                mandate_valid=True,
                observed_at=NOW.isoformat(),
            )
        },
        approvals=approvals,
        policies={
            POLICY_REF: PolicyStatus(
                ref=POLICY_REF,
                version=POLICY_VERSION,
                status="active",
                observed_at=NOW.isoformat(),
            )
        },
        conflicts={
            p.requirement_id: ConflictStatus(
                requirement_id=p.requirement_id,
                state="clear",
                observed_at=NOW.isoformat(),
            )
        },
        role_aliases={
            "customer-service-supervisor": "urn:cognous:role:customer-service-supervisor",
            "refund-authorizer": "urn:cognous:role:refund-authorizer",
        },
        evidence={
            "urn:cognous:evidence:refund-entitlement": EvidenceStatus(
                obligation_id="urn:cognous:evidence:refund-entitlement",
                state="current",
                observed_at=NOW.isoformat(),
                source_ref="urn:cognous:source:entitlement",
            ),
            "urn:cognous:evidence:refund-approval": EvidenceStatus(
                obligation_id="urn:cognous:evidence:refund-approval",
                state="current",
                observed_at=NOW.isoformat(),
                source_ref="urn:cognous:source:approval",
            ),
            "urn:cognous:evidence:optional-context": EvidenceStatus(
                obligation_id="urn:cognous:evidence:optional-context",
                state="unknown",
                observed_at=NOW.isoformat(),
                source_ref="urn:cognous:source:optional",
            ),
        },
    )


def workflow(tmp_path, p, *, tier="T1", resolver=None):
    resolver = resolver or resolver_for(p, tier=tier)
    return BoundedAuthorizationWorkflow(
        manifest=manifest(),
        resolver=resolver,
        destination=LocalRefundDestination(tmp_path / "destination.json"),
        records=BoundedRecordStore(tmp_path / "run.json", "run-1"),
    )


def test_valid_t1_succeeds_and_changes_destination(tmp_path):
    p = proposal()
    flow = workflow(tmp_path, p)
    decision = flow.decide(p, now=NOW)
    assert decision.result == "authorized"

    attempt, observed = flow.execute(
        p, decision, adapter_id=p.adapter_id, now=NOW
    )
    assert attempt.status == "acknowledged"
    assert observed.state == "applied"
    assert observed.destination_state["amount"] == 50.0
    assert len(flow.destination.snapshot()["effects"]) == 1


def test_t2_requires_additional_approval(tmp_path):
    p = proposal("T2")
    r = resolver_for(p, tier="T2")
    r.approvals.clear()
    decision = workflow(tmp_path, p, tier="T2", resolver=r).decide(p, now=NOW)
    assert decision.result == "hold"
    assert "required_approval_missing" in decision.reasons


def test_requirement_only_or_copied_verification_json_cannot_authorize(tmp_path):
    p = proposal()
    r = resolver_for(p, with_grant=False)
    r.contexts[PROFILE]["supporting_evidence_refs"] = [
        "urn:cognous:bitrep:verification-result:copied-json",
        "urn:cognous:index:block:included",
    ]
    decision = workflow(tmp_path, p, resolver=r).decide(p, now=NOW)
    assert decision.result == "hold"
    assert "issued_grant_missing" in decision.reasons


@pytest.mark.parametrize("field", ["payload", "target", "actor", "adapter", "manifest"])
def test_substitution_prevents_effect(tmp_path, field):
    p = proposal()
    flow = workflow(tmp_path, p)
    decision = flow.decide(p, now=NOW)
    assert decision.result == "authorized"
    mutated = p.model_copy(deep=True)
    adapter_id = p.adapter_id
    if field == "payload":
        mutated.payload["refund_reason"] = "changed"
    elif field == "target":
        mutated.target = "urn:cognous:synthetic-account:attacker"
    elif field == "actor":
        mutated.actor = "urn:cognous:identity:other"
    elif field == "adapter":
        adapter_id = "urn:cognous:adapter:other"
    else:
        mutated.manifest_digest = "sha256:" + "0" * 64
    with pytest.raises(PermissionError):
        flow.execute(mutated, decision, adapter_id=adapter_id, now=NOW)
    assert flow.destination.snapshot()["effects"] == {}


def test_revocation_expiry_stale_status_and_policy_change_hold(tmp_path):
    p = proposal()
    r = resolver_for(p)
    grant = r.contexts[PROFILE]["grant"]

    r.statuses[grant["grant_id"]].status = "revoked"
    assert "grant_not_active" in workflow(tmp_path / "a", p, resolver=r).decide(p, now=NOW).reasons

    r = resolver_for(p)
    r.contexts[PROFILE]["grant"]["expires_at"] = (NOW - timedelta(seconds=1)).isoformat()
    assert "grant_outside_validity" in workflow(tmp_path / "b", p, resolver=r).decide(p, now=NOW).reasons

    r = resolver_for(p)
    r.statuses[grant["grant_id"]].observed_at = (NOW - timedelta(minutes=5)).isoformat()
    assert "grant_status_stale" in workflow(tmp_path / "c", p, resolver=r).decide(p, now=NOW).reasons

    r = resolver_for(p)
    r.policies[POLICY_REF].version = "2.0"
    assert "policy_stale_or_changed" in workflow(tmp_path / "d", p, resolver=r).decide(p, now=NOW).reasons


def test_delegation_cannot_widen_or_survive_invalid_parent(tmp_path):
    p = proposal()
    r = resolver_for(p, delegated=True)
    r.identities[ACTOR].delegation_valid = False
    decision = workflow(tmp_path / "a", p, resolver=r).decide(p, now=NOW)
    assert "identity_or_delegation_invalid" in decision.reasons

    base = proposal()
    r2 = resolver_for(base, delegated=True)
    p2 = base.model_copy(deep=True)
    p2.requested_permissions.append("refund.issue.admin")
    approval_ref = r2.contexts[PROFILE]["grant"]["approval_refs"][0]
    r2.approvals[approval_ref].proposal_commitment = commitment(
        p2.model_dump(mode="json", exclude_none=False)
    )
    decision2 = workflow(tmp_path / "b", p2, resolver=r2).decide(p2, now=NOW)
    assert decision2.result == "hold"
    assert "grant_scope_mismatch" in decision2.reasons


def test_stale_required_evidence_holds_but_optional_unknown_does_not(tmp_path):
    p = proposal()
    r = resolver_for(p)
    r.evidence["urn:cognous:evidence:refund-entitlement"].observed_at = (
        NOW - timedelta(minutes=10)
    ).isoformat()
    decision = workflow(tmp_path / "a", p, resolver=r).decide(p, now=NOW)
    assert "required_evidence_stale" in decision.reasons

    r2 = resolver_for(p)
    decision2 = workflow(tmp_path / "b", p, resolver=r2).decide(p, now=NOW)
    assert decision2.result == "authorized"


def test_unresolved_conflict_holds_effect(tmp_path):
    p = proposal()
    r = resolver_for(p)
    r.conflicts[p.requirement_id].state = "conflict"
    decision = workflow(tmp_path, p, resolver=r).decide(p, now=NOW)
    assert decision.result == "hold"
    assert "authority_conflict_unresolved" in decision.reasons


def test_changed_policy_after_decision_prevents_effect(tmp_path):
    p = proposal()
    r = resolver_for(p)
    flow = workflow(tmp_path, p, resolver=r)
    decision = flow.decide(p, now=NOW)
    r.policies[POLICY_REF].version = "2.0"
    with pytest.raises(PermissionError):
        flow.execute(p, decision, adapter_id=p.adapter_id, now=NOW)
    assert flow.destination.snapshot()["effects"] == {}


def test_lost_ack_restart_reconciles_without_duplicate(tmp_path):
    p = proposal()
    r = resolver_for(p)
    flow = workflow(tmp_path, p, resolver=r)
    decision = flow.decide(p, now=NOW)
    attempt, observed = flow.execute(
        p, decision, adapter_id=p.adapter_id, now=NOW, lose_ack=True
    )
    assert attempt.status == "unknown"
    assert observed.state == "applied"

    restarted = BoundedAuthorizationWorkflow(
        manifest=manifest(),
        resolver=r,
        destination=LocalRefundDestination(tmp_path / "destination.json"),
        records=BoundedRecordStore(tmp_path / "run.json", "run-1"),
    )
    assert restarted.reconcile(decision.effect_id).result == "applied"
    retry, observed2 = restarted.execute(
        p, decision, adapter_id=p.adapter_id, now=NOW
    )
    assert retry.status == "acknowledged"
    assert retry.acknowledgement["reconciled_existing"] is True
    assert observed2.state == "applied"
    assert len(restarted.destination.snapshot()["effects"]) == 1
    assert restarted.records.load().decisions[0].decision_id == decision.decision_id


def test_partial_delivery_holds_instead_of_blind_retry(tmp_path):
    p = proposal()
    flow = workflow(tmp_path, p)
    decision = flow.decide(p, now=NOW)
    attempt, observed = flow.execute(
        p, decision, adapter_id=p.adapter_id, now=NOW, partial=True
    )
    assert attempt.status == "partial"
    assert observed.state == "partial"
    assert flow.reconcile(decision.effect_id).result == "hold"
    retry, observed2 = flow.execute(p, decision, adapter_id=p.adapter_id, now=NOW)
    assert retry.status == "partial"
    assert observed2.state == "partial"
    assert len(flow.destination.snapshot()["effects"]) == 1


def test_duplicate_submission_does_not_duplicate_effect(tmp_path):
    p = proposal()
    flow = workflow(tmp_path, p)
    decision = flow.decide(p, now=NOW)
    first, _ = flow.execute(p, decision, adapter_id=p.adapter_id, now=NOW)
    second, _ = flow.execute(p, decision, adapter_id=p.adapter_id, now=NOW)
    assert first.status == "acknowledged"
    assert second.acknowledgement["reconciled_existing"] is True
    assert first.attempt_id != second.attempt_id
    assert len(flow.destination.snapshot()["effects"]) == 1


def test_concurrent_distinct_effects_respect_local_cumulative_cap(tmp_path):
    p1 = proposal(correlation_id="case-1")
    p2 = proposal(correlation_id="case-2")
    r = resolver_for(p1)
    approval_ref = r.contexts[PROFILE]["grant"]["approval_refs"][0]
    p2_commitment = commitment(p2.model_dump(mode="json", exclude_none=False))

    # One synthetic approval record can only bind one operation, so replace it
    # immediately before each decision, then execute both already-authorized
    # effects concurrently against the same local grant budget.
    flow = workflow(tmp_path, p1, resolver=r)
    d1 = flow.decide(p1, now=NOW)
    r.approvals[approval_ref].proposal_commitment = p2_commitment
    d2 = flow.decide(p2, now=NOW)
    assert d1.result == d2.result == "authorized"

    # Restore independent operation binding for revalidation by using two
    # resolver views that share the same destination but distinct approvals.
    r1 = resolver_for(p1)
    r2 = resolver_for(p2)
    f1 = BoundedAuthorizationWorkflow(
        manifest=manifest(), resolver=r1, destination=flow.destination,
        records=BoundedRecordStore(tmp_path / "run1.json", "run-1")
    )
    f2 = BoundedAuthorizationWorkflow(
        manifest=manifest(), resolver=r2, destination=flow.destination,
        records=BoundedRecordStore(tmp_path / "run2.json", "run-2")
    )
    d1 = f1.decide(p1, now=NOW)
    d2 = f2.decide(p2, now=NOW)

    def run(f, p, d):
        return f.execute(p, d, adapter_id=p.adapter_id, now=NOW)[0].status

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda args: run(*args), [(f1, p1, d1), (f2, p2, d2)]))
    assert sorted(statuses) == ["acknowledged", "failed"]
    state = flow.destination.snapshot()
    assert len(state["effects"]) == 1
    grant_id = r.contexts[PROFILE]["grant"]["grant_id"]
    assert state["grant_effect_counts"][grant_id] == 1

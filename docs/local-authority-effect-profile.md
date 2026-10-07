# Local authority/effect execution-claim profile

Status: **implemented proposal on Worker 21 branch; opt-in; not hub-selected**.

Profile: `urn:cognous:profiles:local-authority-effect:0.1.0-proposed`.

## Purpose

This contract is the Control Plane side of a bounded same-host profile that can
order authorization-critical invalidation against one protected SQLite effect.
The legacy `BoundedAuthorizationWorkflow.execute()` path is unchanged.

A claim is materialized only from:

- an immutable persisted `authorized` decision;
- the exact `AuthorizationBinding`;
- a fresh resolution of the same trusted workflow;
- the institution/domain and grant from the trusted Authority Context;
- current approval, policy and decision-relevant evidence state.

Possession of the claim does not authorize execution. A participating local
authority/effect store must provision the claim and become authoritative for all
subsequent invalidating writes in the profile.

## Claim bindings

The claim binds:

- institution and authority domain;
- actor, principal, grant ID and revision;
- decision and effect IDs;
- Manifest, action, adapter, target and exact operation commitment;
- approval state and commitment;
- policy state and commitment;
- evidence obligations/state/freshness inputs and commitment;
- requirement commitment;
- budget ID and maximum effects;
- not-before and expiry;
- profile version and complete claim commitment.

The optional `decision_input_commitment` and
`decision_input_profile_version` fields are opaque compatibility hooks for
Worker 20 PR #11. Worker 21 does not consume that unaccepted branch and does not
redefine its Decision Input Commitment Record.

## Trust boundary

`materialize_local_execution_claim()` is a trusted-host operation. It is not an
agent message parser and does not accept an arbitrary assertion as an execution
claim. It checks the persisted decision and performs a fresh Control Plane
resolution before emitting the claim.

The claim is still not cryptographic authority and does not solve the
check/effect race alone. The corresponding executor profile must store the claim
in the same authoritative SQLite database as mutable authority state and the
protected effect, then validate and consume it in the effect transaction.

## Compatibility

- No existing Control Plane schema changes.
- No changes to `RuntimeDecision`, `AuthorizationBinding` or
  `BoundedRunRecord`.
- Existing consumers remain compatible.
- The existing execution path remains selected unless an integrator explicitly
  opts into the new local profile.
- Worker 20's proposal remains independent and non-authorizing.

## Not claimed

This profile does not establish production identity, source authenticity,
distributed transactions, remote revocation, universal mediation, external
destination atomicity, EBL-Core conformance, or production readiness.

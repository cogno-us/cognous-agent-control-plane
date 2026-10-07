# Worker 21 - local authority/effect claim contract

## Baseline

Starting main: `467446356e213e6d821cc2288cb9ade57b581adc`.

Branch: `worker21/local-authority-effect-profile`.

Worker 20 PR #11 is now merged on Control Plane `main` at
`29337fe900d3b2da5656c77d56d70f18feb190b8`. That Decision Input
Commitment profile remains non-authorizing. Worker 21 does not silently adopt it
into this execution path; the local claim keeps only opaque optional
`decision_input_commitment` and `decision_input_profile_version` linkage
fields.

## Contract choice

The Control Plane owns claim issuance semantics, not the effect transaction.
The enforceable path is `provision_local_execution_claim()`: the authority
source must hold a trusted mutation-exclusion handoff while the final resolve,
coherent snapshot capture, active/current projection validation, claim
construction and destination provisioning all occur. A separate ordinary
recheck without that handoff is explicitly insufficient.

The claim binds exact operation content, institution/domain, actor/principal,
grant identity/revision, requirement commitment, current approvals, policy state,
decision-relevant evidence state, budget/effect limit and validity interval.

The claim is explicitly non-authorizing by possession. Atomic enforcement requires
a participating executor store that is authoritative for subsequent invalidating
writes and consumes the claim in the same transaction as the protected effect.

## Compatibility

- No change to `RuntimeProposal`, `RuntimeDecision`,
  `AuthorizationBinding` or `BoundedRunRecord`.
- Legacy `BoundedAuthorizationWorkflow.execute()` is unchanged.
- Existing consumers need not understand the new module.
- Worker 20's proposed record can later be linked without redefining its schema.

## Focused validation

Command:

```bash
pytest -q tests/test_local_authority_effect_profile.py
```

The branch supplies focused tests for exact claim binding, tamper rejection,
changed-authority refusal before issuance, grant-bounded expiry, invalidation
between successful final resolve and snapshot capture, and proof that
provisioning occurs inside the trusted handoff boundary. Final CI
results must be taken from the PR head; no local execution result is asserted by
this checkpoint until CI is observed.

## Limits

No production identity, source authentication, distributed transaction,
destination atomicity, complete mediation, EBL-Core conformance or hub adoption.


## Hardened validation checkpoint

At hardened head `6c7b49138134eeb0d6e37e1b99a36a49cc42218e`,
Tests run `37639954501` completed successfully on Python 3.11 and 3.12.
Python 3.12 reported **177 passed**, including **7** local authority/effect
profile tests. Worker 20's merged non-authorizing profile tests are present in
the PR merge test context but are not treated as execution authority.

This result precedes this evidence-only checkpoint commit. The final PR head must
be rerun separately; that final result is recorded in the PR review handoff
without rewriting this historical checkpoint.

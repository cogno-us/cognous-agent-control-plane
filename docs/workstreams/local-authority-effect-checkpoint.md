# Worker 21 - local authority/effect claim contract

## Baseline

Starting main: `467446356e213e6d821cc2288cb9ade57b581adc`.

Branch: `worker21/local-authority-effect-profile`.

Worker 20 PR #11 was reviewed at `7294da2e783b4a7f058b3e1ecdefd2cfaf1ddfce`.
Its Decision Input Commitment Record remains proposal-only and non-authorizing.
Worker 21 does not consume that branch. The local claim reserves only opaque
`decision_input_commitment` and `decision_input_profile_version` fields.

## Contract choice

The Control Plane owns claim materialization semantics, not the effect transaction.
A claim is emitted only from an immutable persisted authorized decision whose
fresh resolution still equals the stored `AuthorizationBinding`.

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
changed-authority refusal before issuance and grant-bounded expiry. Final CI
results must be taken from the PR head; no local execution result is asserted by
this checkpoint until CI is observed.

## Limits

No production identity, source authentication, distributed transaction,
destination atomicity, complete mediation, EBL-Core conformance or hub adoption.

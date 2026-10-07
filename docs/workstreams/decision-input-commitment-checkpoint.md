# Worker 20 — decision-input commitment profile checkpoint

Status: **proposal complete on isolated branch; runtime adoption deferred; do not merge as an enforcement claim**.

Branch: `worker20/decision-input-commitment-profile`.

## Reviewed revisions

Primary Control Plane main / branch base reviewed: `248d899634d9db3518e831bc7ab568a48733f825`.

Consumers / integration state reviewed:

- Replay Bundle main: `043830b56595cecddfa65c064afd1c0b95e64792`.
- Governance Evidence Pack main: `de6b9e071df49fc3e0c1254d39b5c94cced554f0`.
- Open Control Stack main / lock reviewed: `5737267d94d2b445735c95e8480a31de73a2abe8`.
- Hub-selected Control Plane: `248d899634d9db3518e831bc7ab568a48733f825`.
- Hub-selected Replay: `043830b56595cecddfa65c064afd1c0b95e64792`.
- Hub-selected Evidence Pack: `de6b9e071df49fc3e0c1254d39b5c94cced554f0`.
- Hub-selected Manifest: `46c950bed37fe3812000895430bc0312d29e37ce`.
- Hub-selected executor: `177354e959cc78c59c1a776f018cfbfbf28c927b`.
- Hub-selected Alvorada/GAX: `9984d9011568ccdf3d562fa9760ad41368947b34`.

Open PR review at branch creation:

- Control Plane: none.
- Replay: PRs #5 and #6 remained open; neither was consumed.
- Governance Evidence Pack: PRs #5 and #6 remained open; neither was consumed.
- Hub: none.

Repository `CONTRIBUTING.md`, current README, bounded authorization/effect contract, current models/tests, consumer importer/model code, and hub `component-lock.json` were inspected before editing.

## Research input

Reviewed: *From Intent to Execution Grant: An Execution-Boundary Conformance Profile for High-Risk AI Actions* (arXiv:2609.11596v1, 10 Sep 2026).

Used as research input only. No EBL conformance claim is made and no EBL object naming was inserted into the live runtime.

Findings carried into this proposal:

- a version label alone is not policy-content/evaluation-semantics identity;
- evidence must be related to explicit obligations, and complete materialized evidence must be committed if later verification is expected;
- decision evaluation should be closed over explicit candidate, policy, evidence, context and time inputs;
- obligation origin/resolution semantics must survive operational-policy changes;
- a compatible or "stricter" operational-policy update does not silently preserve an earlier allow/grant;
- derivation/replay consistency is not external truth verification;
- validation, permission consumption and protected effect are a separate execution-boundary/linearization problem owned by Worker 19.

## Verified observations against current Cognous code

1. **PolicyStatus gap confirmed.** `PolicyStatus` currently binds `ref`, `version`, `status`, `observed_at`, institution and domain. It does not bind policy contents or policy evaluation semantics.
2. **EvidenceStatus gap confirmed.** `EvidenceStatus` currently binds obligation ID, state, observation time, source ref, institution and domain. It does not commit the materialized evidence content or provenance.
3. **Existing useful commitments confirmed.** Manifest, payload, full proposal, requirement and role-mapping commitments already provide meaningful bindings and are reused conceptually rather than replaced.
4. **Replay independence limit confirmed.** Reconstruction semantics explicitly set `policy_reevaluation=false` and `independent_effect_verification=false`; importer checks record consistency and selected commitments but does not independently re-run institutional authorization.
5. **Evidence Pack independence limit confirmed.** The importer distinguishes locally computed artifact hashes/semantic import checks from operational effectiveness, independent audit and independent real-world effect verification.
6. **Canonical hashing limit confirmed.** Control Plane, Replay and Evidence Pack use sorted compact UTF-8 Python JSON with NaN rejected. No current evidence establishes cross-language equivalence or Unicode/numeric normalization beyond that behavior.

## Delivered proposal

New files only:

- `docs/decision-input-commitment-profile.md`
- `src/agent_control_plane/decision_input_profile.py`
- `conformance/decision-input-commitment-vectors.json`
- `tests/test_decision_input_commitment_profile.py`
- `tools/verify_decision_input_commitment.py`
- `docs/workstreams/decision-input-commitment-checkpoint.md`

No live authorization file, producer schema, dependency pin, CI workflow, Worker 19 artifact, refund intent registry, or consumer repository was modified.

## Design choice

The smallest compatible extension is a versioned **non-authorizing sidecar record**, not a new `RuntimeDecision` / `BoundedRunRecord` field. It binds exact candidate, institutional requirements, policy content/evaluation semantics, obligation origin, evidence content/provenance, context, explicit adjudication time, resolver/classification semantics, assurance class, decision-input commitment and reason precedence.

This avoids changing the existing producer wire contract. A later Replay revision can map the sidecar into generic Reconstruction `SourceRecord` / `CommitmentRecord` structures, while a later Evidence Pack transformation can retain it with explicit provenance/verification limits.

## Tests executed

Local proposed-profile test command:

```text
pytest -q tests/test_decision_input_commitment_profile.py
```

Outcome:

```text
16 passed in 0.05s
```

Standalone verifier baseline check:

```text
python tools/verify_decision_input_commitment.py <baseline-record.json>
```

Outcome:

```json
{"authorizing": false, "independent_external_truth_verified": false, "valid": true}
```

The full emitted verifier result also reported both required obligations as `VALID` and returned the expected baseline record commitment.

Coverage includes 13 record vectors plus canonicalization/malformed-value tests. The vector file is explicitly labeled `proposed-profile-tests` with `runtime_enforcement_claim=false` and `independent_external_truth_claim=false`.

These tests establish only the behavior of the standalone proposed verifier and vectors. They do not prove current Control Plane enforcement, EBL conformance, independent implementation equivalence, source authentication, evidence truth, complete mediation, permission-consumption atomicity, effect occurrence, or outcome correctness.

## Deferred implementation work

Deferred to a later runtime/consumer batch:

- durable emission/storage of the sidecar tied atomically enough to the RuntimeDecision for the intended claim;
- authenticated retrieval/materialization of policy contents, evaluation semantics, evidence contents and provenance;
- adoption of a runtime primary-reason contract;
- effect-time comparison / fresh re-adjudication using adopted decision-input commitments;
- Replay revision-pinned importer support;
- Evidence Pack transformation support;
- cross-language canonicalization vectors/implementation before portability claims;
- integration qualification and hub pin advancement;
- authority/effect linearization and permission-consumption work owned by Worker 19.

## Claim boundary

This branch proposes a contract and executable conformance vectors. It does **not** claim EBL conformance, production runtime enforcement, independent external truth verification, or that the sidecar itself carries authority.

# Worker 20 — decision-input commitment profile checkpoint

Status: **PR #11 hardened; proposal remains non-authorizing; adoption deferred; do not merge as an enforcement claim**.

Branch: `worker20/decision-input-commitment-profile`.

## Reviewed revisions

Original branch base / selected Control Plane revision: `248d899634d9db3518e831bc7ab568a48733f825`.

Consumer / hub revisions previously reviewed and unchanged by this hardening pass:

- Replay Bundle: `043830b56595cecddfa65c064afd1c0b95e64792`.
- Governance Evidence Pack: `de6b9e071df49fc3e0c1254d39b5c94cced554f0`.
- Open Control Stack lock reviewed at `5737267d94d2b445735c95e8480a31de73a2abe8`.
- Manifest: `46c950bed37fe3812000895430bc0312d29e37ce`.
- Executor: `177354e959cc78c59c1a776f018cfbfbf28c927b`.
- Alvorada/GAX: `9984d9011568ccdf3d562fa9760ad41368947b34`.

No dependency pin was advanced. No Replay, Evidence Pack, hub, Worker 19, refund-intent-registry, live runtime schema, or authorization-path file was modified.

## Review findings reproduced

The pre-hardening verifier permitted or mishandled five classes:

1. **Source mismatch** — an evidence item naming an obligation could use a different `source_ref`; classification did not enforce the obligation's admissible source.
2. **Future-dated evidence** — freshness calculation could treat an observation after `evaluation_time` as current because a negative age did not exceed `max_age_seconds`.
3. **Resolver/obligation semantics mismatch** — resolver semantics were committed, and obligation semantics were committed, but the verifier did not require them to denote the same supported implementation.
4. **Malformed freshness bounds** — non-integer/negative values could bypass or ambiguously affect classification because the classifier conditionally interpreted only non-negative integers.
5. **Non-boolean required flags** — only `required is True` triggered required-evidence enforcement, so other truthy representations were not rejected structurally.

These were semantic validation defects in the proposed standalone profile, not findings against the current live `BoundedAuthorizationWorkflow`.

## Hardening changes

### Field validation before classification

Obligations now require:

- non-empty string IDs, policy origin, source ref and resolver-semantics ID;
- `required` of exact boolean type;
- `max_age_seconds` of exact integer type, non-negative and not boolean;
- SHA-256 resolver-semantics commitment;
- an existing policy origin.

Evidence items now require:

- non-empty evidence/source IDs;
- non-empty duplicate-free string `obligation_ids`;
- only known obligations;
- declared state in `current | unknown | conflict`;
- timezone-aware parseable `observed_at`;
- provenance object with source matching the evidence source;
- evidence source matching every obligation's admissible source exactly.

Classification runs only after those validations pass.

### Future-time rule

The proposed classifier has **zero future tolerance**:

`observed_at > evaluation_time => EVIDENCE_TIME_FUTURE`.

Future-dated evidence is rejected before freshness classification and cannot become `VALID`.

A future profile that permits clock skew must use separately named/versioned semantics; this verifier will not infer tolerance.

### Resolver / obligation semantics

The standalone verifier now supports exactly:

- semantics ID: `urn:cognous:resolver:required-evidence-v1`;
- classifier: `exact-source-current-with-max-age`;
- version: `1`;
- admissible-source rule: `exact-match`;
- future-observation rule: `reject`;
- status precedence: `CONFLICT, UNKNOWN, STALE, MISSING, VALID`.

The resolver declaration must exactly match this supported semantics object and its commitment.

Every obligation must bind both the supported semantics ID and the resolver's exact semantics commitment.

Unsupported resolver semantics fail with `UNSUPPORTED_RESOLVER_SEMANTICS`. An obligation/resolver mismatch fails with `OBLIGATION_RESOLVER_SEMANTICS_MISMATCH`.

The verifier does not approximate unsupported semantics.

## Negative-vector integrity discipline

Focused review vectors recompute the affected component commitments plus the closed `decision.input_commitment` and top-level `record_commitment`.

Where relevant, vectors also recompute:

- evidence provenance commitments;
- obligation commitments;
- institutional requirement obligation references;
- resolver semantics commitment.

Therefore the expected failures are semantic:

- `EVIDENCE_SOURCE_MISMATCH`;
- `EVIDENCE_TIME_FUTURE`;
- `OBLIGATION_RESOLVER_SEMANTICS_MISMATCH`;
- `UNSUPPORTED_RESOLVER_SEMANTICS`;
- `EVIDENCE_FRESHNESS_INVALID`;
- `OBLIGATION_REQUIRED_INVALID`.

They are not stale-hash failures.

## Files changed in the hardening pass

Only existing PR #11 files were changed:

- `src/agent_control_plane/decision_input_profile.py`
- `tests/test_decision_input_commitment_profile.py`
- `conformance/decision-input-commitment-vectors.json`
- `docs/decision-input-commitment-profile.md`
- `docs/workstreams/decision-input-commitment-checkpoint.md`

The standalone CLI remains unchanged because it delegates to the hardened verifier.

## Focused test result

Executed locally against the hardened profile/vector files:

```text
pytest -q tests/test_decision_input_commitment_profile.py
```

Result:

```text
25 passed in 0.06s
```

The suite includes a dedicated assertion that every `review-*` vector has a recomputed closed decision-input commitment and top-level record commitment, plus affected obligation/provenance commitments where applicable.

## Repository CI

Repository GitHub Actions ran on hardened code/test head `db1a8e3ea48c84626b5d1dc546e3525392b8d173`:

- workflow: **Tests**
- run: **#113** (GitHub Actions run `37636534005`)
- result: **success**

This checkpoint-result update is documentation-only; GitHub may create a subsequent workflow run for the new documentation head. The successful #113 run is the repository-CI result for the hardened verifier/vector/test implementation described above.

## Guarantees established by this PR

Within the standalone proposed verifier only:

- exact source matching is enforced between evidence and every claimed obligation;
- future-dated evidence is rejected;
- freshness bounds and required flags are strictly typed before classification;
- resolver semantics are both commitment-bound and implementation-bound;
- each obligation must bind the same supported resolver semantics;
- unsupported resolver semantics are explicitly rejected;
- semantic negative vectors remain validly re-committed so failures exercise semantics rather than digest staleness.

## Guarantees not established

This PR still does **not** establish:

- adoption by the live authorization path;
- atomicity between sidecar creation and `RuntimeDecision`;
- authenticated production policy/evidence retrieval;
- external evidence truth;
- independent authorization recomputation;
- cross-language canonicalization equivalence;
- authority/grant consumption atomicity;
- authority/effect linearization;
- complete mediation;
- destination finality;
- effect occurrence or intended outcome;
- EBL conformance.

Worker 19 continues to own authority/effect race qualification.

## Deferred adoption work

Still deferred to later runtime/consumer PRs:

- durable sidecar lifecycle and atomicity relative to runtime decisions;
- production source authentication/materialization;
- production clock/tolerance profile;
- runtime reason mapping;
- effect-time adopted commitment comparison / re-adjudication;
- Replay importer support;
- Evidence Pack transformation support;
- independent/cross-language canonicalization work;
- hub qualification and any pin advancement.

The sidecar remains proposal-only and non-authorizing.

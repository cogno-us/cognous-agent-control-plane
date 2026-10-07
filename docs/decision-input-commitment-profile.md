# Proposed Decision Input Commitment Profile

Status: **proposal only; non-authorizing; not implemented by the live authorization path**.

Profile version: `0.1.0-proposed`.

This document specifies the bounded Decision Input Commitment sidecar proposed by Worker 20 after reviewing the current Control Plane, Replay Bundle, Governance Evidence Pack, the selected hub pins, and *From Intent to Execution Grant: An Execution-Boundary Conformance Profile for High-Risk AI Actions*. The research paper is input, not an adopted Cognous framework. Existing Cognous concepts remain authoritative.

## 1. Scope and compatibility

The proposed artifact is a standalone sidecar keyed to the existing decision/proposal chain. It does **not** modify `RuntimeDecision`, `AuthorizationBinding`, `BoundedRunRecord`, Execution Envelope, executor producer schemas, dependency pins, or the live `BoundedAuthorizationWorkflow`.

A valid sidecar is not authority. It does not issue, renew, consume, suspend or revoke a grant; authorize a destination call; prove that the live Control Plane used the sidecar; prove source authenticity or external truth; prove complete mediation; or establish effect occurrence/outcome correctness.

Authority, permission consumption, business-intent deduplication, destination observation and outcome verification remain distinct contracts.

## 2. Existing bindings and bounded gap

Current Control Plane bindings already include Manifest ID/version/digest, payload commitment, full proposal commitment, requirement commitment, grant revision, policy ref/version status, and role-mapping version/digest. Those remain useful and are not replaced.

The proposed sidecar closes only the following representation gap:

- policy ref/version/status does not by itself commit policy contents or evaluation semantics;
- evidence obligation/source/status/time does not by itself commit complete materialized evidence/provenance;
- resolver/classification semantics need an explicit versioned identity;
- a decision-input commitment needs a closed set of candidate, requirement, policy, obligation, evidence, context, time and resolver inputs.

Replay reconstruction remains historical reconstruction, not automatic independent authorization recomputation. Governance Evidence Pack import/commitment checks remain distinct from external truth or operational verification.

## 3. Decision Input Commitment Record

The sidecar binds:

1. exact materialized candidate and commitment;
2. applicable institutional requirements and commitments;
3. institutional and operational policy content plus evaluation-semantics commitments;
4. complete evidence obligations, including policy origin, required flag, admissible source, freshness rule and resolution-semantics identity;
5. complete evidence content/provenance commitments and observation metadata;
6. complete decision-relevant context;
7. explicit adjudication time;
8. declared resolver/classification semantics;
9. assurance classifications;
10. decision, primary reason and deterministic reason precedence; and
11. one commitment over the complete closed decision-input payload.

Historical records are not backfilled. Absence of this sidecar in an older record means the additional commitments are unavailable, not that the historical decision is retroactively invalid.

## 4. Policy and institutional-obligation identity

Policy semantic identity is the tuple of policy reference/version, exact policy-content commitment, and exact evaluation-semantics commitment. Reusing the same version label with different content or evaluation semantics is a different decision input.

Existing Authority Context requirements remain the Cognous representation of non-overridable institutional requirements. Each institutional requirement binds the exact commitments of its institutional obligations. Operational policy may add obligations but cannot silently remove, rename or reinterpret an institutional obligation while retaining its prior identity.

Any legitimate policy replacement creates a new decision input. A claim that a replacement is "stricter", "narrower" or otherwise non-expanding does not preserve an earlier authorization by itself.

## 5. Supported evidence classifier

This proposed verifier intentionally implements **one** evidence-classification semantics and rejects alternatives explicitly.

Semantics identifier:

`urn:cognous:resolver:required-evidence-v1`

Declared classifier:

```json
{
  "classifier": "exact-source-current-with-max-age",
  "version": "1",
  "admissible_source": "exact-match",
  "future_observation": "reject",
  "precedence": ["CONFLICT", "UNKNOWN", "STALE", "MISSING", "VALID"]
}
```

The resolver's `classification_semantics_commitment` must match that exact object. Every obligation must bind both the supported semantics identifier and the same semantics commitment. A different resolver object, a different obligation semantics identifier, or a resolver/obligation commitment mismatch is rejected before evidence classification.

This verifier does not interpret unsupported semantics approximately.

## 6. Pre-classification field validation

Fields are type-checked before evidence classification.

For each obligation:

- `obligation_id`, policy origin, source reference and semantics identifier must be non-empty strings;
- `required` must be a JSON/Python boolean exactly; strings, integers and other truthy/falsy values are rejected;
- `max_age_seconds` must be a non-negative integer exactly; booleans, strings, floats, null and negative integers are rejected;
- `resolution_semantics_commitment` must be a SHA-256 commitment and must match the declared supported resolver semantics;
- the obligation must point to an existing policy ref/version.

For each evidence item:

- evidence ID and source reference must be non-empty strings;
- `obligation_ids` must be a non-empty, duplicate-free string array referencing known obligations;
- `declared_state` must be exactly one of `current`, `unknown`, or `conflict`;
- observation time must be parseable and timezone-aware;
- provenance must be an object with a source reference matching the evidence item source;
- the evidence source must exactly match the admissible source declared by every obligation the item claims to discharge.

These checks occur before `VALID`/`UNKNOWN`/`STALE`/`MISSING`/`CONFLICT` classification.

## 7. Source and time semantics

### Admissible source

Evidence is eligible for an obligation only when:

`evidence.source_ref == obligation.source_ref`.

A committed evidence object from another source does not discharge the obligation. Source identity here is still a declared/authenticated-input property; exact matching does not independently prove provider honesty or external truth.

### Future observations

This proposed classifier has **zero future tolerance**. If an evidence item's `observed_at` is later than the explicit `evaluation_time`, verification fails with `EVIDENCE_TIME_FUTURE`.

Future-dated evidence is not treated as fresh and is not converted to `VALID`. A future deployment that needs clock-skew tolerance must define a different versioned classifier semantics and cannot silently reuse this profile.

### Freshness

After structural/source/time validation, current evidence is `STALE` when:

`evaluation_time - observed_at > max_age_seconds`.

Only `VALID` discharges a required positive obligation. `MISSING`, `UNKNOWN`, `STALE`, and `CONFLICT` remain distinct outcomes.

## 8. Integrity versus semantic validation

The profile deliberately distinguishes commitment failure from semantic failure.

Examples:

- stale hashes produce commitment-mismatch errors;
- a recomputed but wrong source produces `EVIDENCE_SOURCE_MISMATCH`;
- recomputed future-dated evidence produces `EVIDENCE_TIME_FUTURE`;
- recomputed malformed freshness bounds produce `EVIDENCE_FRESHNESS_INVALID`;
- recomputed non-boolean `required` values produce `OBLIGATION_REQUIRED_INVALID`;
- recomputed unsupported resolver semantics produce `UNSUPPORTED_RESOLVER_SEMANTICS`;
- recomputed obligation semantics that do not match the supported resolver produce `OBLIGATION_RESOLVER_SEMANTICS_MISMATCH`.

The conformance-vector harness recomputes affected component commitments, the complete decision-input commitment, and the record commitment for the review-negative cases. Therefore those cases test semantic validation rather than merely stale digest detection.

## 9. Decision and reason precedence

The proposed record retains the deterministic primary-reason order:

1. `INPUT_INVALID`
2. `CANDIDATE_BINDING_FAILED`
3. `INSTITUTIONAL_REQUIREMENT_FAILED`
4. `POLICY_BINDING_FAILED`
5. `EVIDENCE_UNSATISFIED`
6. `CONTEXT_OR_TIME_FAILED`
7. `RESOLVER_SEMANTICS_FAILED`
8. `DECISION_INCONSISTENT`

This is a proposed record-level contract. Current runtime reason lists are not claimed to implement it.

## 10. Decision-to-execution changes

Any decision-relevant mutation after adjudication invalidates reuse of the earlier closed input:

- candidate change: re-adjudicate;
- policy ref/version/content/evaluation-semantics change: re-adjudicate;
- institutional obligation removal/reinterpretation: fail closed and require legitimate replacement plus fresh adjudication;
- evidence content/provenance/source/state change: reclassify and re-adjudicate;
- context change: re-adjudicate;
- resolver/classification semantics change: reject if unsupported or re-adjudicate under a separately adopted profile;
- passage of time: preserve the historical adjudication time and perform a new current-time evaluation rather than rewriting history.

Worker 19 separately owns authority/effect race and linearization qualification. This sidecar does not close that runtime boundary.

## 11. Canonicalization

The sidecar continues to reuse the current Python commitment behavior rather than replacing stack canonicalization globally:

`json-sort-keys-compact-utf8-no-nan-python-semantics-v0.1-proposed`

The vectors retain explicit tests for key ordering, integer versus float representation, negative zero, Unicode code-point sequence, absent versus null, and malformed/non-JSON values. Cross-language equivalence remains unestablished.

## 12. Consumer migration

### Control Plane

No runtime adoption occurs in this PR. A later runtime PR must define durable sidecar storage and lifecycle/atomicity relative to `RuntimeDecision` before it can become enforcement-critical.

### Replay Bundle

A later revision-pinned importer may map the sidecar into Reconstruction `SourceRecord` / `CommitmentRecord` structures. Replay must continue to distinguish locally recomputed commitment checks from policy re-evaluation or independent truth verification.

### Governance Evidence Pack

A later transformation may preserve the sidecar and its validation findings. It must not turn local semantic validation into a claim of independent operational verification.

### Hub

No hub pin changes occur here. Adoption requires accepted producer/consumer revisions and separate integration qualification.

## 13. Proposed-profile vectors and current result

`conformance/decision-input-commitment-vectors.json` remains explicitly labeled `proposed-profile-tests` with both runtime-enforcement and independent-external-truth claims set to false.

Focused review coverage now includes:

- wrong evidence source with recomputed provenance/closed-input/record commitments;
- future-dated evidence with recomputed closed-input/record commitments;
- obligation/resolver semantics mismatch with recomputed obligation/institutional-reference/closed-input/record commitments;
- unsupported resolver semantics with recomputed resolver, obligation, institutional-reference, closed-input and record commitments;
- string and negative freshness bounds with recomputed commitments;
- string and integer non-boolean `required` flags with recomputed commitments.

Focused local result after hardening:

```text
pytest -q tests/test_decision_input_commitment_profile.py
25 passed in 0.06s
```

These results establish only the behavior of this proposed standalone verifier and vector corpus.

## 14. Deferred adoption work

A later runtime/consumer batch still must:

1. define durable sidecar emission/storage relative to `RuntimeDecision`;
2. authenticate and materialize production policy/evidence sources;
3. define production clock authority/tolerance through an adopted resolver profile;
4. map runtime reasons to an adopted deterministic primary-reason contract;
5. perform adopted effect-time commitment comparison/fresh adjudication;
6. add Replay and Evidence Pack consumer support;
7. add independently developed/cross-language canonicalization evaluation;
8. qualify integration before advancing hub pins; and
9. coordinate authority/effect linearization with Worker 19.

No EBL conformance, production enforcement, independent external-truth verification, complete mediation or external outcome correctness is claimed.

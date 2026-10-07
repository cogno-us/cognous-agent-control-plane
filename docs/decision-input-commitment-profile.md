# Proposed Decision Input Commitment Profile

Status: **proposal only; non-authorizing; not implemented by the live authorization path**.

Profile version: `0.1.0-proposed`.

This document specifies the smallest compatible extension identified by Worker 20 after reviewing the current Control Plane, Replay Bundle, Governance Evidence Pack, the selected hub pins, and *From Intent to Execution Grant: An Execution-Boundary Conformance Profile for High-Risk AI Actions*. The paper is research input, not an adopted Cognous requirement. This proposal therefore reuses Cognous objects and terminology instead of introducing an EBL-specific runtime object model.

## 1. Problem and current guarantee map

The current bounded Control Plane already binds substantial execution state:

| Current field / behavior | What it establishes | Remaining gap addressed here |
|---|---|---|
| `RuntimeProposal` commitment | Exact serialized proposal, including candidate-related fields | Does not identify the full closed adjudication input set as one retained object |
| Manifest ID/version/digest and payload commitment | Useful action and declaration binding | Not policy-content or evaluation-semantics identity |
| `AuthorizationBinding.requirement_commitment` | Locally recomputable commitment to the selected institutional requirement | Does not separately retain the origin/identity of every non-overridable obligation |
| `policy_versions` + `PolicyStatus(ref, version, status, observed_at, institution, domain)` | Current reference/version/status/freshness binding | Version label can remain unchanged while policy content or evaluation semantics changes |
| `EvidenceStatus(obligation_id, state, observed_at, source_ref, institution, domain)` | Obligation/source/status/freshness binding | Does not commit to the complete materialized evidence content or its provenance |
| role-mapping version/digest | Current resolver mapping identity | Other resolver/classification semantics are not uniformly content-bound |
| effect-time `_resolve` equality | Re-resolves live authorization-critical inputs and detects many changes | Cannot detect same-label policy/evidence semantic substitution if resolver status records remain unchanged |
| Replay Reconstruction Bundle | Preserves producer records, commitments and links; policy re-evaluation is explicitly false | Record consistency is not independent recomputation of the authorization decision |
| Governance Evidence Pack | Retains source artifacts and locally computed artifact hashes with explicit limitations | Does not independently establish external truth or operational effectiveness |

The existing `commitment()` helper is deterministic within the current Python implementation: sorted compact JSON, UTF-8, `ensure_ascii=false`, and `allow_nan=false`. The same behavior is used by current compatible consumers. Cross-language equivalence has not been established.

## 2. Proposed artifact: Decision Input Commitment Record

The extension is a **sidecar record**, not a new field in `RuntimeDecision`, `AuthorizationBinding`, `BoundedRunRecord`, Execution Envelope, or any existing producer schema.

A record is keyed to the existing decision/proposal chain and is expressly non-authorizing:

```text
DecisionInputCommitmentRecord 0.1.0-proposed
  authorizing = false
  candidate
    materialized object
    exact candidate commitment
  institutional_requirements[]
    requirement id
    requirement content commitment
    non_overridable = true
    policy origin
    required institutional-obligation commitments
  policies[]
    ref + version
    kind = institutional | operational
    policy content + content commitment
    evaluation-semantics identity + commitment
  evidence_obligations[]
    obligation id
    policy origin ref + version
    required flag
    admissible source reference
    freshness rule
    resolution-semantics identity + commitment
    obligation commitment
  evidence_items[]
    evidence id
    obligation ids
    source ref
    materialized content + content commitment
    provenance + provenance commitment
    observation time/state
    assurance class
  context
    complete decision-relevant projection + commitment
  evaluation_time
    explicit adjudication time
  resolver_semantics
    classification/resolution semantics + commitment
  assurance
    declared / recomputable / authenticated / externally verified classification
  decision
    semantic result
    primary reason
    profile-defined deterministic reason precedence
    commitment to complete closed decision inputs
  record_commitment
```

An implementation may replace embedded materialized objects with immutable retrievable objects only if the verification context can retrieve the exact committed semantic object. A dangling reference is not equivalent to a materialized closed input.

### 2.1 Non-authorizing semantics

A valid record means only that the supplied record is structurally valid under this proposed profile and that locally recomputable commitments agree. It does **not** issue, renew, consume, suspend or revoke a grant; authorize a destination call; prove the live Control Plane used the record; authenticate a provider merely because its reference is present; prove evidence truth; or prove complete mediation, destination finality, effect occurrence or outcome correctness.

Authority, permission consumption, business-intent deduplication, destination observation and outcome verification remain separate contracts.

## 3. Input closure and bindings

The decision-input commitment covers, as one closed payload:

1. profile/canonicalization/commitment versions;
2. exact candidate and commitment;
3. all applicable institutional requirements;
4. all policy objects plus policy-evaluation semantics;
5. complete applicable evidence-obligation set;
6. complete materialized evidence used to classify those obligations;
7. decision-relevant context;
8. explicit adjudication time;
9. resolver/classification semantics; and
10. assurance classifications.

The decision contains `input_commitment` over that closed payload. Mutating any component while retaining the earlier decision invalidates the binding. Component commitments remain separately visible so a verifier can identify which input class changed rather than seeing only one opaque bundle hash.

## 4. Policy identity and institutional non-weakening

`PolicyStatus.ref` and `version` remain useful status coordinates but are insufficient as semantic identity. The proposal adds:

- `content_commitment`: exact policy-content identity;
- `evaluation_semantics`: named/versioned evaluator or semantics object;
- `evaluation_semantics_commitment`: exact semantics identity.

Reusing a policy version label with different content or evaluation semantics is a different decision input and invalidates reuse of the earlier decision record.

### 4.1 Non-overridable institutional obligations

Existing Authority Context requirements provide the natural Cognous root for non-overridable institutional constraints. This proposal does not rename them as a second governance framework.

Each institutional requirement records the exact commitments of obligations that originate from that requirement/policy. Operational policy may add obligations. It may not remove an institutional obligation, change its policy origin, or change its committed resolution semantics/content while presenting it as the same institutional obligation.

A legitimate institutional-policy replacement is administratively possible, but it creates a new decision input. The earlier decision remains historical evidence and cannot be silently reinterpreted as current permission.

## 5. Evidence obligations and evidence identity

An obligation is separately committed from the evidence item that discharges it. Its identity includes obligation ID, policy origin ref/version, required/optional status, admissible source reference, freshness bound, and resolution/classification semantics identity and commitment.

Evidence items separately commit exact materialized content, provenance metadata, source reference, observation time/state, and obligation bindings.

For positive required obligations, only `VALID` discharges the obligation. `MISSING`, `UNKNOWN`, `STALE`, and `CONFLICT` remain distinct failures. These states classify supplied evidence under declared semantics; they are not claims about external truth.

## 6. Assurance / verification classes

The record distinguishes four classes:

| Class | Meaning | Does not mean |
|---|---|---|
| `trusted_declaration` | A designated component declares the value and the integration chooses to trust it | Cryptographically authenticated or independently true |
| `locally_recomputable_commitment` | The verifier recomputed a commitment from supplied materialized content | Source authenticity or external truth |
| `authenticated_source` | Source identity/integrity was authenticated under a separately specified mechanism | The assertion is substantively true or complete |
| `externally_verified_fact` | An independent mechanism established the named fact under its own contract | Universal truth, correct policy, correct intent, or complete mediation |

The bounded verifier in this PR establishes only local structure/commitments. It does not create authenticated-source or externally-verified-fact status by itself.

## 7. Decision and deterministic reason precedence

The proposed record carries an explicit, versioned precedence order for primary failure classification:

1. `INPUT_INVALID`
2. `CANDIDATE_BINDING_FAILED`
3. `INSTITUTIONAL_REQUIREMENT_FAILED`
4. `POLICY_BINDING_FAILED`
5. `EVIDENCE_UNSATISFIED`
6. `CONTEXT_OR_TIME_FAILED`
7. `RESOLVER_SEMANTICS_FAILED`
8. `DECISION_INCONSISTENT`

This is a proposed record-level classification contract, not a claim that current `BoundedAuthorizationWorkflow` exposes these reason codes. A later runtime PR must define a mapping and compatibility tests before claiming implementation.

## 8. Decision-to-execution change behavior

No policy/evidence change is automatically safe merely because it is described as "stricter," "narrower," or "more secure."

For any decision-relevant change after adjudication and before effect:

- candidate change: earlier decision-input commitment is unusable; re-adjudicate;
- policy ref/version/content/evaluation-semantics change: re-adjudicate;
- institutional obligation removal/reinterpretation: fail closed; re-adjudicate only after legitimate institutional replacement;
- evidence content/provenance/source/status change: reclassify under committed obligation semantics and re-adjudicate when the closed input changes;
- context change: re-adjudicate;
- resolver/classification semantics change: re-adjudicate;
- passage of time: do **not** mutate historical `evaluation_time`; perform a new current-time evaluation of temporal predicates. If it contributes to authorization, it is a new closed decision input/decision record.

A proof that a new operational policy is non-expanding may be useful governance evidence, but does not itself preserve an earlier authorization or grant.

Worker 19 separately owns authority/effect race and linearization qualification. This proposal does not claim to close that runtime race.

## 9. Canonicalization profile and limits

To remain compatible with current Cognous commitments, the proposed vectors deliberately use existing Python JSON behavior rather than replacing canonicalization globally:

`json-sort-keys-compact-utf8-no-nan-python-semantics-v0.1-proposed`

Properties made explicit by the vectors:

- object key order is normalized;
- integer `1` and floating `1.0` are distinct serialized values;
- `0.0` and `-0.0` are distinct serialized values;
- Unicode is emitted as UTF-8 without normalization, so NFC and NFD strings remain distinct;
- absent member and explicit `null` are distinct;
- NaN and non-JSON values are rejected.

This is intentionally **not** a cross-language canonical JSON claim. A later interoperability profile may adopt a stronger standard only through a new canonicalization-profile identifier and cross-language vectors; it must not silently change existing commitments.

## 10. Consumer compatibility and migration

### Control Plane

No current runtime model or authorization path changes in this batch. A later runtime PR may emit the sidecar after adjudication and persist it separately, keyed by decision ID plus existing proposal commitment. It must define lifecycle/atomicity with the decision record before the sidecar becomes enforcement-critical.

### Replay Bundle

Current Reconstruction Bundle `0.2.0` already has generic `SourceRecord`, `CommitmentRecord`, links and explicit semantics stating that import is reconstruction, not policy re-evaluation. A later Replay adapter can ingest this sidecar as a new revision-pinned source record and locally recompute commitments while continuing to distinguish producer-attributed claims from independently checked facts.

Do not inject this artifact as an unknown top-level `BoundedRunRecord` field: current import completeness handling treats unknown producer fields as unmapped, and the live model does not expose them.

### Governance Evidence Pack

A later transformation can preserve the sidecar and locally checked commitments in traceable import metadata. It must retain the current limitation that semantic import validation is not independent operational verification or external truth verification.

### Hub

No dependency pin advances in this batch. Hub adoption requires separate accepted consumer revisions and integration qualification.

### Historical records

Historical RuntimeDecision/Reconstruction/Evidence Pack records remain valid only for claims supported at their original revisions. They are not backfilled with policy/evidence commitments that were never recorded. Absence of a sidecar is `unavailable`, not evidence that an old decision was invalid.

### Version consequences

This proposal introduces only `DecisionInputCommitmentRecord 0.1.0-proposed`. It does not bump existing RuntimeDecision, BoundedRunRecord, Reconstruction Bundle, Evidence Pack, Manifest, Execution Envelope, or executor producer schemas. Any future producer adoption must assign a reviewed non-proposed version and update downstream adapters explicitly.

## 11. Proposed-profile vectors

`conformance/decision-input-commitment-vectors.json` is explicitly marked `proposed-profile-tests` and covers:

- policy content changed under the same version label;
- evidence changed under the same source reference;
- missing, stale, unknown and conflicting required evidence;
- removed and reinterpreted institutional obligations;
- changed candidate, context and historical adjudication time under an earlier decision-input commitment;
- deterministic reason-precedence mutation;
- numeric representation, Unicode normalization, absent/null and malformed JSON values.

The standalone verifier and tests demonstrate only that these proposed record rules are executable. They are not evidence that current runtime enforcement implements this proposal.

## 12. Deferred implementation work

A later runtime PR must, at minimum:

1. define durable sidecar storage/atomicity with `RuntimeDecision`;
2. materialize exact policy contents and evaluation semantics from authenticated production resolvers;
3. materialize complete evidence content/provenance rather than status-only responses;
4. define authenticated policy/evidence source mechanisms and clock trust;
5. map existing runtime reason sets to an adopted deterministic primary-reason contract;
6. emit and compare current decision-input commitments at execution-time revalidation;
7. define a current-time re-evaluation record without rewriting historical adjudication time;
8. update Replay with a revision-pinned sidecar importer and semantic checks;
9. update Evidence Pack transformation/support metadata;
10. qualify consumer compatibility and then, only if accepted, advance hub pins;
11. add independently developed/cross-language canonicalization tests before any portability claim; and
12. coordinate with Worker 19 for decision/effect linearization rather than treating this sidecar as a repair for the authority/effect race.

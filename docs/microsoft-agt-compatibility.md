# Optional Microsoft Agent Governance Toolkit compatibility profile

Status: optional W5 compatibility surface. It is not part of the core component lock.

## Pin

- Upstream: `microsoft/agent-governance-toolkit`
- Revision: `84ae67348705996a3d65e31936afb7d02853f2a0`
- Selected SDK: Python `agent-control-specification` `0.4.0b0`
- License: MIT
- Python prerequisite: 3.11+
- Selected intervention point: `pre_tool_call`

The pinned SDK exposes `InterventionPoint.PRE_TOOL_CALL`,
`InterventionPointRequest`, `InterventionPointResult`, and an async
`RuntimeClient.evaluate_intervention_point(...)` boundary. The current engine
produces allow/deny/transform; warning is carried in `warnings[]`, and
approval/escalation semantics are represented as deny-side host behavior.
Legacy enum members are treated conservatively by this profile.

## Mapping

The compatibility adapter receives a Cognous `RuntimeProposal` plus an
explicit `tenant_id`. It sends only the bounded tool name, tool call identity,
proposal payload and supplied snapshot to AGT `pre_tool_call`.

Cognous remains authoritative for:
- exact tenant;
- action ID and adapter ID;
- target and payload commitment;
- requested permissions and effect limits;
- grant/approval/policy/evidence freshness;
- the final protected-dispatch decision.

AGT is conjunctive only. An AGT allow is not a grant and cannot override a
Cognous hold/deny. AGT denial blocks the compatibility path. Warning,
escalation, unavailable service, malformed/unsupported response and evaluation
error do not authorize.

## Transform rule

A transform may replace only the AGT policy target. For this profile the policy
target must materialize as a mapping usable as the Cognous proposal payload.
The adapter recalculates `payload_commitment` and invokes Cognous authority
again on the transformed proposal. Authorization for the original proposal is
never reused.

This is intentionally conservative. A transform that changes target, action,
tool/adapter identity, tenant, amount, permissions, or other commitment-bearing
fields is unsupported by this profile and must be represented as a new Cognous
proposal by the caller, followed by fresh authorization.

## Evidence boundary

The adapter records:
- exact AGT upstream revision and compatibility profile;
- tool and call identity;
- AGT decision, reason/message, warnings and input/enforced identities;
- opaque AGT evidence artefact and verification pointers;
- original and effective Cognous proposal commitments;
- Cognous decision ID/result when evaluated;
- whether a transform occurred.

AGT telemetry/evidence is source-attributed evidence about the AGT decision.
It is not proof of Cognous authority, destination execution, observation or
independent verification.

## Tenant limitation pending W1

At W0 baseline `74a3f1e7d7c872ad1b61fd9f857ac5fa517615f5`, the implementation
`RuntimeProposal` has not yet incorporated the frozen C1/C2 tenant-aware 0.2
producer field; W1 owns that producer change. W5 therefore accepts tenant as an
explicit required compatibility input and passes it unchanged into the
independent Cognous authority evaluator. This profile must be re-bound to the
accepted W1 `RuntimeProposal.tenant_id` field once that producer generation is
merged; it must not infer or default tenant.

## Qualification

Unit tests use deterministic local fakes for AGT outcomes and the Cognous
authority evaluator. `test_real_sdk_types_are_supported_when_installed`
uses the actual pinned Python SDK types and request shape with an in-process
runtime client. The W5 qualification workflow installs the SDK from the exact
upstream revision and runs this test plus the adapter suite.

That is a real SDK compatibility test, but not a live remote policy service.
No cloud service, tenant, identity provider, or external approval backend is
required or claimed. A deployment using OPA/Cedar/remote annotators requires
its own backend-specific qualification and must fail closed when unavailable.

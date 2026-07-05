# Core Concepts

This page defines the core objects in Agent Control Plane.

---

## Frame

A **Frame** is the execution context for a single agent run.  It specifies:

- **actor** – who or what is executing the task (agent identifier, user ID, service name).
- **environment** – the deployment environment, e.g. `"production"`, `"staging"`, `"sandbox"`.
- **allowed_tools** – tools the agent is explicitly permitted to call.
- **blocked_tools** – tools the agent is explicitly forbidden from calling.
- **policy_version** – the version of the policy set in effect.

A Frame is created once at the start of a run and is not modified thereafter.
The policy gate uses the Frame to evaluate every action proposal.

---

## ActionProposal

An **ActionProposal** is a record of an action the agent *wants* to execute,
captured *before* any tool is called.

Key fields:

- **tool_name** – the tool the agent wants to invoke.
- **action_type** – the semantic type of the action: `"read"`, `"write"`,
  `"external_send"`, or any other type defined by your policy.
- **target** – the resource, endpoint, or object the action targets.
- **payload** – arguments or parameters for the tool.
- **reason** – optional agent-supplied justification.

Every proposal is stored regardless of whether it is ultimately allowed or
blocked.

---

## PolicyDecision

A **PolicyDecision** is the output of the policy gate for one `ActionProposal`.

Key fields:

- **result** – one of `"allow"`, `"block"`, or `"escalate"`.
- **policy_name** – the name of the rule that determined the outcome.
- **reason** – a human-readable explanation.
- **deterministic_fingerprint** – a SHA-256 hex digest of the canonical
  inputs (tool name, action type, target, allowed/blocked tools, policy
  version, active authority scopes).  Identical inputs always produce the
  same result and fingerprint, enabling verification that a decision was
  reached correctly.  The `decision_id` and `decided_at` fields are
  generated per evaluation.

---

## BlockedAction

A **BlockedAction** record is created automatically whenever a
`PolicyDecision` has `result == "block"`.

It captures:

- **action_id** – the proposal that was blocked.
- **reason** – why it was blocked.
- **policy_name** – which policy rule triggered the block.
- **blocked_at** – timestamp.

No real tool is called when an action is blocked.

---

## AuthorityRecord

An **AuthorityRecord** grants an actor a set of permission **scopes** for
the duration of a run.

Scopes that the policy gate checks:

- `"read"` – allows read-type actions on allowed tools.
- `"write"` – allows write-type actions on allowed tools.
- `"external_send"` – allows `external_send` actions on allowed tools.

Multiple authority records can be active simultaneously.  The policy gate
collects scopes only from active records that match the current run, match
the Frame actor, and have not expired when the proposal is evaluated.

---

## RelianceRecord

A **RelianceRecord** documents that the agent relied on an external source
during the run.

Key fields:

- **source_name** – name of the source (e.g. `"crm_read"`, `"user_prompt"`).
- **source_type** – category: `"tool"`, `"database"`, `"file"`, `"api"`,
  `"user_input"`, `"model_output"`, or `"other"`.
- **scope** – what was accessed, e.g. `"customer record fields: name, email"`.
- **referenced_action_id** – optional link to the `ActionProposal` that
  triggered the reliance.

Reliance records help auditors trace the origin of information used to
produce the final output.

---

## ReplayBundle

A **ReplayBundle** is a self-contained, portable snapshot of a completed run.

It contains:

- The `Frame`
- All `ActionProposal` records
- All `PolicyDecision` records
- All `AuthorityRecord` records
- All `RelianceRecord` records
- All `BlockedAction` records
- The final output

Bundles can be serialised to JSON via `replay.to_json()` and deserialised
via `replay.from_json()`.  They are intended for offline audit, compliance
review, or replay simulation.

---

## SignedReplayBundle

A **SignedReplayBundle** wraps a `ReplayBundle` plus an HMAC-SHA256 signature
and signing metadata.

It supports optional integrity verification for exported bundles. It does not
provide production key management or claim to be a complete security boundary.

---

## PolicyConfig

A **PolicyConfig** is a lightweight JSON configuration model that can be used
to create a `Frame` for examples or small integrations.

It includes:

- `policy_version`
- `allowed_tools`
- `blocked_tools`
- `authority_required`
- `default_action`

This is intentionally a simple configuration format, not a full policy DSL.

# Architecture

Agent Control Plane is a thin runtime control layer that sits alongside
an AI agent.  It does not replace an agent framework; it records what the
agent proposed to do, what was permitted or blocked, and produces a
replayable audit trace.

## Overview

```
Agent Task
   ↓
Frame
   ↓
Action Proposal
   ↓
Policy Gate
   ↓
Policy Decision + Evaluation Trace
   ↓
Allow / Block / Escalate
   ↓
Optional Tool Adapter Execution
   ↓
Run Record
   ↓
Validation Report
   ↓
Replay Bundle
   ↓
Optional Redacted or Signed Export
```

## Components

### Frame

A Frame is created at the start of each run.  It captures the actor, the
deployment environment, the active policy version, and explicit allow/block
lists for tools.  The Frame is immutable for the duration of the run.

### RunRecorder

`RunRecorder` is the main entry point.  It:

1. Creates the Frame via `start_run()`.
2. Accepts authority records via `add_authority_record()`.
3. Records proposed actions via `propose_action()`.
4. Evaluates each proposal via `evaluate_action()`, which delegates to
   the `PolicyGate`.
5. Records external-source reliance via `record_reliance()`.
6. Closes the run via `complete_run()`.
7. Exports the `RunRecord` to JSON via `export_json()`.
8. Generates a `ReplayBundle` via `generate_replay_bundle()`.

### PolicyGate

`PolicyGate.evaluate()` and `PolicyGate.evaluate_with_trace()` apply a
deterministic rule chain to a single `ActionProposal`. The rules are evaluated
in order:

1. Blocked tool → `block`
2. Unknown tool (not in allow-list) → `escalate`
3. `external_send` without authority → `block`
4. `read` with allowed tool → `allow`
5. `write` with write authority → `allow`
6. Default → `escalate`

The gate produces a `deterministic_fingerprint` (SHA-256 hex) from the
canonical inputs so that two evaluations with identical inputs always
produce the same result and fingerprint.  The `decision_id` and
`decided_at` fields are generated per evaluation.

`evaluate_with_trace()` also returns a `PolicyEvaluationTrace` showing the rule
order, which rule matched, and why the final result was reached.

### RunRecord

`RunRecord` is the complete in-memory and JSON representation of a finished
run.  It aggregates:

- `Frame`
- `list[ActionProposal]`
- `list[PolicyDecision]`
- `list[PolicyEvaluationTrace]`
- `list[AuthorityRecord]`
- `list[RelianceRecord]`
- `list[BlockedAction]`

### ReplayBundle

A `ReplayBundle` is a self-contained export of a completed run.  It
includes every record needed to reconstruct what happened, enabling
offline audit, replay simulation, or compliance review.

### Validation and redaction

Validation checks internal consistency before replay or export. Redaction
produces public-safe copies for sharing without mutating the original records.

### Tool adapters

Tool adapters are optional integration helpers. They execute only after an
allow decision and can add reliance metadata for the executed tool.

### Optional utilities

The package also includes a few additive utilities that sit around the core
recording flow:

- `signing` for optional HMAC-based replay bundle integrity checks
- `policy_config` for loading small JSON examples into `Frame` objects
- `cli` for validating, redacting, and signing exported JSON files
- `persistence` for a minimal adapter interface and filesystem storage

## Data flow

```
start_run()
    └─ creates Frame

add_authority_record()
    └─ appends AuthorityRecord

propose_action()
    └─ appends ActionProposal

evaluate_action(action)
    ├─ PolicyGate.evaluate_with_trace() → PolicyDecision + PolicyEvaluationTrace
    │       └─ if result == "block"
    │              └─ creates BlockedAction
    └─ appends PolicyDecision, PolicyEvaluationTrace, and BlockedAction if blocked

record_reliance()
    └─ appends RelianceRecord

complete_run()
    └─ sets completed = True, final_output

export_json()            → run_record.json
validate_run_record()    → ValidationReport
generate_replay_bundle() → ReplayBundle
redact_replay_bundle()   → redacted replay export
```

## Design principles

- **Determinism**: given the same inputs the gate always returns the same
  result and fingerprint, while `decision_id` and `decided_at` are generated
  for each evaluation.
- **Immutability**: records are append-only; existing records are never
  modified after creation.
- **Portability**: all records serialise to plain JSON with no binary
  dependencies.
- **Minimal dependencies**: only the Python standard library and Pydantic
  are required.
- **Additive utilities**: signing, validation, redaction, tool adapters, and
  persistence helpers stay optional and do not turn the package into a full
  agent platform.

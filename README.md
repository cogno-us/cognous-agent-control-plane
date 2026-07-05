# Agent Control Plane

**Runtime control and replay for AI agents.**

Agent Control Plane is a minimal runtime governance layer for AI-agent
workflows. It records proposed actions, policy decisions, blocked
operations, authority context, external-source reliance, and replayable run
traces.

> This repository is intentionally minimal. It is not an agent framework,
> not a model runtime, and not a complete enterprise governance platform.
> It is a reference implementation for deterministic policy gating and
> replayable agent-run records.

---

## Contents

1. [What it is](#what-it-is)
2. [Why it matters](#why-it-matters)
3. [What this MVP records](#what-this-mvp-records)
4. [What this is not](#what-this-is-not)
5. [Quickstart](#quickstart)
6. [Examples](#examples)
7. [Optional signed replay bundles](#optional-signed-replay-bundles)
8. [Policy configuration example](#policy-configuration-example)
9. [Framework integration pattern](#framework-integration-pattern)
10. [Policy evaluation traces](#policy-evaluation-traces)
11. [Semantic validation](#semantic-validation)
12. [Redacted exports](#redacted-exports)
13. [Tool adapter execution](#tool-adapter-execution)
14. [CLI](#cli)
15. [Persistence adapters](#persistence-adapters)
16. [Architecture](#architecture)
17. [Core concepts](#core-concepts)
18. [JSON schemas](#json-schemas)
19. [Tests](#tests)
20. [Roadmap](#roadmap)
21. [Security](#security)
22. [License](#license)

---

## What it is

Agent Control Plane is a thin Python package that sits beside an AI agent
and records what the agent proposed, what was allowed or blocked, what
external sources it relied on, and how the run can be replayed or audited.

It provides:

- A **deterministic policy gate** that evaluates action proposals against a
  Frame (allowed tools, blocked tools, authority records) and returns a
  stable result plus a verifiable deterministic fingerprint.
- A **RunRecorder** that accumulates all run events into a structured
  `RunRecord`.
- A **ReplayBundle** generator that produces a self-contained, portable
  snapshot of any completed run.
- **JSON export** for all records.
- **JSON Schema** files for all core objects.

---

## Why it matters

AI agents can call tools, read databases, send messages, and modify files.
Without a control layer:

- There is no record of what was proposed vs. what was executed.
- Blocked actions leave no trace.
- It is impossible to replay a run to verify what happened.
- External-source reliance is opaque.
- Policy decisions may be inconsistent.

Agent Control Plane addresses all of these gaps with a lightweight,
auditable record-keeping layer.

---

## What this MVP records

| Record | Description |
|--------|-------------|
| `Frame` | Execution context: actor, environment, allowed/blocked tools, policy version |
| `ActionProposal` | Every action the agent proposed, before execution |
| `PolicyDecision` | Allow / block / escalate outcome for each proposal, with fingerprint |
| `BlockedAction` | Automatically created when a decision is `"block"` |
| `AuthorityRecord` | Scoped permissions granted to the actor for the run |
| `RelianceRecord` | External sources and tools the agent relied on |
| `ReplayBundle` | Self-contained snapshot of a completed run |

---

## What this is not

- **Not an agent framework** – it does not run agents, schedule tasks, or
  manage model calls.
- **Not a model runtime** – it does not load or execute language models.
- **Not a complete enterprise governance platform** – it is a reference
  implementation for deterministic policy gating and replayable records.
- **Not a security boundary by itself** – the policy gate enforces what you
  define; bad policy configuration is not detected.

---

## Limitations

- No built-in tool integrations are included; callers provide optional tool adapters.
- No production key-management workflow is included.
- No persistence backend beyond the simple filesystem adapter is included.
- No full policy DSL is included.
- No dashboard or replay viewer yet.
- Correctness depends on the policy rules supplied by the implementer.

---

## Quickstart

```bash
pip install -e ".[dev]"
pytest
acp validate-run examples/sample_run_record.json
```

```python
from agent_control_plane import RunRecorder

recorder = RunRecorder()
recorder.start_run(
    task="Summarize customer record and draft email.",
    actor="agent-v1",
    environment="production",
    allowed_tools=["crm_read", "notes_search"],
    blocked_tools=["email_send"],
    policy_version="v1.0",
)

recorder.add_authority_record(
    actor="agent-v1",
    scope=["read"],
    source="user_consent",
)

# Allowed action
action = recorder.propose_action(
    tool_name="crm_read",
    action_type="read",
    target="customer:42",
)
decision, blocked = recorder.evaluate_action(action)
print(decision.result)  # "allow"

# Blocked action
send = recorder.propose_action(
    tool_name="email_send",
    action_type="external_send",
    target="customer@example.com",
)
decision, blocked = recorder.evaluate_action(send)
print(decision.result)  # "block"

recorder.complete_run("Draft prepared but email blocked.")
recorder.export_json("run_record.json")
bundle = recorder.generate_replay_bundle()
```

---

## Examples

Run the included examples from the repository root:

```bash
python examples/simple_agent_run.py
python examples/tool_policy_demo.py
python examples/policy_config_demo.py
python examples/framework_integration_demo.py
python examples/tool_adapter_demo.py
```

`examples/sample_run_record.json` shows a realistic output from
`simple_agent_run.py`.

---

## Optional signed replay bundles

Replay bundles can be signed with HMAC-SHA256 for optional export integrity
verification.

```python
from agent_control_plane import sign_replay_bundle, verify_signed_replay_bundle

signed = sign_replay_bundle(bundle, "shared-secret")
assert verify_signed_replay_bundle(signed, "shared-secret")
```

This adds integrity metadata to exported replay bundles. It is not production
key management and not a complete security boundary by itself.

---

## Policy configuration example

`examples/policy_config.json` shows a small JSON policy file with:

- allow and block lists for tools
- simple authority requirements by action type
- a policy version and default action label

Use it to derive a `Frame` without introducing a full policy DSL:

```bash
python examples/policy_config_demo.py
```

---

## Framework integration pattern

`examples/framework_integration_demo.py` shows how a framework adapter can sit
beside this package:

1. the agent proposes an action
2. `RunRecorder` records and evaluates it
3. only allowed actions execute
4. reliance is recorded when an action is used
5. the run completes and produces a replay bundle

The example uses a mock adapter and no external credentials. The same pattern
can be adapted to LangChain, OpenAI Agents, or other agent frameworks.

---

## Policy evaluation traces

`PolicyGate.evaluate_with_trace()` returns the same policy decision result as
`evaluate()`, plus an ordered `PolicyEvaluationTrace`. Each trace records the
rule path, the matching rule, the final result, and the same deterministic
fingerprint stored on the `PolicyDecision`. `RunRecorder` stores traces by
default and includes them in `RunRecord` and `ReplayBundle` exports.

---

## Semantic validation

`validate_run_record()` and `validate_replay_bundle()` check more than Pydantic
structure. They verify run ID consistency, action references, blocked-action
links, policy trace relationships, and missing outputs. Validation produces a
compact `ValidationReport` with warning and error issues. CLI validation uses
these reports and does not print full records.

---

## Redacted exports

`redact_run_record()` and `redact_replay_bundle()` return deep copies with
privacy-safe redaction. Payloads are redacted by default, and optional settings
can also redact targets, final output, and recorded reasons. IDs, timestamps,
decision results, fingerprints, and trace relationships are preserved so the
export remains useful for replay and audit workflows.

---

## Tool adapter execution

`execute_with_control()` is a small adapter pattern for public-safe tool
execution. It records an action proposal, evaluates it through the policy gate,
and only calls a provided `ToolAdapter` when the decision result is `"allow"`.
Successful executions can add a reliance record without turning this package
into a full agent framework. See `examples/tool_adapter_demo.py`.

---

## CLI

The package includes a small CLI for validation, redaction, and signing:

```bash
acp validate-run examples/sample_run_record.json
acp validate-replay path/to/replay_bundle.json
acp redact-run examples/sample_run_record.json --out path/to/redacted_run_record.json
acp redact-replay path/to/replay_bundle.json --out path/to/redacted_replay_bundle.json --reasons
acp sign-replay path/to/replay_bundle.json --secret "shared-secret" --out path/to/signed_replay_bundle.json
acp verify-signed-replay path/to/signed_replay_bundle.json --secret "shared-secret"
```

Commands return:

- `0` on success
- `1` on validation or signature failure
- `2` on usage or file lookup errors

---

## Persistence adapters

`FileSystemPersistenceAdapter` provides a minimal reference implementation for
storing run records and replay bundles as JSON files under a local directory.
It is intentionally small and does not attempt to be a production storage
platform.

---

## Architecture

```
Agent Task
   ↓
Frame
   ↓
Action Proposal
   ↓
Policy Gate
   ↓
Allow / Block / Escalate
   ↓
Run Record
   ↓
Replay Bundle
```

See [docs/architecture.md](docs/architecture.md) for full details.

Identical inputs produce the same result and `deterministic_fingerprint`.
The `decision_id` and `decided_at` fields are generated per evaluation.

---

## Core concepts

| Concept | Summary |
|---------|---------|
| **Frame** | Immutable execution context for a run |
| **ActionProposal** | Proposed tool call, recorded before execution |
| **PolicyDecision** | Gate outcome with stable result and fingerprint; IDs and timestamps are per evaluation |
| **BlockedAction** | Auto-created record for every blocked decision |
| **AuthorityRecord** | Scoped permission grant for the run |
| **RelianceRecord** | External-source dependency record |
| **ReplayBundle** | Self-contained run snapshot for audit/replay |

See [docs/concepts.md](docs/concepts.md) for detailed definitions.

---

## JSON schemas

JSON Schema Draft 2020-12 files are in the `schemas/` directory:

| File | Describes |
|------|-----------|
| `schemas/frame.schema.json` | `Frame` |
| `schemas/run_record.schema.json` | `RunRecord` |
| `schemas/action_proposal.schema.json` | `ActionProposal` |
| `schemas/policy_decision.schema.json` | `PolicyDecision` |
| `schemas/policy_rule_evaluation.schema.json` | `PolicyRuleEvaluation` |
| `schemas/policy_evaluation_trace.schema.json` | `PolicyEvaluationTrace` |
| `schemas/authority_record.schema.json` | `AuthorityRecord` |
| `schemas/reliance_record.schema.json` | `RelianceRecord` |
| `schemas/validation_issue.schema.json` | `ValidationIssue` |
| `schemas/validation_report.schema.json` | `ValidationReport` |
| `schemas/redaction_config.schema.json` | `RedactionConfig` |
| `schemas/tool_execution_result.schema.json` | `ToolExecutionResult` |
| `schemas/replay_bundle.schema.json` | `ReplayBundle` |
| `schemas/signed_replay_bundle.schema.json` | `SignedReplayBundle` |

---

## Tests

```bash
pip install -e ".[dev]"
pytest
python examples/policy_config_demo.py
python examples/framework_integration_demo.py
python examples/tool_adapter_demo.py
acp --help
acp validate-run examples/sample_run_record.json
```

Test coverage:

- `test_policy_gate.py` – allow, block, and escalate decisions; external-send authority
- `test_frame_immutability.py` – frozen Frame behavior
- `test_blocked_action.py` – blocked-action record creation
- `test_replay_bundle.py` – bundle completeness and JSON round-trip
- `test_reliance_record.py` – reliance record creation and linkage
- `test_determinism.py` – fingerprint stability and JSON export round-trip
- `test_run_recorder.py` – recorder action/run validation
- `test_signing.py` – replay bundle signing and verification
- `test_policy_config.py` – config loading and demo behavior
- `test_policy_traces.py` – evaluation trace generation and recorder storage
- `test_validation.py` – semantic validation report behavior
- `test_redaction.py` – redacted export helpers
- `test_tool_adapter.py` – tool adapter execution flow
- `test_framework_integration_demo.py` – mock framework adapter example
- `test_cli.py` – CLI validation and signing commands
- `test_persistence.py` – filesystem persistence round-trips

---

## Roadmap

See [docs/roadmap.md](docs/roadmap.md).

- **Phase 1** – Deterministic policy gate and run records *(current)*
- **MVP extensions** – Signed replay bundles, policy traces, semantic validation, redacted exports, tool adapter execution, policy config helpers, CLI support, framework integration example, filesystem persistence
- **Phase 2** – Optional replay viewer and richer config tooling
- **Phase 3** – Broader integration hooks and richer export utilities
- **Phase 4** – Deeper action classification and context-change records
- **Phase 5** – Additional ecosystem integrations

---

## Security

See [SECURITY.md](SECURITY.md) for the vulnerability reporting policy.

---

## License

Apache-2.0.  See [LICENSE](LICENSE).

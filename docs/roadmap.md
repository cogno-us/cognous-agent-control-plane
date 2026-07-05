# Roadmap

This roadmap describes the planned phases for Agent Control Plane.

---

## Phase 1 – Deterministic policy gate and run records *(current)*

- Deterministic policy gate with allow, block, and escalate outcomes.
- Stable `deterministic_fingerprint` for every policy decision.
- `RunRecord` aggregating all run events.
- `ReplayBundle` for offline audit and replay.
- JSON export for all records.
- JSON Schema files for all core objects.
- Full pytest test suite.

---

## Phase 2 – Policy configuration and dashboard

- External policy configuration via YAML or JSON files.
- Rule-based policy definitions without code changes.
- CLI tool for loading and validating policy configs.
- Simple web dashboard for viewing run records and decisions.

---

## Phase 3 – Replay viewer and signed run exports

- Interactive replay viewer showing the step-by-step run timeline.
- Cryptographically signed run exports for tamper-evident audit trails.
- Signature verification tooling.
- Diff view comparing two run records.

---

## Phase 4 – Deeper action classification and context-change records

- Richer action type taxonomy with semantic categories.
- Context-change records capturing state transitions during a run.
- Structured payload schemas per tool type.
- Integration hooks for custom classifiers.

---

## Phase 5 – Enterprise integrations

- Connectors for common enterprise tooling (SIEM, ticketing, identity providers).
- Webhook delivery for real-time decision notifications.
- Role-based access control for run record retrieval.
- Multi-run aggregation and trend reporting.

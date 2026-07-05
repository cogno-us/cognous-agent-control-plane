# Roadmap

This roadmap describes the planned phases for Agent Control Plane.

---

## Phase 1 – Deterministic policy gate and run records

- Deterministic policy gate with allow, block, and escalate outcomes.
- Stable `deterministic_fingerprint` for every policy decision.
- `RunRecord` aggregating all run events.
- `ReplayBundle` for offline audit and replay.
- JSON export for all records.
- JSON Schema files for all core objects.
- Full pytest test suite.

---

## MVP extensions *(current)*

- Optional signed replay bundles using HMAC-SHA256.
- JSON policy configuration example and demo helpers.
- Dependency-light framework integration example with a mock adapter.
- CLI validation and replay signing commands.
- Minimal persistence interface plus filesystem adapter.

These extensions keep the project positioned as a compact runtime control and
replay layer. They are not a full policy DSL, enterprise platform, or
production key-management solution.

---

## Phase 2 – Richer config tooling and replay utilities

- More expressive policy configuration without turning into a full DSL.
- Additional replay inspection and comparison utilities.
- Optional viewer for inspecting run records and decisions.

---

## Phase 3 – Broader ecosystem adapters

- Framework adapter examples beyond the mock reference integration.
- Additional persistence adapters that remain optional and lightweight.
- Export helpers for larger workflow pipelines.

---

## Phase 4 – Deeper action classification and context-change records

- Richer action type taxonomy with semantic categories.
- Context-change records capturing state transitions during a run.
- Structured payload schemas per tool type.
- Integration hooks for custom classifiers.

---

## Phase 5 – Additional integrations

- Optional connectors for common workflow tooling.
- Extra delivery hooks for downstream automation.
- Lightweight aggregation helpers where they fit the minimal package scope.

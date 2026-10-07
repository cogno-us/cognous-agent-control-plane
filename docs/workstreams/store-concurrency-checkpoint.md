# Worker 14d — Control Plane record-store concurrency

## Starting point and independent scope

Accepted reference and inspected remote main:
`2ea9528eeb87e14ff10f05de06473122b9df540f`. No matching open repair PR or
branch existed. Branch: `worker14d/control-plane-store-concurrency`.
Read CONTRIBUTING and bounded authorization guidance; no AGENTS file was present.
Main remained at that exact SHA on the pre-publication recheck.

Batch A was completed/checkpointed first in hub PR #6, published head
`225c4f4f267d63bf479310cf06f16d7a7b202f17`. Its one-time CI check found both
runs in progress. This component repair does not modify hub pins or evidence.
Later hub adoption needs separately reviewed qualification. No self-merge.

## Reproduction before repair

Read Worker 16's test and checkpoint at hub
`1f682ab9e2111349a777d77b832c764e1a10cb02` without editing them.
A separate local checkout at that revision used its exact five dependency pins.
Ran its unmodified public-store characterization:

```bash
python -m pytest -q tests/test_process_boundary_qualification.py::test_shared_control_plane_store_behavior --junitxml=<evidence>/baseline/junit.xml
```

`PYTHONPATH` pointed to that accepted hub and its pinned Control Plane `src`;
`PROCESS_BOUNDARY_RESULTS_DIR` pointed to this PR's baseline evidence directory,
`PROCESS_BOUNDARY_REPETITION=1`, and bytecode writes were disabled.
Its one characterization test passed while recording actual lost writes: passing
characterization is not a persistence safety pass. Round 2 for attempts silently
lost one record although both child calls returned successfully; other rounds
reported `FileNotFoundError` at the shared fixed temporary path.
Exact identities, child outcomes, before/after records and pins are retained in
`examples/store-concurrency/baseline/shared-control-plane-store.json`.

## Repair

A persistent sidecar `flock` serializes the complete initialization/read/append
transaction. Mutations reload and validate current JSON while holding the lock.
A unique temporary file is flushed/fsynced, atomically replaced and the directory
fsynced before success. Kernel ownership releases on close or process death.
No stale cached document can overwrite a newer successful append.

Raw historical fields survive appends; schema and lifecycle semantics do not
change. Corrupt data and write/lock failures are explicit. Linux local supported
mount types are checked; unavailable locking, unknown/network filesystems and
unsupported OS fail closed. There is no unsafe fallback.
See [persistence contract](../record-store-persistence.md) for same-user/canonical
path requirements, upgrade procedure, uncertain post-replace outcomes, sidecar
lifetime, filesystem limits and non-goals.

## Validation

Final concurrency repetitions: **20 passed each**, zero failures/errors/skips.
Full component suite: **145 passed**, zero failures/errors/skips, Python 3.12.
Existing bounded authorization suite initially passed 45/45 as well.

Tests use spawned processes, explicit start/readiness signals, bounded waits and
cleanup. They cover every record type plus mixed records, stale writer/reader
instances, exact identities/content/counts, complete concurrent reads, concurrent
initialization, termination before/after replacement with a separately waiting
recovery process, old JSON/lifecycle/extension preservation, malformed records,
failed lock/temp/replace/file-fsync/directory-fsync, and unsupported environments.

Commands and exact source hashes are in
[summary](../../examples/store-concurrency/summary.json). The
[artifact index](../../examples/store-concurrency/artifact-index.json) identifies
all JUnit, logs and per-scenario records within `raw-evidence.tar.xz`; extract it
into an empty directory. Initial diagnostic runs are retained and
not counted as final qualification. Existing CI runs the full component suite on
Python 3.11 and 3.12; local validation here establishes only Python 3.12.

No destination implementation, authorization policy, whole-workflow transaction,
distributed budget or exactly-once contract changed. The permanent lock file must
not be deleted while any client may use it. All writers must upgrade together.
A new append following an uncertain result is not automatically idempotent.

Final published SHA and the one-time final-head CI observation will be recorded
in the PR handoff. No polling or self-merge.

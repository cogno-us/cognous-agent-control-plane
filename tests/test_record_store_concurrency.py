"""Spawned-process qualification of record transactions, not workflow atomicity."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path
import traceback

import pytest

from agent_control_plane import bounded as b

WAIT = 15
NOW = "2026-10-07T00:00:00+00:00"
FIELDS = ("decisions", "attempts", "observations", "reconciliations")
METHODS = dict(zip(FIELDS, ("append_decision", "append_attempt", "append_observation", "append_reconciliation")))


def value(field, token):
    if field == "decisions":
        return b.RuntimeDecision(decision_id=token, effect_id=token, result="hold", reasons=[token], decided_at=NOW)
    if field == "attempts":
        return b.EffectAttempt(attempt_id=token, effect_id=token, decision_id=token, started_at=NOW, status="unknown")
    if field == "observations":
        return b.EffectObservation(effect_id=token, observed_at=NOW, state="absent", destination_state={"token": token})
    return b.ReconciliationResult(effect_id=token, reconciled_at=NOW, result="observed_absent", retry_eligible=False, reasons=[token])


def append(store, field, token):
    getattr(store, METHODS[field])(value(field, token))


def emit(name, data):
    if root := os.environ.get("STORE_CONCURRENCY_EVIDENCE"):
        out = Path(root)
        out.mkdir(parents=True, exist_ok=True)
        (out / (name + ".json")).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def writer(path, fields, side, go, conn):
    try:
        store = b.BoundedRecordStore(path, "concurrency")
        conn.send({"ready": True, "pid": os.getpid(), "before": store.load().model_dump(mode="json")})
        assert go.wait(WAIT), "writer start deadline"
        tokens = []
        for i in range(8):
            for field in fields:
                token = f"{field}-{side}-{i}"
                append(store, field, token)
                tokens.append(token)
        conn.send({"done": True, "tokens": tokens})
    except BaseException:
        conn.send({"error": traceback.format_exc()})
        raise
    finally:
        conn.close()


def reader(path, go, stop, conn):
    try:
        store = b.BoundedRecordStore(path, "concurrency")
        conn.send({"ready": True})
        assert go.wait(WAIT), "reader start deadline"
        snapshots = 0
        previous = {field: [] for field in FIELDS}
        while True:
            current = store.load().model_dump(mode="json")
            for field in FIELDS:
                records = current[field]
                assert records[:len(previous[field])] == previous[field]
                assert len({v["effect_id"] for v in records}) == len(records)
                previous[field] = records
            snapshots += 1
            if stop.is_set():
                break
        conn.send({"done": True, "snapshots": snapshots, "last": current})
    except BaseException:
        conn.send({"error": traceback.format_exc()})
        raise
    finally:
        conn.close()


def receive(conn):
    assert conn.poll(WAIT), "child response deadline"
    result = conn.recv()
    assert "error" not in result, result
    return result


def finish(process):
    process.join(WAIT)
    assert not process.is_alive(), "child exit deadline"
    assert process.exitcode == 0


def cleanup(processes):
    for process in processes:
        if process.is_alive():
            process.terminate()
        process.join(WAIT)


@pytest.mark.parametrize("fields", [(field,) for field in FIELDS] + [FIELDS], ids=[*FIELDS, "mixed"])
def test_concurrent_appends_and_readers(tmp_path, fields):
    ctx = mp.get_context("spawn")
    path = tmp_path / "records.json"
    store = b.BoundedRecordStore(path, "concurrency")
    for field in FIELDS:
        append(store, field, "prior-" + field)
    before = store.load().model_dump(mode="json")
    go, stop = ctx.Event(), ctx.Event()
    processes, pipes = [], []
    try:
        for side in ("a", "b", "c"):
            parent, child = ctx.Pipe(duplex=False)
            process = ctx.Process(target=writer, args=(str(path), fields, side, go, child))
            process.start(); child.close()
            processes.append(process); pipes.append(parent)
        rp, rc = ctx.Pipe(duplex=False)
        process = ctx.Process(target=reader, args=(str(path), go, stop, rc))
        process.start(); rc.close(); processes.append(process)
        ready = [receive(conn) for conn in pipes]
        assert all(item["before"] == before for item in ready)  # All instances precede every new write.
        assert receive(rp)["ready"]
        go.set()
        done = [receive(conn) for conn in pipes]
        for process in processes[:-1]:
            finish(process)
        stop.set()
        reads = receive(rp); finish(processes[-1])
        after = store.load().model_dump(mode="json")  # Parent instance is stale too.
        for field in FIELDS:
            expected = ["prior-" + field]
            if field in fields:
                expected += [f"{field}-{side}-{i}" for side in ("a", "b", "c") for i in range(8)]
            actual = [record["effect_id"] for record in after[field]]
            assert sorted(actual) == sorted(expected)
            assert after[field][:1] == before[field]
            assert len(actual) == len(set(actual))
            assert {json.dumps(v, sort_keys=True) for v in after[field][1:]} == {
                json.dumps(value(field, token).model_dump(mode="json"), sort_keys=True) for token in expected[1:]
            }
        assert reads["snapshots"] > 0
        assert reads["last"] == after
        emit("concurrent-" + (fields[0] if len(fields) == 1 else "mixed"),
             {"before": before, "after": after, "writers": done, "read_snapshots": reads["snapshots"], "passed": True})
    finally:
        go.set(); stop.set(); cleanup(processes)


def initializer(path, go, side, conn):
    try:
        conn.send({"ready": True})
        assert go.wait(WAIT)
        store = b.BoundedRecordStore(path, "concurrency")
        append(store, "decisions", side)
        conn.send({"done": True})
    finally:
        conn.close()


def test_concurrent_initialization(tmp_path):
    ctx = mp.get_context("spawn"); go = ctx.Event()
    path = tmp_path / "new.json"
    processes, pipes = [], []
    try:
        for side in ("a", "b", "c", "d"):
            parent, child = ctx.Pipe(duplex=False)
            process = ctx.Process(target=initializer, args=(str(path), go, side, child))
            process.start(); child.close(); processes.append(process); pipes.append(parent)
        assert all(receive(conn)["ready"] for conn in pipes)
        go.set()
        assert all(receive(conn)["done"] for conn in pipes)
        for process in processes: finish(process)
        assert sorted(v.decision_id for v in b.BoundedRecordStore(path, "concurrency").load().decisions) == list("abcd")
    finally:
        go.set(); cleanup(processes)


def interrupted_writer(path, stage, wait, conn):
    store = b.BoundedRecordStore(path, "concurrency")
    replace = b.os.replace
    def paused_replace(source, target):
        if stage == "after":
            replace(source, target)
        conn.send({"at_replace": stage})
        assert wait.wait(WAIT), "termination test release deadline"
        if stage == "before":
            replace(source, target)
    b.os.replace = paused_replace
    append(store, "decisions", "interrupted")


@pytest.mark.parametrize("stage", ["before", "after"])
def test_termination_during_persistence(tmp_path, stage):
    ctx = mp.get_context("spawn")
    path = tmp_path / "records.json"
    store = b.BoundedRecordStore(path, "concurrency")
    append(store, "decisions", "prior")
    prior = store.load().decisions[0]
    parent, child = ctx.Pipe(duplex=False); release = ctx.Event()
    process = ctx.Process(target=interrupted_writer, args=(str(path), stage, release, child))
    process.start(); child.close()
    processes = [process]
    try:
        assert receive(parent) == {"at_replace": stage}
        recovery_parent, recovery_child = ctx.Pipe(duplex=False)
        recovery_go = ctx.Event(); recovery_go.set()
        recovery = ctx.Process(target=initializer,
                              args=(str(path), recovery_go, "recovered", recovery_child))
        recovery.start(); recovery_child.close(); processes.append(recovery)
        assert receive(recovery_parent)["ready"]
        assert not recovery_parent.poll(0.05), "live owner must exclude another writer"
        # Kill while the transaction owns the lock, immediately before/after real replacement.
        process.terminate(); process.join(WAIT)
        assert not process.is_alive() and process.exitcode != 0
        assert receive(recovery_parent)["done"]  # Reopening/writing has a bounded deadline.
        finish(recovery)
        reopened = b.BoundedRecordStore(path, "concurrency")
        after = reopened.load()
        expected = ["prior"] + (["interrupted"] if stage == "after" else []) + ["recovered"]
        assert [v.decision_id for v in after.decisions] == expected
        assert after.decisions[0] == prior
        emit("termination-" + stage, {"exitcode": process.exitcode, "record": after.model_dump(mode="json"), "passed": True})
    finally:
        cleanup(processes)


def test_historical_content_and_lifecycle_survive(tmp_path):
    path = tmp_path / "historical.json"
    # Old optional fields may be absent; unknown historical extensions must not be erased.
    original = {"run_id": "historical", "decisions": [], "attempts": [
        {"attempt_id": "same", "effect_id": "e", "decision_id": "d", "started_at": NOW,
         "status": status, "legacy_extension": {"kept": True}} for status in ("attempted", "unknown")],
        "legacy_top_level": {"kept": [1, 2, 3]}}
    path.write_text(json.dumps(original))
    first = b.BoundedRecordStore(path, "historical")
    stale = b.BoundedRecordStore(path, "historical")
    append(first, "decisions", "first")
    append(stale, "decisions", "second")
    result = json.loads(path.read_text())
    assert result["attempts"] == original["attempts"]
    assert result["legacy_top_level"] == original["legacy_top_level"]
    assert [v.decision_id for v in first.load().decisions] == ["first", "second"]
    assert [v.status for v in stale.load().attempts] == ["attempted", "unknown"]
    assert all(v.acknowledgement == {} for v in stale.load().attempts)


@pytest.mark.parametrize("content", ["", "{broken", "null", "{}", '{"run_id":"x","decisions":[{}]}'])
def test_corruption_is_never_replaced(tmp_path, content):
    path = tmp_path / "records.json"
    store = b.BoundedRecordStore(path, "concurrency")
    path.write_text(content)
    with pytest.raises((ValueError, TypeError)):
        b.BoundedRecordStore(path, "concurrency")
    with pytest.raises((ValueError, TypeError)):
        append(store, "decisions", "must-not-write")
    assert path.read_text() == content


@pytest.mark.parametrize("operation", ["mkstemp", "fsync", "replace", "directory_fsync", "flock"])
def test_write_and_lock_failures_are_explicit(tmp_path, monkeypatch, operation):
    path = tmp_path / "records.json"
    store = b.BoundedRecordStore(path, "concurrency")
    append(store, "decisions", "prior")
    before = path.read_bytes()
    real_fsync = b.os.fsync
    calls = []
    def fail(*args, **kwargs):
        if operation == "directory_fsync":
            calls.append(args)
            if len(calls) == 1:
                return real_fsync(*args, **kwargs)
        raise OSError("injected persistence failure")
    with monkeypatch.context() as patch:
        if operation == "mkstemp": patch.setattr(b.tempfile, "mkstemp", fail)
        elif operation == "flock": patch.setattr(b.fcntl, "flock", fail)
        else: patch.setattr(b.os, "fsync" if operation == "directory_fsync" else operation, fail)
        with pytest.raises(OSError, match="injected persistence failure"):
            append(store, "decisions", "uncertain")
    if operation != "directory_fsync":
        assert path.read_bytes() == before
    else:
        assert [v.decision_id for v in store.load().decisions] == ["prior", "uncertain"]
    append(store, "decisions", "recovery")  # Failure releases ownership.
    assert store.load().decisions[0].decision_id == "prior"


def test_unsupported_platform_and_filesystem_fail_closed(tmp_path, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(b, "fcntl", None)
        with pytest.raises(RuntimeError, match="requires Linux"):
            b.BoundedRecordStore(tmp_path / "platform.json", "unsupported")
    read = Path.read_text
    def mountinfo(path, *args, **kwargs):
        if str(path) == "/proc/self/mountinfo":
            return "1 0 0:1 / / rw - nfs server:/ rw\n"
        return read(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", mountinfo)
        with pytest.raises(RuntimeError, match="filesystem is not supported"):
            b.BoundedRecordStore(tmp_path / "network.json", "unsupported")
    assert not (tmp_path / "platform.json").exists()
    assert not (tmp_path / "network.json").exists()

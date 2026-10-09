from __future__ import annotations

import json
import sqlite3
import threading
from datetime import timedelta

import pytest

from agent_control_plane.local_authority_effect import provision_local_execution_claim
from tests.test_local_authority_effect_profile import (
    APPROVAL,
    EVIDENCE,
    GRANT,
    NOW,
    POLICY,
    setup,
)


def _invalidate(resolver, kind: str) -> None:
    if kind == "grant":
        resolver.statuses[GRANT] = resolver.statuses[GRANT].model_copy(update={"status": "revoked"})
    elif kind == "policy":
        resolver.policies[POLICY] = resolver.policies[POLICY].model_copy(update={"status": "superseded"})
    elif kind == "approval":
        resolver.approvals[APPROVAL] = resolver.approvals[APPROVAL].model_copy(update={"status": "revoked"})
    elif kind == "evidence_unknown":
        resolver.evidence[EVIDENCE] = resolver.evidence[EVIDENCE].model_copy(update={"state": "unknown"})
    elif kind == "evidence_stale":
        resolver.evidence[EVIDENCE] = resolver.evidence[EVIDENCE].model_copy(
            update={"observed_at": (NOW - timedelta(minutes=10)).isoformat()}
        )
    else:
        raise AssertionError(kind)


class MutatingDestination:
    """Inject an authority mutation after C0 revalidation but before destination commit."""

    def __init__(self, base, mutate):
        self.base = base
        self.mutate = mutate
        self.injected = False

    def observe(self, effect_id):
        return self.base.observe(effect_id)

    def apply(self, **kwargs):
        if not self.injected:
            self.injected = True
            self.mutate()
        return self.base.apply(**kwargs)

    def snapshot(self):
        return self.base.snapshot()


@pytest.mark.parametrize("kind", ["grant", "policy", "approval", "evidence_unknown", "evidence_stale"])
def test_c0_invalid_before_revalidation_fails_closed(tmp_path, kind):
    proposal, resolver, flow, decision = setup(tmp_path)
    _invalidate(resolver, kind)

    with pytest.raises(PermissionError, match="authorization-critical inputs changed"):
        flow.execute(proposal, decision, adapter_id=proposal.adapter_id, now=NOW)

    assert flow.destination.snapshot()["effects"] == {}


@pytest.mark.parametrize("kind", ["grant", "policy", "approval", "evidence_unknown", "evidence_stale"])
def test_c0_change_after_revalidation_before_destination_commit_is_residual_race(tmp_path, kind):
    proposal, resolver, flow, decision = setup(tmp_path)
    base = flow.destination
    flow.destination = MutatingDestination(base, lambda: _invalidate(resolver, kind))

    attempt, observation = flow.execute(
        proposal, decision, adapter_id=proposal.adapter_id, now=NOW
    )

    # C0 is revalidate-then-dispatch, not destination-commit atomicity.  This
    # assertion intentionally records the residual race rather than upgrading C0.
    assert attempt.status == "acknowledged"
    assert observation is not None and observation.state == "applied"
    assert decision.effect_id in base.snapshot()["effects"]


def test_c0_revocation_after_commit_does_not_rewrite_historical_effect(tmp_path):
    proposal, resolver, flow, decision = setup(tmp_path)
    attempt, observation = flow.execute(
        proposal, decision, adapter_id=proposal.adapter_id, now=NOW
    )
    assert attempt.status == "acknowledged"
    assert observation is not None and observation.state == "applied"

    _invalidate(resolver, "grant")

    state = flow.destination.snapshot()
    assert decision.effect_id in state["effects"]
    assert resolver.statuses[GRANT].status == "revoked"


class SameHostInventory:
    """Test-only SQLite ordering model for optional C1.

    This is qualification infrastructure, not an activated runtime path.
    Authoritative ordering comes from SQLite transaction serialization; the
    event log is evidence of that database order, not an application-log proxy.
    """

    def __init__(self, path):
        self.path = str(path)
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE authority (
                    name TEXT PRIMARY KEY,
                    state TEXT NOT NULL
                );
                CREATE TABLE claims (
                    claim_id TEXT PRIMARY KEY,
                    body TEXT NOT NULL
                );
                CREATE TABLE effects (
                    effect_id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL
                );
                CREATE TABLE ordering (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL
                );
                """
            )

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def provision(self, claim):
        states = {
            "grant": "active",
            "policy": "active",
            "approval": "active",
            "evidence": "current",
        }
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for name, state in states.items():
                db.execute("INSERT INTO authority(name, state) VALUES (?, ?)", (name, state))
            db.execute(
                "INSERT INTO claims(claim_id, body) VALUES (?, ?)",
                (claim.claim_id, json.dumps(claim.model_dump(mode="json"), sort_keys=True)),
            )
            db.execute("INSERT INTO ordering(event) VALUES ('claim_provisioned')")
            db.commit()

    def mutate(self, name, state, *, acquired=None, release=None):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if acquired is not None:
                acquired.set()
            if release is not None:
                assert release.wait(timeout=5)
            db.execute("UPDATE authority SET state=? WHERE name=?", (state, name))
            db.execute("INSERT INTO ordering(event) VALUES (?)", (f"mutation:{name}:{state}",))
            db.commit()

    def commit_effect(self, claim, *, acquired=None, release=None):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if acquired is not None:
                acquired.set()
            if release is not None:
                assert release.wait(timeout=5)
            states = dict(db.execute("SELECT name, state FROM authority"))
            expected = {
                "grant": "active",
                "policy": "active",
                "approval": "active",
                "evidence": "current",
            }
            failed = sorted(name for name, state in expected.items() if states.get(name) != state)
            if failed:
                db.execute("INSERT INTO ordering(event) VALUES (?)", ("hold:" + ",".join(failed),))
                db.commit()
                return False
            db.execute(
                "INSERT INTO effects(effect_id, claim_id) VALUES (?, ?)",
                (claim.effect_id, claim.claim_id),
            )
            db.execute("INSERT INTO ordering(event) VALUES ('effect_commit')")
            db.commit()
            return True

    def snapshot(self):
        with self._connect() as db:
            return {
                "authority": dict(db.execute("SELECT name, state FROM authority")),
                "effects": list(db.execute("SELECT effect_id, claim_id FROM effects ORDER BY effect_id")),
                "ordering": list(db.execute("SELECT seq, event FROM ordering ORDER BY seq")),
            }


def _c1_fixture(tmp_path):
    proposal, resolver, flow, decision = setup(tmp_path / "source")
    inventory = SameHostInventory(tmp_path / "c1.sqlite")
    claim = provision_local_execution_claim(
        flow,
        proposal,
        decision,
        provision=inventory.provision,
        now=NOW,
        claim_id="o6-c1-claim",
    )
    return proposal, resolver, flow, decision, inventory, claim


@pytest.mark.parametrize(
    ("name", "state"),
    [
        ("grant", "revoked"),
        ("policy", "superseded"),
        ("approval", "revoked"),
        ("evidence", "stale"),
        ("evidence", "unknown"),
    ],
)
def test_c1_authoritative_mutation_before_commit_fails_closed(tmp_path, name, state):
    _, _, _, decision, inventory, claim = _c1_fixture(tmp_path)
    inventory.mutate(name, state)

    assert inventory.commit_effect(claim) is False

    snap = inventory.snapshot()
    assert snap["effects"] == []
    assert snap["ordering"][-1][1].startswith("hold:")
    assert decision.effect_id == claim.effect_id


def test_c1_concurrent_revocation_ordered_before_effect_holds(tmp_path):
    _, _, _, _, inventory, claim = _c1_fixture(tmp_path)
    mutation_acquired = threading.Event()
    release_mutation = threading.Event()
    results = {}

    mutator = threading.Thread(
        target=inventory.mutate,
        args=("grant", "revoked"),
        kwargs={"acquired": mutation_acquired, "release": release_mutation},
    )
    mutator.start()
    assert mutation_acquired.wait(timeout=5)

    committer = threading.Thread(
        target=lambda: results.setdefault("effect", inventory.commit_effect(claim))
    )
    committer.start()
    release_mutation.set()

    mutator.join(timeout=5)
    committer.join(timeout=5)
    assert not mutator.is_alive() and not committer.is_alive()
    assert results["effect"] is False

    events = [event for _, event in inventory.snapshot()["ordering"]]
    assert events.index("mutation:grant:revoked") < events.index("hold:grant")
    assert inventory.snapshot()["effects"] == []


def test_c1_concurrent_effect_ordered_before_revocation_preserves_committed_effect(tmp_path):
    _, _, _, _, inventory, claim = _c1_fixture(tmp_path)
    effect_acquired = threading.Event()
    release_effect = threading.Event()
    results = {}

    committer = threading.Thread(
        target=lambda: results.setdefault(
            "effect",
            inventory.commit_effect(claim, acquired=effect_acquired, release=release_effect),
        )
    )
    committer.start()
    assert effect_acquired.wait(timeout=5)

    mutator = threading.Thread(target=inventory.mutate, args=("grant", "revoked"))
    mutator.start()
    release_effect.set()

    committer.join(timeout=5)
    mutator.join(timeout=5)
    assert not committer.is_alive() and not mutator.is_alive()
    assert results["effect"] is True

    snap = inventory.snapshot()
    events = [event for _, event in snap["ordering"]]
    assert events.index("effect_commit") < events.index("mutation:grant:revoked")
    assert snap["effects"] == [(claim.effect_id, claim.claim_id)]
    assert snap["authority"]["grant"] == "revoked"

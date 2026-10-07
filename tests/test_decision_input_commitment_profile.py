import copy
import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "src" / "agent_control_plane" / "decision_input_profile.py"
spec = importlib.util.spec_from_file_location("decision_input_profile", MODULE_PATH)
profile = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(profile)

VECTORS = json.loads((Path(__file__).parents[1] / "conformance" / "decision-input-commitment-vectors.json").read_text())


def _pointer(record, path):
    parts = [p.replace("~1", "/").replace("~0", "~") for p in path.strip("/").split("/") if p]
    parent = record
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    return parent, parts[-1] if parts else ""


def _apply_patch(record, patch):
    parent, key = _pointer(record, patch["path"])
    op = patch["op"]
    if isinstance(parent, list):
        if op == "add" and key == "-":
            parent.append(copy.deepcopy(patch["value"]))
        elif op == "remove":
            parent.pop(int(key))
        elif op == "replace":
            parent[int(key)] = copy.deepcopy(patch["value"])
        else:
            raise AssertionError(f"unsupported list patch {patch}")
    else:
        if op in {"add", "replace"}:
            parent[key] = copy.deepcopy(patch["value"])
        elif op == "remove":
            del parent[key]
        else:
            raise AssertionError(f"unsupported object patch {patch}")


def _obligation_payload(obligation):
    return {
        "obligation_id": obligation.get("obligation_id"),
        "policy_origin_ref": obligation.get("policy_origin_ref"),
        "policy_origin_version": obligation.get("policy_origin_version"),
        "required": obligation.get("required"),
        "source_ref": obligation.get("source_ref"),
        "max_age_seconds": obligation.get("max_age_seconds"),
        "resolution_semantics_id": obligation.get("resolution_semantics_id"),
        "resolution_semantics_commitment": obligation.get("resolution_semantics_commitment"),
    }


def _decision_input_payload(record):
    keys = [
        "profile_version", "canonicalization_profile", "commitment_algorithm",
        "candidate", "institutional_requirements", "policies",
        "evidence_obligations", "evidence_items", "context", "evaluation_time",
        "resolver_semantics", "assurance",
    ]
    return {key: record[key] for key in keys}


def _recompute_requirement_obligation_refs(record, indexes):
    by_id = {o["obligation_id"]: o["obligation_commitment"] for o in record["evidence_obligations"]}
    for index in indexes:
        requirement = record["institutional_requirements"][index]
        for oid in list(requirement["obligation_commitments"]):
            if oid in by_id:
                requirement["obligation_commitments"][oid] = by_id[oid]


def _materialize_case(case):
    record = copy.deepcopy(VECTORS["baseline_record"])
    for patch in case.get("patches", []):
        _apply_patch(record, patch)

    if case.get("recompute_resolver"):
        resolver = record["resolver_semantics"]
        resolver["classification_semantics_commitment"] = profile.commitment(resolver["classification_semantics"])
        new_commitment = resolver["classification_semantics_commitment"]
        for obligation in record["evidence_obligations"]:
            obligation["resolution_semantics_commitment"] = new_commitment

    for index in case.get("recompute_obligations", []):
        obligation = record["evidence_obligations"][index]
        obligation["obligation_commitment"] = profile.commitment(_obligation_payload(obligation))

    _recompute_requirement_obligation_refs(record, case.get("recompute_requirement_obligation_refs", []))

    for index in case.get("recompute_evidence_content", []):
        item = record["evidence_items"][index]
        item["content_commitment"] = profile.commitment(item["content"])
    for index in case.get("recompute_evidence_provenance", []):
        item = record["evidence_items"][index]
        item["provenance_commitment"] = profile.commitment(item["provenance"])

    if case.get("recompute_candidate"):
        record["candidate"]["commitment"] = profile.commitment(record["candidate"]["materialized"])
    if case.get("recompute_context"):
        record["context"]["commitment"] = profile.commitment(record["context"]["materialized"])
    if case.get("recompute_decision_input"):
        record["decision"]["input_commitment"] = profile.commitment(_decision_input_payload(record))

    record["record_commitment"] = profile.commitment({k: v for k, v in record.items() if k != "record_commitment"})
    return record


def test_vectors_are_explicitly_proposed_profile_only():
    assert VECTORS["status"] == "proposed-profile-tests"
    assert VECTORS["runtime_enforcement_claim"] is False
    assert VECTORS["independent_external_truth_claim"] is False


@pytest.mark.parametrize("case", VECTORS["record_vectors"], ids=lambda c: c["id"])
def test_record_vectors(case):
    record = _materialize_case(case)
    if case["expect_valid"]:
        result = profile.verify_record(record)
        assert result["valid"] is True
        assert result["authorizing"] is False
        assert result["independent_external_truth_verified"] is False
    else:
        with pytest.raises(profile.ProfileValidationError) as exc:
            profile.verify_record(record)
        assert exc.value.code == case["expected_code"]


def test_review_vectors_recompute_closed_input_commitments():
    review = [case for case in VECTORS["record_vectors"] if case["id"].startswith("review-")]
    assert len(review) >= 7
    for case in review:
        record = _materialize_case(case)
        assert record["decision"]["input_commitment"] == profile.commitment(_decision_input_payload(record))
        assert record["record_commitment"] == profile.commitment({k: v for k, v in record.items() if k != "record_commitment"})
        for index in case.get("recompute_obligations", []):
            obligation = record["evidence_obligations"][index]
            assert obligation["obligation_commitment"] == profile.commitment(_obligation_payload(obligation))
        for index in case.get("recompute_evidence_provenance", []):
            item = record["evidence_items"][index]
            assert item["provenance_commitment"] == profile.commitment(item["provenance"])


def test_canonicalization_vectors():
    for case in VECTORS["canonicalization_vectors"]:
        if case["operation"] == "equal":
            assert profile.commitment(case["left"]) == profile.commitment(case["right"]), case["id"]
        elif case["operation"] == "distinct":
            assert profile.commitment(case["left"]) != profile.commitment(case["right"]), case["id"]
        else:
            raise AssertionError(f"unknown vector operation {case['operation']}")


def test_malformed_values_rejected():
    for value in ({"bad": float("nan")}, {"bad": {1, 2}}, {"bad": b"bytes"}):
        with pytest.raises(profile.ProfileValidationError) as exc:
            profile.commitment(value)
        assert exc.value.code == "CANONICALIZATION_REJECTED"

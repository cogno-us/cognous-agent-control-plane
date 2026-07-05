"""Replay bundle signing helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

from agent_control_plane.models import ReplayBundle, SignedReplayBundle


def _serialise_replay_bundle(bundle: ReplayBundle) -> bytes:
    payload = json.dumps(
        bundle.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return payload.encode("utf-8")


def _sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def sign_replay_bundle(bundle: ReplayBundle, secret: str) -> SignedReplayBundle:
    """Return a signed replay bundle using HMAC-SHA256."""

    signature = _sign_payload(_serialise_replay_bundle(bundle), secret)
    return SignedReplayBundle(
        signed_bundle_id=str(uuid.uuid4()),
        replay_bundle=bundle,
        signature=signature,
    )


def verify_signed_replay_bundle(
    signed_bundle: SignedReplayBundle, secret: str
) -> bool:
    """Verify a signed replay bundle using HMAC-SHA256."""

    if signed_bundle.signature_algorithm != "HMAC-SHA256":
        return False
    expected_signature = _sign_payload(
        _serialise_replay_bundle(signed_bundle.replay_bundle),
        secret,
    )
    return hmac.compare_digest(signed_bundle.signature, expected_signature)

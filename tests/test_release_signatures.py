import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import src.utils.release_signatures as signatures


def test_release_manifest_signature_round_trip(monkeypatch):
    private = Ed25519PrivateKey.generate()
    manifest = {"version": "2.3.0-hardened.17", "zip_sha256": "a" * 64}
    payload = signatures.canonical_manifest_bytes(manifest)
    signature = base64.b64encode(private.sign(payload))
    monkeypatch.setattr(signatures, "load_public_key", lambda: private.public_key())
    assert signatures.verify_release_manifest(payload, signature) == manifest


def test_release_manifest_rejects_tampering(monkeypatch):
    private = Ed25519PrivateKey.generate()
    payload = signatures.canonical_manifest_bytes({"version": "1"})
    signature = base64.b64encode(private.sign(payload))
    monkeypatch.setattr(signatures, "load_public_key", lambda: private.public_key())
    with pytest.raises(signatures.ReleaseSignatureError):
        signatures.verify_release_manifest(payload + b" ", signature)

"""Detached Ed25519 signatures for manually approved application updates.

The private signing key is deliberately never read by the application and must
never be committed.  Portable builds contain only the public key below.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.utils.resource_path import get_resource_path

PUBLIC_KEY_RESOURCE = "assets/release-signing-public-key.txt"
MAX_MANIFEST_BYTES = 256 * 1024
MAX_SIGNATURE_BYTES = 1024


class ReleaseSignatureError(ValueError):
    """The update trust metadata is absent, malformed, or untrusted."""


def canonical_manifest_bytes(manifest: dict) -> bytes:
    """Serialize release metadata in the one canonical signed form."""
    if not isinstance(manifest, dict):
        raise ReleaseSignatureError("release manifest must be a JSON object")
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_public_key() -> Ed25519PublicKey:
    """Load the embedded public key, rejecting placeholder/invalid values."""
    path = Path(get_resource_path(PUBLIC_KEY_RESOURCE))
    try:
        value = path.read_text(encoding="ascii").strip()
        raw = base64.b64decode(value, validate=True)
        if len(raw) != 32:
            raise ValueError("expected 32 bytes")
        return Ed25519PublicKey.from_public_bytes(raw)
    except (OSError, ValueError) as exc:
        raise ReleaseSignatureError("no valid embedded update-signing public key") from exc


def verify_release_manifest(manifest_bytes: bytes, signature_bytes: bytes) -> dict:
    """Verify a detached signature and return strictly parsed release data."""
    if len(manifest_bytes) > MAX_MANIFEST_BYTES or len(signature_bytes) > MAX_SIGNATURE_BYTES:
        raise ReleaseSignatureError("release metadata is unexpectedly large")
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        if canonical_manifest_bytes(manifest) != manifest_bytes:
            raise ReleaseSignatureError("release manifest is not canonical")
        signature = base64.b64decode(signature_bytes.strip(), validate=True)
        load_public_key().verify(signature, manifest_bytes)
        return manifest
    except InvalidSignature as exc:
        raise ReleaseSignatureError("release signature verification failed") from exc
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReleaseSignatureError("release manifest or signature is invalid") from exc

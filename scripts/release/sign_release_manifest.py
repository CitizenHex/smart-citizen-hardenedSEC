"""Create an Ed25519 key pair or sign canonical Smart Citizen release metadata.

Run this ONLY on the trusted signing machine. The private key stays outside the
repository; commit only the generated public-key text to assets/.
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

# Allow direct execution from the project checkout on the isolated signing
# machine without requiring an editable package installation.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.utils.release_signatures import canonical_manifest_bytes


def generate(private_path: Path, public_path: Path) -> None:
    if private_path.exists() or public_path.exists():
        raise SystemExit("Refusing to overwrite an existing signing-key file.")
    private = Ed25519PrivateKey.generate()
    private_path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    public_path.write_text(base64.b64encode(private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )).decode("ascii") + "\n", encoding="ascii")
    print(f"Private key: {private_path}")
    print(f"Public key:  {public_path}")


def sign(private_path: Path, manifest_path: Path, signature_path: Path) -> None:
    private = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise SystemExit("The supplied key is not an Ed25519 private key.")
    # Normalize before signing, so the client can reject ambiguous JSON.
    import json
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = canonical_manifest_bytes(manifest)
    manifest_path.write_bytes(payload)
    signature_path.write_bytes(base64.b64encode(private.sign(payload)) + b"\n")
    print(f"Signed: {manifest_path.name} -> {signature_path.name}")


parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest="command", required=True)
keygen = sub.add_parser("keygen")
keygen.add_argument("private_key", type=Path)
keygen.add_argument("public_key", type=Path)
sign_cmd = sub.add_parser("sign")
sign_cmd.add_argument("private_key", type=Path)
sign_cmd.add_argument("manifest", type=Path)
sign_cmd.add_argument("signature", type=Path)
args = parser.parse_args()

if args.command == "keygen":
    generate(args.private_key, args.public_key)
else:
    sign(args.private_key, args.manifest, args.signature)

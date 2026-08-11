"""Manual, signature-first discovery of Smart Citizen Hardened releases."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.utils.release_signatures import ReleaseSignatureError, verify_release_manifest

RELEASE_API = "https://api.github.com/repos/ZeroDiv1de/smart-citizen-hardenedSEC/releases/latest"
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_ZIP_BYTES = 600 * 1024 * 1024


def _read(url: str, accept: str = "application/vnd.github+json") -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"api.github.com", "github.com"}:
        raise ValueError("release asset URL is not an approved GitHub HTTPS URL")
    request = Request(url, headers={"Accept": accept, "User-Agent": "SmartCitizen-Hardened"})
    with urlopen(request, timeout=15) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("release metadata is unexpectedly large")
    return data


def fetch_latest_signed_release() -> dict:
    """Return only a release whose detached manifest signature verifies."""
    release = json.loads(_read(RELEASE_API).decode("utf-8"))
    assets = {asset.get("name"): asset for asset in release.get("assets", []) if isinstance(asset, dict)}
    manifest_asset = assets.get("release-manifest.json")
    signature_asset = assets.get("release-manifest.sig")
    if not manifest_asset or not signature_asset:
        raise ReleaseSignatureError("latest release has no signed update manifest")
    # GitHub's ``assets[].url`` is an API metadata endpoint and can return an
    # asset JSON document even when an octet-stream Accept header is supplied.
    # The browser download URL is the actual release asset. Its redirect target
    # is safe to follow because the detached Ed25519 signature below remains
    # the trust boundary for the bytes received.
    manifest = verify_release_manifest(
        _read(manifest_asset["browser_download_url"], "application/octet-stream"),
        _read(signature_asset["browser_download_url"], "application/octet-stream"),
    )
    zip_asset = assets.get(manifest.get("zip_name"))
    if not zip_asset or int(zip_asset.get("size", -1)) != manifest.get("zip_size"):
        raise ReleaseSignatureError("signed manifest does not match the published ZIP")
    return {"manifest": manifest, "release_url": release.get("html_url", ""), "zip_url": zip_asset.get("browser_download_url", "")}


def download_verified_release(release: dict, destination: Path, progress=None) -> Path:
    """Download one user-approved ZIP and verify its signed size/hash."""
    manifest = release["manifest"]
    expected_size = int(manifest["zip_size"])
    if expected_size < 1 or expected_size > MAX_ZIP_BYTES:
        raise ValueError("signed update ZIP size is outside safe limits")
    parsed = urlparse(release["zip_url"])
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise ValueError("release ZIP URL is not an approved GitHub HTTPS URL")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    written = 0
    request = Request(release["zip_url"], headers={"User-Agent": "SmartCitizen-Hardened"})
    with urlopen(request, timeout=30) as response, partial.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > expected_size:
                raise ValueError("download exceeded signed ZIP size")
            digest.update(chunk)
            output.write(chunk)
            if progress:
                progress(written, expected_size)
    if written != expected_size or digest.hexdigest() != manifest["zip_sha256"]:
        partial.unlink(missing_ok=True)
        raise ValueError("downloaded ZIP does not match its signed manifest")
    partial.replace(destination)
    return destination

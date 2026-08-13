"""Safe, explicitly initiated refresh support for Finder shop data."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from src.utils.acquisition_catalog import (
    SCHEMA_VERSION, _normalize_display_name, validate_catalog,
)
from src.utils.network_policy import require_network_allowed

FINDER_CATALOG_URL = "https://finder.cstone.space/GetSearch"
MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
MAX_RECORDS = 25_000


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Finder refresh rejected an unexpected redirect.")


def _validate_url(url: str) -> None:
    parsed = urlsplit(url)
    expected = urlsplit(FINDER_CATALOG_URL)
    if (parsed.scheme, parsed.netloc.casefold(), parsed.path) != (
        expected.scheme, expected.netloc.casefold(), expected.path,
    ) or parsed.query or parsed.fragment:
        raise ValueError("Finder refresh only permits the reviewed GetSearch HTTPS URL.")


def _unwrap_finder_items(payload) -> list:
    """Accept Finder's documented list plus conservative transport wrappers.

    The endpoint normally returns a list directly, but its hosting layer has
    intermittently returned ASP.NET/DataTables-style wrappers.  Only unwrap
    known single-purpose list fields; an arbitrary object is still rejected.
    """
    if isinstance(payload, list):
        return payload
    # A few proxy layers serialize an otherwise valid JSON response one extra
    # time. Decode exactly once and still require the final value to be a
    # list/wrapper; never recursively unpack arbitrary data.
    if isinstance(payload, str):
        try:
            return _unwrap_finder_items(json.loads(payload))
        except json.JSONDecodeError:
            pass
    if isinstance(payload, dict):
        for key in ("data", "items", "results", "d", "aaData", "response"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            # Some legacy ASP.NET endpoints serialize the d field a second
            # time as JSON text. Decode it once, then require a list.
            if key == "d" and isinstance(value, str):
                try:
                    decoded = json.loads(value)
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, list):
                    return decoded
        # A safe fallback for a benign host/CDN envelope we do not recognize:
        # accept exactly one list-valued field. Multiple lists are ambiguous
        # and remain rejected. The row-by-row catalog validation below still
        # controls what may enter the saved catalog.
        list_values = [value for value in payload.values() if isinstance(value, list)]
        if len(list_values) == 1:
            return list_values[0]
        keys = ", ".join(str(key)[:80] for key in list(payload)[:8])
        raise ValueError(f"Finder response has no usable item list (fields: {keys or 'none'}).")
    raise ValueError(f"Finder response is not a supported item list (got {type(payload).__name__}).")


def parse_finder_search(payload, existing_catalog: dict, now: datetime | None = None) -> tuple[dict, int]:
    """Turn Finder's minimal public search response into a safe local catalog.

    Ambiguous duplicate display names are excluded rather than guessed. Manual
    key-based overrides are retained exactly as the player set them.
    """
    payload = _unwrap_finder_items(payload)
    if len(payload) > MAX_RECORDS:
        raise ValueError(f"Finder response has too many items (limit {MAX_RECORDS:,}).")
    names: dict[str, dict] = {}
    conflicts: set[str] = set()
    for row in payload:
        if not isinstance(row, dict):
            continue
        name, sold = row.get("name"), row.get("Sold")
        if not isinstance(name, str) or not name.strip() or len(name) > 500:
            continue
        if sold not in (0, 1, False, True):
            continue
        normalized = _normalize_display_name(name)
        status = "shop" if bool(sold) else "unlisted"
        old = names.get(normalized)
        if old and old["status"] != status:
            conflicts.add(normalized)
        else:
            names[normalized] = {"status": status, "source": "Finder community catalog"}
    for name in conflicts:
        names.pop(name, None)
    if not names:
        raise ValueError("Finder response did not contain usable item names.")
    existing = validate_catalog(existing_catalog)
    timestamp = (now or datetime.now(UTC)).strftime("%Y-%m-%d %H:%M UTC")
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "items": existing["items"],
        "names": names,
        "shop_catalog_complete": False,
        "shop_catalog_version": f"Finder refresh {timestamp}",
    }
    return validate_catalog(catalog), len(names)


def refresh_finder_catalog(existing_catalog: dict) -> tuple[dict, int]:
    """Fetch one reviewed Finder endpoint after an explicit UI confirmation."""
    _validate_url(FINDER_CATALOG_URL)
    require_network_allowed("Finder shop catalog refresh", FINDER_CATALOG_URL)
    request = Request(FINDER_CATALOG_URL, headers={"Accept": "application/json"})
    opener = build_opener(_RejectRedirects())
    with opener.open(request, timeout=30) as response:
        if response.geturl() != FINDER_CATALOG_URL:
            raise ValueError("Finder refresh rejected an unexpected final URL.")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > MAX_DOWNLOAD_BYTES:
            raise ValueError("Finder response exceeds the 5 MiB safety limit.")
        chunks, total = [], 0
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError("Finder response exceeds the 5 MiB safety limit.")
            chunks.append(chunk)
    try:
        payload = json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Finder response was not valid UTF-8 JSON.") from exc
    return parse_finder_search(payload, existing_catalog)

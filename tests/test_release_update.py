import json

import src.utils.release_update as release_update


def test_fetch_uses_browser_download_urls(monkeypatch):
    manifest = {"version": "2.3.0-hardened.19", "zip_name": "app.zip", "zip_size": 3}
    seen = []

    def fake_read(url, _accept=""):
        seen.append(url)
        if url == release_update.RELEASE_API:
            return json.dumps({"assets": [
                {"name": "release-manifest.json", "url": "https://api.github.com/bad-manifest", "browser_download_url": "https://github.com/good-manifest"},
                {"name": "release-manifest.sig", "url": "https://api.github.com/bad-signature", "browser_download_url": "https://github.com/good-signature"},
                {"name": "app.zip", "size": 3, "browser_download_url": "https://github.com/app.zip"},
            ]}).encode()
        return b"ignored"

    monkeypatch.setattr(release_update, "_read", fake_read)
    monkeypatch.setattr(release_update, "verify_release_manifest", lambda _m, _s: manifest)
    result = release_update.fetch_latest_signed_release()
    assert seen == [release_update.RELEASE_API, "https://github.com/good-manifest", "https://github.com/good-signature"]
    assert result["zip_url"] == "https://github.com/app.zip"

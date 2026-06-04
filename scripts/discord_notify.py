"""
Discord Release Notification Script for Smart Citizen

Posts release announcements to Discord via webhook with release notes.

Setup:
  1. Create a webhook in Discord's #other-releases channel
  2. Add the webhook URL to GitHub secrets as: DISCORD_RELEASE_WEBHOOK_URL
  3. Add the webhook URL to your local .env file for development

Usage: python scripts/discord_notify.py <version> [release_notes]
  - version: The release version (e.g., v0.1.0)
  - release_notes: Optional release notes body

Examples:
  python scripts/discord_notify.py v0.1.0
  python scripts/discord_notify.py v0.1.0 "Initial release"
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

WEBHOOK_URL = os.getenv("DISCORD_RELEASE_WEBHOOK_URL")
GITHUB_REPO = "Osiris-DevWorks/smart-citizen"


def create_embed(version: str, release_notes: str = "") -> dict:
    """Create a Discord embed for the release announcement."""
    release_url = f"https://github.com/{GITHUB_REPO}/releases/tag/{version}"

    description_parts = [
        "🎉 **Smart Citizen Release**\n",
    ]

    if release_notes.strip():
        description_parts.append(release_notes.strip())
    else:
        description_parts.append("Check the release page for more details.")

    description_parts.append(f"\n📥 **[View Release]({release_url})**")

    description = "\n".join(description_parts)
    # Discord embed descriptions have a 4096 character limit
    if len(description) > 4000:
        description = description[:3997] + "..."

    embed = {
        "title": f"Smart Citizen {version}",
        "description": description,
        "color": 0x1E90FF,  # Dodger blue
        "url": release_url,
        "footer": {
            "text": f"Smart Citizen {version}"
        }
    }

    return embed


def send_discord_notification(version: str, release_notes: str = "") -> bool:
    """Send release notification to Discord via webhook."""
    if not WEBHOOK_URL:
        print("Warning: DISCORD_RELEASE_WEBHOOK_URL not set in environment")
        print("Skipping Discord notification.")
        return False

    embed = create_embed(version, release_notes)

    payload = {
        "embeds": [embed],
        "username": "Smart Citizen",
    }

    data = json.dumps(payload).encode('utf-8')

    try:
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'SmartCitizen-Release-Bot/1.0'
            }
        )

        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                print(f"[SUCCESS] Posted release {version} to Discord!")
                return True
            else:
                print(f"[WARNING] Unexpected response status: {response.status}")
                return False

    except urllib.error.HTTPError as e:
        print(f"[ERROR] Failed to post to Discord: HTTP {e.code}")
        print(f"Response: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"[ERROR] Error posting to Discord: {e}")
        return False


def _resolve_release_notes(version: str, explicit_notes: str | None) -> str:
    """Three-tier resolution for the embed body.

    1. Explicit positional argument (legacy callers, tests).
    2. ``RELEASE_BODY`` env var (CI patterns that pre-load via env).
    3. ``{VERSION}-RELEASE-NOTES.md`` on disk — ``docs/`` first (their
       home since the 1.4.1 cleanup), repo root as the legacy fallback.
       This mirrors release.yml's "Resolve release notes" step; the two
       must agree or the GitHub release gets full notes while the
       Discord post degrades to the bare fallback line (the 1.4.1 and
       1.4.2 announcements shipped that way — only this tier had not
       learned the docs/ move).

    Returns ``""`` when nothing's available; the embed falls back to its
    "Check the release page for more details." default in that case.
    """
    if explicit_notes is not None and explicit_notes.strip():
        return explicit_notes
    env_notes = os.getenv("RELEASE_BODY", "")
    if env_notes.strip():
        return env_notes
    # Strip leading "v" from the tag so v1.3.0 → 1.3.0-RELEASE-NOTES.md
    version_bare = version.lstrip("v")
    for notes_file in (
        project_root / "docs" / f"{version_bare}-RELEASE-NOTES.md",
        project_root / f"{version_bare}-RELEASE-NOTES.md",
    ):
        if notes_file.exists():
            try:
                return notes_file.read_text(encoding="utf-8")
            except OSError as e:
                print(f"[WARNING] Could not read {notes_file}: {e}")
    return ""


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/discord_notify.py <version> [release_notes]")
        print("       (release_notes also resolved from $RELEASE_BODY env var")
        print("        or {VERSION}-RELEASE-NOTES.md if not given)")
        print("Example: python scripts/discord_notify.py v1.3.0")
        sys.exit(1)

    version = sys.argv[1]
    explicit_notes = sys.argv[2] if len(sys.argv) > 2 else None
    release_notes = _resolve_release_notes(version, explicit_notes)

    if release_notes:
        print(f"Posting release notification for {version} ({len(release_notes)} chars of notes)...")
    else:
        print(f"Posting release notification for {version} (no release notes resolved)...")

    success = send_discord_notification(version, release_notes)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

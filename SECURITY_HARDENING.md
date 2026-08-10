# Hardened build policy

This fork treats upstream application code, cached files, downloads, and build
dependencies as untrusted until reviewed.

## Runtime network policy

- Offline Security Mode is opt-in and fails closed if its setting cannot be
  read after it has been enabled. Automatic update and startup sync features
  remain removed regardless of this setting.
- A process-wide socket guard rejects and logs outbound connection attempts,
  including calls introduced by future application code.
- The optional community-language downloader checks the policy before creating
  any request. Cached language files remain usable while offline.
- External web links are blocked while Offline Security Mode is enabled; local
  folder links remain available.
- Disabling the lock requires an explicit confirmation in Config. Application
  self-updates remain disabled even while network access is unlocked.
- The application never checks for or installs application updates.
- Startup performs no network requests.
- The Test Plan cannot submit data to Discord.
- English localization, blueprints, missions, and item data come from the local
  Star Citizen `Data.p4k` installed and updated by the RSI Launcher.
- During Quick Setup, previously earned blueprints are imported only by reading
  the local `Game.log` and `logbackups` files in the selected game channel; no
  account service or network request is used.
- A network request occurs only when the user selects a non-English language
  whose community localization file is not cached.
- Language requests are restricted to the exact URLs committed in
  `languages/sources.json`. HTTPS, final redirect destination, a 32 MiB limit,
  UTF-8 decoding, basic INI structure, and atomic replacement are enforced.
- Downloaded language text is data only. It is never imported or executed.

## Native extraction tools

The application executes the bundled `unp4k.exe` and `unforge.exe` only after
checking every bundled executable and `libzstd.dll` against these SHA-256 values:

| File | SHA-256 |
|---|---|
| `unp4k.exe` | `753ff2556729a2e6c3b936ab6a510d0c80861a6b66837f3948c224d1160cca54` |
| `unforge.exe` | `6b7c07d8c61521e17951aa8cf7c63c624dfc093ac8afcc6daaf1be91c9954545` |
| `x86/libzstd.dll` | `7b6d1d65b95f7f170568ed81298f3875b7990962229b526d4492cc67e4f7a7dd` |
| `x64/libzstd.dll` | `9bef1e2c8eee89d9f54713f01808aacb195bbded5991e11f80b88d132b60f5e4` |

Changing a native component requires a new source review and an intentional
hash update. Hash matching detects modification; it does not prove the original
binary is harmless.

The Advanced view's **More** menu provides a *Hardened Build & Integrity
Report*. It repeats this same verification without running an extraction and
shows the result locally. The adjacent *Export Local Security Audit Log* action
copies the local JSON Lines record to a user-selected destination. Audit records
are never transmitted and currently cover Apply, emergency rollback, and audit
exports.

## Portable package integrity

Every portable build includes a `package-integrity.json` manifest containing
the size and SHA-256 hash of every packaged runtime file. The application
verifies that manifest before it creates its user interface and refuses to
launch if a listed file is missing or changed. The local `data/` folder is not
part of the manifest so normal settings, cache, backup, and audit-log writes
remain possible.

This is a tamper/corruption check, not a substitute for release verification:
always compare the downloaded ZIP's detached SHA-256 value with the value
published on the GitHub release page.

These two executables were built locally from the source snapshot in
`../odw-fast-unp4k` using the .NET 10 SDK. The reviewed source was hardened
before compilation:

- removed `unp4k`'s automatic exception upload to
  `https://herald.holoxplor.space`;
- removed its `HttpClient` dependency and all runtime networking;
- confined P4K entry output paths to the extraction directory; and
- confined DataForge record output paths to the extraction directory.
- converts top-level file-access exceptions into ordinary non-zero exits so
  Smart Citizen can explain the problem without a Windows CLR error popup.

The locally built binaries are unsigned. Their identity is enforced by the
SHA-256 allowlist above. The original vendor binaries are retained outside the
application tree under `../odw-fast-unp4k/vendor-original-binaries` for
comparison and rollback; they are not included in the portable package.

## Cache policy

Python pickle lookup caches are disabled. Enhancement lookups are rebuilt from
local game data because deserializing a tampered pickle can execute code.

## Trusted build procedure

1. Build from a reviewed commit with a clean worktree.
2. Create a fresh virtual environment.
3. Install only the exact versions in `requirements.txt`.
4. For the signed-update feature, install the separately hash-locked
   `requirements-update-security.txt` file from a reviewed local wheel
   directory. This prevents a build from silently fetching a replacement
   cryptography package during installation.
5. Run the full test suite.
6. Build the portable artifact with `python scripts/build/build_exe.py --portable`.
7. Record a SHA-256 hash for the completed portable ZIP and retain it with this
   source revision.
8. Do not replace the executable or any `_internal` file without rebuilding and
   repeating verification.

The update-signature dependency is locked in
`requirements-update-security.txt` for this Windows x86-64 build VM. Other
application dependencies remain version-pinned but are not yet fully
hash-locked across all platforms.

## Signed release keys

The future manual updater trusts an Ed25519 public key bundled in
`assets/release-signing-public-key.txt`. Its matching private key must stay on
a separate trusted signing machine and must never be placed in this repository,
a GitHub secret visible to untrusted workflows, or a portable package.

On that trusted machine, generate the pair once:

```powershell
python scripts/release/sign_release_manifest.py keygen C:\Secure\release-signing-private.pem C:\Secure\release-signing-public.txt
```

Copy only the generated public-key text into
`assets/release-signing-public-key.txt`, commit that public file, and keep the
private `.pem` offline/backed up. Every release manifest will be canonicalized
and signed there before the app accepts its ZIP hash.

For a machine that should not have Python installed, build and transfer the
offline `SmartCitizen-ReleaseSigner.exe` instead. It has no network features
and contains no private key:

```powershell
.\.venv\Scripts\python.exe scripts\release\build_release_signer.py
```

Verify the adjacent `.exe.sha256` file before transferring the EXE to the
trusted signing machine.

To prepare a built release without manually copying/signing each asset, run
the local-only helper from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\release\prepare_signed_release.ps1
```

It checks the ZIP hash and size against `release-manifest.json`, signs that
manifest, and creates `dist/release-upload-v<version>/` containing exactly the
ZIP, its SHA-256 file, the manifest, and its `.sig`. It does not upload to
GitHub or copy either key.

## Current local artifact

`dist/SmartCitizen-Portable-v2.3.0-hardened.3.zip`

SHA-256: `7025241905594a3573d3dbedca9bda892bec75841fd0084067a526572a39373f`

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
4. Run the full test suite.
5. Build the portable artifact with `python scripts/build/build_exe.py --portable`.
6. Record a SHA-256 hash for the completed portable ZIP and retain it with this
   source revision.
7. Do not replace the executable or any `_internal` file without rebuilding and
   repeating verification.

Package hashes are not yet recorded. Before treating a release build as final,
download the pinned wheels once, review their origin, generate a hash-locked
requirements file, and build offline from that local wheel set.

## Current local artifact

`dist/SmartCitizen-Portable-v2.3.0.zip`

SHA-256: `e8afe35285c785a8fd524bc5fc84b7095c829046a1667825328e88075b61517a`

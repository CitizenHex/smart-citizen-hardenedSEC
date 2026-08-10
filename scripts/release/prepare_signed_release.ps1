<#
Prepare the four assets for one Smart Citizen Hardened GitHub release.

This script is deliberately local-only: it never opens a network connection,
does not upload to GitHub, and never copies the private key. It verifies the
built ZIP against its manifest, asks the offline signer to sign that manifest,
and creates a single release-upload folder for drag-and-drop publishing.
#>
[CmdletBinding()]
param(
    [string]$SecureDirectory = "C:\Secure"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$distDirectory = Join-Path $projectRoot "dist"
$version = (Get-Content (Join-Path $projectRoot "VERSION.TXT") -Raw).Trim()
$zipName = "SmartCitizen-Hardened-v$version.zip"
$zipPath = Join-Path $distDirectory $zipName
$zipHashPath = "$zipPath.sha256"
$manifestPath = Join-Path $distDirectory "release-manifest.json"
$signerPath = Join-Path $distDirectory "release-signer\SmartCitizen-ReleaseSigner.exe"
$privateKeyPath = Join-Path $SecureDirectory "release-signing-private.pem"
$uploadDirectory = Join-Path $distDirectory "release-upload-v$version"

foreach ($required in @($zipPath, $zipHashPath, $manifestPath, $signerPath, $privateKeyPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required file is missing: $required"
    }
}
if (Test-Path -LiteralPath $uploadDirectory) {
    throw "Refusing to overwrite existing release folder: $uploadDirectory"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.version -ne $version -or $manifest.zip_name -ne $zipName) {
    throw "The release manifest does not match VERSION.TXT or the expected ZIP name. Build again."
}
$actualHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $manifest.zip_sha256.ToLowerInvariant()) {
    throw "ZIP SHA-256 does not match release-manifest.json. Refusing to sign."
}
if ((Get-Item -LiteralPath $zipPath).Length -ne [int64]$manifest.zip_size) {
    throw "ZIP size does not match release-manifest.json. Refusing to sign."
}

New-Item -ItemType Directory -Path $uploadDirectory | Out-Null
Copy-Item -LiteralPath $zipPath, $zipHashPath, $manifestPath -Destination $uploadDirectory
$uploadManifest = Join-Path $uploadDirectory "release-manifest.json"
$signaturePath = Join-Path $uploadDirectory "release-manifest.sig"

& $signerPath sign $privateKeyPath $uploadManifest $signaturePath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $signaturePath -PathType Leaf)) {
    throw "The offline signing utility did not produce a release-manifest.sig file."
}

Write-Host ""
Write-Host "Signed release assets are ready:" -ForegroundColor Green
Get-ChildItem -LiteralPath $uploadDirectory -File | Select-Object Name, Length
Write-Host ""
Write-Host "Upload exactly these four files to the matching GitHub release." -ForegroundColor Cyan

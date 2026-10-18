<#
  Builds dist\knowledgewala-agentic-sdlc-v<Version>.zip and a .sha256 file.
  .\scripts\build-release.ps1 -Version 1.0.0
#>
param([Parameter(Mandatory)][string]$Version)
$ErrorActionPreference = 'Stop'
$root  = Split-Path -Parent $PSScriptRoot
$dist  = Join-Path $root 'dist'
$name  = "knowledgewala-agentic-sdlc-v$Version"
$stage = Join-Path $dist $name
$zip   = Join-Path $dist "$name.zip"

New-Item -ItemType Directory -Force $dist | Out-Null
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
if (Test-Path $zip)   { Remove-Item $zip -Force }
New-Item -ItemType Directory $stage | Out-Null

$include = '.claude-plugin','agents','skills','scripts','templates','install','docs','media','tests','README.md','LICENSE','NOTICE.md','CHANGELOG.md'
foreach ($i in $include) { Copy-Item (Join-Path $root $i) $stage -Recurse -Force }

# render intermediates (png/wav/clips) are not part of the release
$mo = Join-Path $stage 'media\out'; if (Test-Path $mo) { Remove-Item $mo -Recurse -Force }
# the staging copy of build-release.ps1 is not needed by users
$self = Join-Path $stage 'scripts\build-release.ps1'; if (Test-Path $self) { Remove-Item $self -Force }

Compress-Archive -Path $stage -DestinationPath $zip -CompressionLevel Optimal
Remove-Item $stage -Recurse -Force
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
"$hash  $name.zip" | Set-Content "$zip.sha256" -Encoding ascii
Write-Host "Built $zip"; Write-Host "SHA256 $hash"

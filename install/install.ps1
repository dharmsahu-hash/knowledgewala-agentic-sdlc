<#
  KnowledgeWala Agentic SDLC installer (Windows). Thin wrapper over kw_install.py (needs Python 3).

  .\install\install.ps1                         # install for your user (all projects)
  .\install\install.ps1 -Scope project          # install into .\.claude of the current folder
  .\install\install.ps1 -Guardrail              # also enable the optional destructive-command hook
  .\install\install.ps1 -Uninstall              # remove exactly what was installed, restore your backups
#>
param(
  [ValidateSet('user','project')][string]$Scope = 'user',
  [switch]$Uninstall,
  [switch]$Guardrail,
  [switch]$Observe
)
$py = $null
foreach ($c in 'python3','python','py') { if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break } }
if (-not $py) { throw "Python 3 is required to run the installer. Install it from python.org, or copy agents/ and skills/ by hand (see README, Option C)." }
$script = Join-Path $PSScriptRoot 'kw_install.py'
$pyArgs = if ($py -eq 'py') { @('-3') } else { @() }
if ($Uninstall) { & $py @pyArgs $script uninstall --scope $Scope }
else {
  $extra = @(); if ($Guardrail) { $extra += '--guardrail' }; if ($Observe) { $extra += '--observe' }
  & $py @pyArgs $script install --scope $Scope @extra
}
exit $LASTEXITCODE

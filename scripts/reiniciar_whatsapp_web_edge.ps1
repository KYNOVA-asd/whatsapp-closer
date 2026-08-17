$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$profile = Join-Path $repo ".local\edge-whatsapp-profile"

if (Test-Path -LiteralPath $profile) {
  $resolvedProfile = (Resolve-Path -LiteralPath $profile).Path
} else {
  $resolvedProfile = $profile
}

Get-CimInstance Win32_Process -Filter "name = 'msedge.exe'" |
  Where-Object {
    $_.CommandLine -like "*$resolvedProfile*" -or
    $_.CommandLine -like "*edge-whatsapp-profile*"
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force
  }

Start-Sleep -Seconds 2

powershell -ExecutionPolicy Bypass -File (Join-Path $repo "scripts\abrir_whatsapp_web_edge.ps1")

param(
  [string]$ProfileDir = "",
  [int]$DebugPort = 9222,
  [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")

if ([string]::IsNullOrWhiteSpace($ProfileDir)) {
  $ProfileDir = Join-Path $repo ".local\edge-whatsapp-profile"
}

$edgeCandidates = @(
  "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
  "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
  "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
)

$edgePath = $null
foreach ($candidate in $edgeCandidates) {
  if (Test-Path -LiteralPath $candidate) {
    $edgePath = $candidate
    break
  }
}

if (-not $edgePath) {
  $command = Get-Command msedge -ErrorAction SilentlyContinue
  if ($command) {
    $edgePath = $command.Source
  }
}

if (-not $edgePath) {
  throw "No encontre Microsoft Edge. Instala Edge o pasa -ProfileDir y abre https://web.whatsapp.com manualmente."
}

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$resolvedProfile = (Resolve-Path -LiteralPath $ProfileDir).Path
$url = "https://web.whatsapp.com/"

Write-Host "Edge: $edgePath"
Write-Host "Perfil local: $resolvedProfile"
Write-Host "Debug local: http://127.0.0.1:$DebugPort"
Write-Host "URL: $url"

if ($NoLaunch) {
  Write-Host "Validacion lista. No se abrio Edge porque usaste -NoLaunch."
  exit 0
}

$args = @(
  "--user-data-dir=$resolvedProfile",
  "--profile-directory=Default",
  "--remote-debugging-address=127.0.0.1",
  "--remote-debugging-port=$DebugPort",
  "--no-first-run",
  "--new-window",
  $url
)

Start-Process -FilePath $edgePath -ArgumentList $args

Write-Host ""
Write-Host "Se abrio Edge con un perfil separado para WhatsApp Web."
Write-Host "Escanea el QR desde tu telefono. La sesion queda guardada en .local\edge-whatsapp-profile."

# run.ps1 - Build and run the photo frame for local testing on Windows.
# Compatible with Windows PowerShell 5.1+
#
# OPTION A - See the actual window (recommended):
#   1. Install VcXsrv: https://sourceforge.net/projects/vcxsrv/
#   2. Launch XLaunch: choose "Multiple windows", display 0,
#      tick "Disable access control", finish.
#   3. Run:  .\run.ps1
#
# OPTION B - Headless (logs only, no window):
#   .\run.ps1 -Headless
#
# Other flags:
#   .\run.ps1 -Photos C:\Users\you\Pictures   # custom photos folder
#   .\run.ps1 -Rebuild                         # force image rebuild
#   .\run.ps1 -Shell                           # bash shell inside container

param(
    [string]$Photos   = ".\photos",
    [switch]$Rebuild,
    [switch]$Shell,
    [switch]$Headless
)

$ErrorActionPreference = "Stop"
$ImageName     = "photo-frame-test"
$ContainerName = "photo-frame"

# Resolve photos path to absolute (PS 5.1 compatible - no ?. operator)
$resolved = Resolve-Path -Path $Photos -ErrorAction SilentlyContinue
if ($resolved) {
    $PhotosAbs = $resolved.Path
} else {
    New-Item -ItemType Directory -Path $Photos -Force | Out-Null
    $PhotosAbs = (Resolve-Path -Path $Photos).Path
}

Write-Host ""
Write-Host "+------------------------------------------+"
Write-Host "|       Photo Frame - Docker Test          |"
Write-Host "+------------------------------------------+"
Write-Host "  Photos : $PhotosAbs"

# Build
$imageExists = $false
try { docker image inspect $ImageName 2>&1 | Out-Null; $imageExists = ($LASTEXITCODE -eq 0) } catch {}
$needsBuild = $Rebuild -or (-not $imageExists)
if ($needsBuild) {
    Write-Host "`n  Building Docker image (this takes ~2 min the first time)..."
    docker build -t $ImageName .
    if ($LASTEXITCODE -ne 0) { Write-Error "Docker build failed."; exit 1 }
    Write-Host "  Build complete."
} else {
    Write-Host "  Using cached image  (use -Rebuild to force a fresh build)."
}

# Remove stale container
$exists = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $ContainerName }
if ($exists) {
    docker rm -f $ContainerName | Out-Null
}

# Determine DISPLAY_HOST
$DisplayHost = ""
if (-not $Headless) {
    # Docker Desktop on Windows routes host.docker.internal to your machine
    $DisplayHost = "host.docker.internal"
    Write-Host "`n  Mode    : Windowed  (VcXsrv required - see instructions above)"
    Write-Host "  Display : ${DisplayHost}:0.0"
} else {
    Write-Host "`n  Mode    : Headless  (log output only)"
}

Write-Host ""

# Run
$dockerArgs = @(
    "run", "--rm", "-it",
    "--name", $ContainerName,
    "-v", "${PhotosAbs}:/app/photos:ro",
    "-e", "DOCKER_TEST=1"
)

if ($DisplayHost) {
    $dockerArgs += @("-e", "DISPLAY_HOST=$DisplayHost")
}

if ($Shell) {
    Write-Host "  Dropping into shell. Run 'python3 main.py' to start."
    $dockerArgs += @("--entrypoint", "bash")
    $dockerArgs += $ImageName
} else {
    Write-Host "  Starting photo frame. Press Ctrl+C to stop."
    $dockerArgs += $ImageName
}

& docker @dockerArgs

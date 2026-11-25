# Build Credo OS from Windows using a Fedora WSL distribution.
# Usage (PowerShell):  .\build\build-wsl.ps1 [-Distro FedoraLinux-45] [-WithLibrary]
param(
    [string]$Distro = "",
    [switch]$WithLibrary
)
$ErrorActionPreference = "Stop"

$installed = (wsl.exe -l -q 2>$null) -replace "`0", "" | Where-Object { $_ -match "Fedora" }
if (-not $Distro) { $Distro = $installed | Select-Object -First 1 }
if (-not $Distro) {
    Write-Host "No Fedora WSL distribution found. Install one first (needs admin and a reboot the first time):"
    Write-Host "    wsl --install FedoraLinux-45 --no-launch   (see: wsl --list --online)"
    Write-Host "Then run this script again."
    exit 1
}

$src = (Resolve-Path "$PSScriptRoot\..").Path
$drive = $src.Substring(0,1).ToLower()
$wslPath = "/mnt/$drive" + ($src.Substring(2) -replace "\\", "/")
$extra = if ($WithLibrary) { "--with-library" } else { "" }

Write-Host "Building in WSL distro '$Distro' from $wslPath"
# Windows PowerShell treats a native program's stderr as an error under "Stop";
# dnf and livemedia-creator write progress there, so judge by the exit code instead.
$ErrorActionPreference = "Continue"
wsl.exe -d $Distro -u root -- bash -c "sed -i 's/\r$//' '$wslPath/build/build.sh' && bash '$wslPath/build/build.sh' --out '$wslPath/out' $extra" 2>&1 |
    ForEach-Object { "$_" }
$code = $LASTEXITCODE
if ($code -ne 0) { Write-Host "Build failed (exit $code). Log: wsl -d $Distro -- cat /var/tmp/credo-build/lmc.log" }
exit $code

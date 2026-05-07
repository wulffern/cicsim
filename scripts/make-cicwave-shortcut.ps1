<#
.SYNOPSIS
    Create a Windows shortcut (.lnk) that launches cicwave.

.DESCRIPTION
    Resolves cicwave.exe from PATH (or from -CicwavePath) and writes a
    cicwave.lnk next to this script. Drag the .lnk to your Desktop /
    Start menu / taskbar — or pass -OnDesktop to drop it there directly.

.PARAMETER OnDesktop
    Place the shortcut on the current user's Desktop instead of next to
    this script.

.PARAMETER CicwavePath
    Override auto-discovery and point the shortcut at a specific
    cicwave.exe.

.PARAMETER IconPath
    Override the default icon (cicsim/cicwave.ico shipped with the repo).

.EXAMPLE
    .\make-cicwave-shortcut.ps1
    # writes .\cicwave.lnk

.EXAMPLE
    .\make-cicwave-shortcut.ps1 -OnDesktop
    # writes %USERPROFILE%\Desktop\cicwave.lnk
#>

[CmdletBinding()]
param(
    [switch]$OnDesktop,
    [string]$CicwavePath,
    [string]$IconPath
)

$ErrorActionPreference = 'Stop'

# Repo-relative paths.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
$defaultIcon = Join-Path $repoRoot 'cicsim\cicwave.ico'

# 1) Resolve cicwave.exe.
if (-not $CicwavePath) {
    $cmd = Get-Command cicwave.exe -ErrorAction SilentlyContinue
    if (-not $cmd) {
        $cmd = Get-Command cicwave -ErrorAction SilentlyContinue
    }
    if (-not $cmd) {
        throw "cicwave not found on PATH. Install with 'pip install -e .' " +
              "from the repo root, or pass -CicwavePath <full path>."
    }
    $CicwavePath = $cmd.Source
}
if (-not (Test-Path -LiteralPath $CicwavePath)) {
    throw "cicwave executable does not exist: $CicwavePath"
}

# 2) Resolve icon.
if (-not $IconPath) { $IconPath = $defaultIcon }
if (-not (Test-Path -LiteralPath $IconPath)) {
    Write-Warning "Icon not found at $IconPath - using default exe icon."
    $IconPath = $CicwavePath
}

# 3) Pick destination.
if ($OnDesktop) {
    $destDir = [Environment]::GetFolderPath('Desktop')
} else {
    $destDir = $scriptDir
}
$lnkPath = Join-Path $destDir 'cicwave.lnk'

# 4) Build the .lnk via WScript.Shell.
$shell    = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath       = $CicwavePath
$shortcut.WorkingDirectory = [Environment]::GetFolderPath('UserProfile')
$shortcut.IconLocation     = "$IconPath,0"
$shortcut.Description      = 'cicwave waveform viewer (cicsim)'
$shortcut.Save()

Write-Host "Created shortcut:" -ForegroundColor Green
Write-Host "  $lnkPath"
Write-Host "  -> $CicwavePath"
Write-Host "  icon: $IconPath"
if (-not $OnDesktop) {
    Write-Host ""
    Write-Host "Drag cicwave.lnk to your Desktop, Start menu, or taskbar."
}

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
    cicwave executable.

.PARAMETER WithConsole
    Use cicwave.exe (which opens a console window) instead of the
    silent cicwavew.exe wrapper. Handy when you want to see startup
    log output for debugging.

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
    [switch]$WithConsole,
    [string]$CicwavePath,
    [string]$IconPath
)

$ErrorActionPreference = 'Stop'

# Repo-relative paths.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
$defaultIcon = Join-Path $repoRoot 'cicsim\cicwave.ico'

# 1) Resolve the cicwave executable. Prefer cicwavew.exe (no console
#    window) for shortcut launches; fall back to cicwave.exe if the
#    GUI wrapper isn't installed (older cicsim versions).
if (-not $CicwavePath) {
    $names = if ($WithConsole) { @('cicwave.exe', 'cicwave') }
             else              { @('cicwavew.exe', 'cicwavew',
                                    'cicwave.exe', 'cicwave') }
    $cmd = $null
    foreach ($n in $names) {
        $cmd = Get-Command $n -ErrorAction SilentlyContinue
        if ($cmd) { break }
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

$exeName = [System.IO.Path]::GetFileName($CicwavePath)
if ($exeName -ieq 'cicwave.exe' -and -not $WithConsole) {
    Write-Warning ("Using cicwave.exe - a console window will appear when " +
                   "the shortcut is double-clicked. Reinstall cicsim " +
                   ">= 0.2.9 to get cicwavew.exe (silent), or pass " +
                   "-WithConsole to suppress this warning.")
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

# AWS CLI v2 install script for Windows (PowerShell 5.1+).
#
# Defaults to a user-local install under %LOCALAPPDATA%. Use -System for the
# traditional Program Files layout (requires admin). See -Help for details.

param(
    [string] $Version,  # specific version to install; empty means "latest"
    [switch] $System,   # install system-wide (Program Files); requires admin
    [switch] $Quiet,    # suppress non-essential stdout
    [switch] $Help
)

# Stop on any error so failures don't silently continue.
$ErrorActionPreference = 'Stop'
# PowerShell 5.1 defaults to TLS 1.0; force 1.2 for the CDN.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# ============================================================================
# Configuration
# ============================================================================

$DownloadBaseUrl    = 'https://awscli.amazonaws.com'
$LatestVersionUrl   = "$DownloadBaseUrl/v2/version.txt"

# The system MSI always installs to the 64-bit Program Files. Use
# ProgramW6432, which points there even from a 32-bit PowerShell host;
# $env:ProgramFiles would resolve to "Program Files (x86)" under 32-bit
# and make the post-install check look in the wrong place.
$SystemProgramFiles = $env:ProgramW6432
if (-not $SystemProgramFiles) { $SystemProgramFiles = $env:ProgramFiles }
$SystemInstallDir   = Join-Path $SystemProgramFiles 'Amazon\AWSCLIV2'
$UserInstallDir     = Join-Path $env:LOCALAPPDATA 'Programs\Amazon\AWSCLIV2'

$DistributionSource = 'script-exe'
if ($env:AWS_CLI_DISTRIBUTION_SOURCE_OVERRIDE) {
    $DistributionSource = $env:AWS_CLI_DISTRIBUTION_SOURCE_OVERRIDE
}
$DownloadQuery = "?src=$DistributionSource"

$MsiexecSuccessCodes = @(0, 1641, 3010)

# ============================================================================
# Output helpers
# ============================================================================

$EscRed    = [char]27 + '[31m'
$EscYellow = [char]27 + '[33m'
$EscGreen  = [char]27 + '[32m'
$EscReset  = [char]27 + '[0m'

function Use-Color {
    param([bool] $IsErrStream)
    if ($env:NO_COLOR) { return $false }
    if ($IsErrStream) { return -not [Console]::IsErrorRedirected }
    return -not [Console]::IsOutputRedirected
}

# Progress/info on stdout, silenced by -Quiet.
function Write-Info {
    param([string] $Message)
    if (-not $Quiet) { Write-Host $Message }
}

# Green success on stdout, silenced by -Quiet.
function Write-Success {
    param([string] $Message)
    if ($Quiet) { return }
    if (Use-Color $false) {
        Write-Host "$EscGreen$Message$EscReset"
    } else {
        Write-Host $Message
    }
}

# Yellow warning on stderr; never silenced.
function Write-Warn {
    param([string] $Message)
    if (Use-Color $true) {
        [Console]::Error.WriteLine("${EscYellow}aws-cli installer: warning:${EscReset} $Message")
    } else {
        [Console]::Error.WriteLine("aws-cli installer: warning: $Message")
    }
}

# Red error on stderr; never silenced.
function Write-Err {
    param([string] $Message)
    if (Use-Color $true) {
        [Console]::Error.WriteLine("${EscRed}aws-cli installer: error:${EscReset} $Message")
    } else {
        [Console]::Error.WriteLine("aws-cli installer: error: $Message")
    }
}

# Record the exit code and throw to unwind. We never call `exit` here: under
# `irm | iex` the script runs in the caller's session, so `exit` would close
# the user's PowerShell. The error is printed by the top-level handler (which
# also reports any other exception), so nothing is silently swallowed; the
# recorded code becomes a process exit status only when run as a file.
$Script:ExitCode = 0
function Throw-Error {
    param([int] $Code, [string] $Message)
    $Script:ExitCode = $Code
    throw $Message
}

# ============================================================================
# Argument validation
# ============================================================================

function Show-Help {
    @"
Usage: install.ps1 [-Version <X.Y.Z>] [-System] [-Quiet] [-Help]

Install or update the AWS CLI v2.

Parameters:
  -Version <X.Y.Z>  Install a specific fully-qualified version. Otherwise
                    installs the latest release. Downgrades are not
                    supported. To install a previous version, see:
                    https://docs.aws.amazon.com/cli/latest/userguide/getting-started-version.html
  -System           Install system-wide (requires admin). Otherwise installs
                    under %LOCALAPPDATA%\Programs\Amazon\AWSCLIV2\.
  -Quiet            Suppress non-essential output. Errors and warnings are
                    still printed to stderr.
  -Help             Show this help and exit.
"@ | Write-Host
}

# Accept only fully-qualified MAJOR.MINOR.PATCH.
function Test-Semver {
    param([string] $Value)
    return ($Value -match '^\d+\.\d+\.\d+$')
}

# Returns $false when the run should stop early without error.
function Validate-Args {
    if ($Help) { Show-Help; return $false }
    if ($Version -and -not (Test-Semver $Version)) {
        Throw-Error 2 "-Version must be fully-qualified semver (e.g. 2.27.41), got: $Version"
    }
    return $true
}

# ============================================================================
# Pre-install checks
# ============================================================================

function Test-Windows {
    if ($PSVersionTable.PSVersion.Major -ge 6) {
        return $IsWindows
    }
    return $true
}

function Assert-Platform {
    if (-not (Test-Windows)) {
        Throw-Error 1 'unsupported OS. install.ps1 supports only Windows; use install.sh on Linux/macOS.'
    }
}

function Test-IsAdmin {
    $identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-SystemPrivilege {
    if ($System -and -not (Test-IsAdmin)) {
        Throw-Error 1 '-System requires admin privileges. Re-run from an elevated PowerShell, or omit -System for a user-local install.'
    }
}

# ============================================================================
# Path resolution
# ============================================================================

$Script:InstallDir = $null

function Resolve-InstallPath {
    if ($System) {
        $Script:InstallDir = $SystemInstallDir
    } else {
        if (-not $env:LOCALAPPDATA) {
            Throw-Error 2 'LOCALAPPDATA is not set; cannot resolve user-local install path.'
        }
        $Script:InstallDir = $UserInstallDir
    }
}

# ============================================================================
# Download
# ============================================================================

$Script:TempDir = $null   # working dir; removed in the finally block

function New-TempDir {
    $Script:TempDir = Join-Path $env:TEMP "aws-cli-install-$([guid]::NewGuid().Guid)"
    New-Item -ItemType Directory -Path $Script:TempDir -Force | Out-Null
}

function Remove-TempDir {
    if ($Script:TempDir -and (Test-Path $Script:TempDir)) {
        try {
            Remove-Item -Recurse -Force $Script:TempDir -ErrorAction Stop
        } catch {
            Write-Warn "could not remove temp directory: $Script:TempDir"
        }
    }
}

function Get-InstallerFilename {
    if ($System) {
        if ($Script:TargetVersion) {
            return "AWSCLIV2-$($Script:TargetVersion).msi"
        }
        return 'AWSCLIV2.msi'
    }
    if ($Script:TargetVersion) {
        return "AWSCLIV2-User-$($Script:TargetVersion).msi"
    }
    return 'AWSCLIV2-User.msi'
}

function Get-InstallerUrl {
    return "$DownloadBaseUrl/$(Get-InstallerFilename)$DownloadQuery"
}

function Download-File {
    param([string] $Url, [string] $Out)
    Invoke-WebRequest -Uri $Url -OutFile $Out -UseBasicParsing -TimeoutSec 60
}

function Download-WithRetry {
    param([string] $Url, [string] $Out, [string] $Label)
    Write-Info "Downloading $Label from $Url"
    try {
        Download-File -Url $Url -Out $Out
        return
    } catch {
        Write-Warn "download of $Label failed; retrying once"
    }
    try {
        Download-File -Url $Url -Out $Out
    } catch {
        Throw-Error 1 "failed to download $Label from $Url after one retry: $($_.Exception.Message)"
    }
}

$Script:InstallerPath = $null

function Download-Installer {
    $Script:InstallerPath = Join-Path $Script:TempDir 'AWSCLIV2.msi'
    Download-WithRetry -Url (Get-InstallerUrl) -Out $Script:InstallerPath -Label 'AWS CLI installer'
}

# ============================================================================
# Signature verification
# ============================================================================

function Verify-Installer {
    $sig = Get-AuthenticodeSignature -FilePath $Script:InstallerPath
    if ($sig.Status -ne 'Valid') {
        Throw-Error 1 ("Authenticode signature verification failed for " +
            "$($Script:InstallerPath): status is '$($sig.Status)'. " +
            'Refusing to install.')
    }

    Write-Success 'MSI Authenticode signature verified.'
}

# ============================================================================
# Version resolution
# ============================================================================

# Extracts the semver from `aws --version`.
function Read-InstalledVersion {
    param([string] $AwsExe)
    if (-not (Test-Path $AwsExe)) { return $null }
    try {
        $out = & $AwsExe --version 2>$null
    } catch {
        return $null
    }
    if ($out -match '^aws-cli/(\d+\.\d+\.\d+)') {
        return $Matches[1]
    }
    return $null
}

function Get-CandidateAwsBinary {
    return Join-Path $Script:InstallDir 'aws.exe'
}

$Script:PreInstallVersion  = $null   # version present before install
$Script:TargetVersion      = $null   # version we resolved to install
$Script:PostInstallVersion = $null   # version present after install

function Capture-PreInstallVersion {
    $Script:PreInstallVersion = Read-InstalledVersion (Get-CandidateAwsBinary)
}

# Best-effort fetch of the published "latest" version; $null on any failure.
function Fetch-LatestVersion {
    try {
        $resp = Invoke-WebRequest -Uri $LatestVersionUrl -UseBasicParsing -TimeoutSec 10
        $text = ([string] $resp.Content).Trim()
        if (Test-Semver $text) { return $text }
    } catch {}
    return $null
}

function Resolve-TargetAndAnnounce {
    if ($Version) {
        $Script:TargetVersion = $Version
    } else {
        $Script:TargetVersion = Fetch-LatestVersion
    }

    if (-not $Script:TargetVersion -or -not $Script:PreInstallVersion) {
        if ($Script:TargetVersion) {
            Write-Info "Installing AWS CLI $($Script:TargetVersion)"
        }
        return $true
    }

    if ($Script:TargetVersion -eq $Script:PreInstallVersion) {
        Write-Info "AWS CLI $($Script:TargetVersion) is already installed at $($Script:InstallDir); nothing to do."
        return $false
    }

    if ([version]$Script:TargetVersion -lt [version]$Script:PreInstallVersion) {
        Write-Info "AWS CLI $($Script:PreInstallVersion) is already installed at $($Script:InstallDir). To install $($Script:TargetVersion), uninstall the existing AWS CLI at $($Script:InstallDir) and try again. See https://docs.aws.amazon.com/cli/latest/userguide/uninstall.html"
        return $false
    }

    Write-Info "Installing AWS CLI $($Script:PreInstallVersion) -> $($Script:TargetVersion)"
    return $true
}

# ============================================================================
# Install
# ============================================================================

function Run-Installer {
    $msiFilename = Split-Path $Script:InstallerPath -Leaf
    $msiDir = Split-Path $Script:InstallerPath -Parent

    $msiArgs = @('/i', $msiFilename, '/qn', '/norestart')

    Write-Info 'Running MSI installer...'
    $proc = Start-Process -FilePath 'msiexec' -ArgumentList $msiArgs `
                          -WorkingDirectory $msiDir -Wait -PassThru
    if ($MsiexecSuccessCodes -notcontains $proc.ExitCode) {
        Throw-Error 8 "msiexec failed with exit code $($proc.ExitCode)"
    }
}

# ============================================================================
# Post-install
# ============================================================================

function Verify-InstallRuns {
    $awsExe = Get-CandidateAwsBinary
    $Script:PostInstallVersion = Read-InstalledVersion $awsExe
    if (-not $Script:PostInstallVersion) {
        Throw-Error 9 "post-install check failed: '$awsExe --version' did not run successfully."
    }
}

# Writes install-time metadata next to the bundled metadata.json. `aws update`
# reads this back to learn where and how the CLI was installed. No bin_dir
# field - on Windows the MSI manages PATH, there's no symlink dir to record.
function Write-InstallJson {
    $installJson = Join-Path $Script:InstallDir 'awscli\data\install.json'
    $parent = Split-Path $installJson -Parent
    if (-not (Test-Path $parent)) { return }

    $obj = [ordered]@{
        distribution_source = $DistributionSource
        install_dir         = $Script:InstallDir
        script_install      = [ordered]@{
            system           = [bool]$System
            version_resolved = $Script:PostInstallVersion
            quiet            = [bool]$Quiet
        }
    }
    $json = $obj | ConvertTo-Json -Depth 3
    [IO.File]::WriteAllText($installJson, $json, (New-Object Text.UTF8Encoding $false))
}

function Invoke-PostInstallChecks {
    Verify-InstallRuns
    Write-InstallJson
    Write-Success "AWS CLI $($Script:PostInstallVersion) installed to $($Script:InstallDir)"
    Write-Info "When multiple installs exist, PATH order determines which 'aws' runs."
}

# ============================================================================
# Entry point
# ============================================================================

function Invoke-Main {
    try {
        # Pre-flight: validate args and environment before touching disk/network.
        if (-not (Validate-Args)) { return }
        Assert-Platform
        Assert-SystemPrivilege
        Resolve-InstallPath

        # Install: stage, resolve target (may short-circuit), download, run.
        New-TempDir
        Capture-PreInstallVersion
        if (-not (Resolve-TargetAndAnnounce)) { return }
        Download-Installer
        Verify-Installer
        Run-Installer
        Invoke-PostInstallChecks
    } finally {
        # Always remove the temp dir, even on error or early return.
        Remove-TempDir
    }
}

# Run the body inside a scriptblock and catch errors here rather than calling
# `exit` from deep in the script. Under `irm | iex` the script shares the
# caller's session, so `exit` would close the user's PowerShell window. All
# errors are printed here -- both Throw-Error (which sets $Script:ExitCode)
# and any other exception raised under $ErrorActionPreference = 'Stop' -- so
# nothing is silently swallowed.
& {
    try {
        Invoke-Main
    } catch {
        Write-Err $_.Exception.Message
        if ($Script:ExitCode -eq 0) { $Script:ExitCode = 1 }
    }
}

# Only set a real process exit status when invoked as a file (powershell
# -File, or .\install.ps1), where $PSCommandPath is populated. Under
# `irm | iex` $PSCommandPath is empty and calling `exit` would terminate the
# user's shell, so we leave it alone there.
if ($PSCommandPath) {
    exit $Script:ExitCode
}

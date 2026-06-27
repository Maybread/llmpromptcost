param(
    [string]$RepoUrl = "https://github.com/Maybread/llmpromptcost.git",
    [string]$Branch = "main",
    [string]$CommitMessage = "",
    [switch]$Watch,
    [int]$IntervalSeconds = 300,
    [switch]$SkipPull,
    [switch]$AllowUnrelatedHistories
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message"
}

function Find-Git {
    $fromPath = Get-Command git -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    $candidates = @(
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files (x86)\Git\cmd\git.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "Git was not found. Install Git for Windows, or add git.exe to PATH."
}

$Git = Find-Git

function Invoke-Git {
    param([string[]]$Arguments)

    $display = "git " + ($Arguments -join " ")
    & $Git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$display failed with exit code $LASTEXITCODE."
    }
}

function Test-GitCommand {
    param([string[]]$Arguments)

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Git @Arguments *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Get-GitText {
    param([string[]]$Arguments)

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $text = & $Git @Arguments 2>$null
        if ($LASTEXITCODE -ne 0) {
            return ""
        }

        return ($text -join "`n").Trim()
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Initialize-Repository {
    if (Test-GitCommand @("rev-parse", "--is-inside-work-tree")) {
        return
    }

    if (Test-Path -LiteralPath ".git") {
        Write-Step "Found .git, but it is not a valid repository yet"
    }

    Write-Step "Initializing local Git repository"
    & $Git init -b $Branch
    if ($LASTEXITCODE -ne 0) {
        Invoke-Git @("init")
        Invoke-Git @("branch", "-M", $Branch)
    }
}

function Ensure-Branch {
    $currentBranch = Get-GitText @("branch", "--show-current")
    if ($currentBranch -eq $Branch) {
        return
    }

    Write-Step "Switching to branch $Branch"
    if (Test-GitCommand @("show-ref", "--verify", "--quiet", "refs/heads/$Branch")) {
        Invoke-Git @("switch", $Branch)
    }
    else {
        Invoke-Git @("switch", "-c", $Branch)
    }
}

function Ensure-Remote {
    $remoteUrl = Get-GitText @("remote", "get-url", "origin")
    if ([string]::IsNullOrWhiteSpace($remoteUrl)) {
        Write-Step "Adding origin remote: $RepoUrl"
        Invoke-Git @("remote", "add", "origin", $RepoUrl)
        return
    }

    if ($remoteUrl -ne $RepoUrl) {
        Write-Step "Updating origin remote from $remoteUrl to $RepoUrl"
        Invoke-Git @("remote", "set-url", "origin", $RepoUrl)
    }
}

function Test-RemoteBranch {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Git ls-remote --exit-code --heads origin $Branch *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Test-RepositoryHasCommit {
    return Test-GitCommand @("rev-parse", "--verify", "HEAD")
}

function Commit-LocalChanges {
    Invoke-Git @("add", "-A")

    if (Test-GitCommand @("diff", "--cached", "--quiet")) {
        Write-Step "No local file changes to commit"
        return $false
    }

    if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
        $message = "sync: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    }
    else {
        $message = $CommitMessage
    }

    Write-Step "Creating commit: $message"
    Invoke-Git @("commit", "-m", $message)
    return $true
}

function Pull-RemoteChanges {
    if ($SkipPull) {
        Write-Step "Skipping pull"
        return
    }

    Write-Step "Fetching remote changes"
    Invoke-Git @("fetch", "origin")

    if (-not (Test-RemoteBranch)) {
        Write-Step "Remote branch origin/$Branch does not exist yet"
        return
    }

    if (-not (Test-RepositoryHasCommit)) {
        Write-Step "Local repository has no commits yet"
        return
    }

    if ($AllowUnrelatedHistories) {
        Write-Step "Merging origin/$Branch with unrelated histories allowed"
        Invoke-Git @("merge", "origin/$Branch", "--allow-unrelated-histories", "--no-edit")
    }
    else {
        Write-Step "Rebasing local commits on origin/$Branch"
        Invoke-Git @("pull", "--rebase", "origin", $Branch)
    }
}

function Push-LocalChanges {
    if (-not (Test-RepositoryHasCommit)) {
        Write-Step "Nothing to push because there are no commits"
        return
    }

    Write-Step "Pushing to origin/$Branch"
    Invoke-Git @("push", "-u", "origin", $Branch)
}

function Sync-Once {
    Write-Step "Project root: $ProjectRoot"
    Write-Step "Using Git: $Git"

    Initialize-Repository
    Ensure-Branch
    Ensure-Remote
    $committed = Commit-LocalChanges
    Pull-RemoteChanges

    if ($committed -or (Test-RemoteBranch)) {
        Push-LocalChanges
    }
    else {
        Write-Step "No remote branch and no local commit to push"
    }

    Write-Step "Sync finished"
}

if ($Watch -and $IntervalSeconds -lt 10) {
    throw "IntervalSeconds must be at least 10 when -Watch is used."
}

if ($Watch) {
    Write-Step "Watch mode enabled. Press Ctrl+C to stop."
    while ($true) {
        try {
            Sync-Once
        }
        catch {
            Write-Error $_
        }

        Start-Sleep -Seconds $IntervalSeconds
    }
}
else {
    Sync-Once
}

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('begin','progress','proposal','error','clear')]
    [string]$Operation,

    [Parameter(Mandatory=$false)]
    [string]$TaskManifest,

    [Parameter(Mandatory=$false)]
    [string]$DriveRoot = 'G:\Meine Ablage\ChatGPT_Projekte\DeepThought_Away',

    [Parameter(Mandatory=$false)]
    [string]$RuntimeRoot = 'C:\DeepThought',

    [Parameter(Mandatory=$false)]
    [int]$ProgressSeq = -1,

    [Parameter(Mandatory=$false)]
    [string]$ProposalFile,

    [Parameter(Mandatory=$false)]
    [string]$ErrorCode = 'worker_error',

    [Parameter(Mandatory=$false)]
    [string]$ErrorMessage = 'worker reported an error'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$TaskSchema = 'loop42.drive-task.v1'
$SessionSchema = 'loop42.windows-worker-session.v1'
$ArtifactSchema = 'loop42.drive-artifact.v1'
$SessionPath = Join-Path $RuntimeRoot 'loop42-worker-session.json'
$Results = Join-Path $DriveRoot '10_Results'
$Errors = Join-Path $DriveRoot '95_Error'

function Write-AtomicJson {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)]$Value
    )
    $directory = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        throw "Target directory unavailable: $directory"
    }
    $temp = Join-Path $directory ('.{0}.{1}.{2}.tmp' -f (Split-Path -Leaf $Path), $PID, [guid]::NewGuid().ToString('N'))
    $json = $Value | ConvertTo-Json -Depth 10
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    try {
        [System.IO.File]::WriteAllText($temp, $json + [Environment]::NewLine, $utf8NoBom)
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            [System.IO.File]::Replace($temp, $Path, $null)
        }
        else {
            [System.IO.File]::Move($temp, $Path)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temp -PathType Leaf) {
            Remove-Item -LiteralPath $temp -Force
        }
    }
}

function Read-StrictTask {
    if ([string]::IsNullOrWhiteSpace($TaskManifest)) {
        throw 'TaskManifest is required for this operation'
    }
    if (-not (Test-Path -LiteralPath $TaskManifest -PathType Leaf)) {
        throw "Task manifest unavailable: $TaskManifest"
    }

    $raw = Get-Content -LiteralPath $TaskManifest -Raw -Encoding UTF8
    $value = $raw | ConvertFrom-Json

    if ($value.schema -ne $TaskSchema) { throw "task schema must be $TaskSchema" }

    foreach ($name in @('task_id','attempt_id','source_revision','context_fingerprint','observed_at')) {
        if ([string]::IsNullOrWhiteSpace([string]$value.$name)) {
            throw "task field missing: $name"
        }
    }
    if ($null -eq $value.acceptance_criteria) {
        throw 'task field missing: acceptance_criteria'
    }

    return $value
}

function Current-Session {
    if (-not (Test-Path -LiteralPath $SessionPath -PathType Leaf)) {
        throw 'worker session identity is missing'
    }
    $value = (Get-Content -LiteralPath $SessionPath -Raw -Encoding UTF8) | ConvertFrom-Json
    if ($value.schema -ne $SessionSchema) { throw 'worker session schema mismatch' }
    return $value
}

function Assert-SessionMatchesTask {
    param($Session, $Task)
    if (
        [string]$Session.task_id -ne [string]$Task.task_id -or
        [string]$Session.attempt_id -ne [string]$Task.attempt_id
    ) {
        throw 'worker session does not match task identity'
    }
}

function Artifact-Base {
    param(
        [Parameter(Mandatory=$true)]$Task,
        [Parameter(Mandatory=$true)][string]$Kind
    )
    return [ordered]@{
        schema = $ArtifactSchema
        kind = $Kind
        task_id = [string]$Task.task_id
        attempt_id = [string]$Task.attempt_id
        source_revision = [string]$Task.source_revision
        context_fingerprint = [string]$Task.context_fingerprint
        observed_at = ([datetimeoffset]::Now.ToUniversalTime().ToString('o'))
        complete = $true
        valid = $true
    }
}

if (-not (Test-Path -LiteralPath $RuntimeRoot -PathType Container)) {
    throw "Runtime root unavailable: $RuntimeRoot"
}

switch ($Operation) {
    'begin' {
        $task = Read-StrictTask
        if (Test-Path -LiteralPath $SessionPath -PathType Leaf) {
            throw 'worker session already exists; reconcile before begin'
        }
        $session = [ordered]@{
            schema = $SessionSchema
            session_id = 'worker-' + [guid]::NewGuid().ToString('N')
            task_id = [string]$task.task_id
            attempt_id = [string]$task.attempt_id
            process_id = $PID
            progress_seq = 0
            progress_at = ([datetimeoffset]::Now.ToUniversalTime().ToString('o'))
        }
        Write-AtomicJson -Path $SessionPath -Value $session
        $session | ConvertTo-Json -Depth 6
    }

    'progress' {
        if ($ProgressSeq -lt 1) { throw 'ProgressSeq must be >= 1' }
        $task = Read-StrictTask
        $session = Current-Session
        Assert-SessionMatchesTask -Session $session -Task $task
        if ($ProgressSeq -le [int]$session.progress_seq) {
            throw 'ProgressSeq must increase monotonically'
        }
        $session.progress_seq = $ProgressSeq
        $session.progress_at = ([datetimeoffset]::Now.ToUniversalTime().ToString('o'))
        Write-AtomicJson -Path $SessionPath -Value $session
        $session | ConvertTo-Json -Depth 6
    }

    'error' {
        $task = Read-StrictTask
        $session = Current-Session
        Assert-SessionMatchesTask -Session $session -Task $task

        if ([string]::IsNullOrWhiteSpace($ErrorCode)) { throw 'ErrorCode must be non-empty' }
        if ([string]::IsNullOrWhiteSpace($ErrorMessage)) { throw 'ErrorMessage must be non-empty' }

        $artifact = Artifact-Base -Task $task -Kind 'error'
        $artifact.success = $false
        $artifact.error_code = $ErrorCode
        $artifact.error_message = $ErrorMessage

        # The generic Drive adapter intentionally ignores provider-only error
        # detail fields today. Persist a strict provider-neutral companion
        # artifact separately, and keep the canonical .error.json minimal.
        $canonical = [ordered]@{
            schema = $ArtifactSchema
            kind = 'error'
            task_id = [string]$task.task_id
            attempt_id = [string]$task.attempt_id
            source_revision = [string]$task.source_revision
            context_fingerprint = [string]$task.context_fingerprint
            observed_at = $artifact.observed_at
            complete = $true
            valid = $true
            success = $false
        }
        $target = Join-Path $Errors ('{0}__{1}.error.json' -f $task.task_id, $task.attempt_id)
        Write-AtomicJson -Path $target -Value $canonical
        $target
    }

    'proposal' {
        $task = Read-StrictTask
        $session = Current-Session
        Assert-SessionMatchesTask -Session $session -Task $task

        if ([string]::IsNullOrWhiteSpace($ProposalFile)) {
            throw 'ProposalFile is required'
        }
        if (-not (Test-Path -LiteralPath $ProposalFile -PathType Leaf)) {
            throw "Proposal file unavailable: $ProposalFile"
        }

        $proposalHash = (Get-FileHash -LiteralPath $ProposalFile -Algorithm SHA256).Hash.ToLowerInvariant()
        $proposal = [ordered]@{
            schema = 'loop42.drive-worker-proposal.v1'
            task_id = [string]$task.task_id
            attempt_id = [string]$task.attempt_id
            source_revision = [string]$task.source_revision
            context_fingerprint = [string]$task.context_fingerprint
            observed_at = ([datetimeoffset]::Now.ToUniversalTime().ToString('o'))
            proposal_sha256 = $proposalHash
            proposal_file = [System.IO.Path]::GetFileName($ProposalFile)
            verified = $false
        }
        $target = Join-Path $Results ('{0}__{1}.proposal.json' -f $task.task_id, $task.attempt_id)
        Write-AtomicJson -Path $target -Value $proposal
        $target
    }

    'clear' {
        if (-not (Test-Path -LiteralPath $SessionPath -PathType Leaf)) {
            throw 'worker session identity is already absent'
        }
        Remove-Item -LiteralPath $SessionPath -Force
        'cleared'
    }
}

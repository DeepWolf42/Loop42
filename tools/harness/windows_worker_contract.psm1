Set-StrictMode -Version Latest

$script:TaskSchema = 'loop42.drive-task.v1'
$script:WorkerSessionSchema = 'loop42.windows-worker-session.v1'
$script:ProposalSchema = 'loop42.drive-proposal.v1'

function Test-Loop42Id([string]$Value) {
    return ($null -ne $Value -and $Value -match '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$')
}

function Test-Loop42Fingerprint([string]$Value) {
    return ($null -ne $Value -and $Value -match '^[0-9a-f]{64}$')
}

function Write-Loop42AtomicJson(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)]$Value
) {
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Target directory unavailable: $parent"
    }

    $json = $Value | ConvertTo-Json -Depth 12
    $temp = Join-Path $parent ('.loop42.{0}.{1}.tmp' -f $PID, [guid]::NewGuid().ToString('N'))
    try {
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText(
            $temp,
            $json + [Environment]::NewLine,
            $utf8NoBom
        )
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

function Read-Loop42TaskManifest(
    [Parameter(Mandatory=$true)][string]$Path
) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Task manifest unavailable: $Path"
    }

    $value = (Get-Content -LiteralPath $Path -Raw -Encoding UTF8) | ConvertFrom-Json
    if ($value.schema -ne $script:TaskSchema) { throw 'task manifest schema mismatch' }
    if (-not (Test-Loop42Id ([string]$value.task_id))) { throw 'invalid task_id' }
    if (-not (Test-Loop42Id ([string]$value.attempt_id))) { throw 'invalid attempt_id' }
    if ([string]$value.source_revision -notmatch '^[0-9a-f]{7,64}$') { throw 'invalid source_revision' }
    if (-not (Test-Loop42Fingerprint ([string]$value.context_fingerprint))) {
        throw 'invalid context_fingerprint'
    }
    if ($null -eq $value.acceptance_criteria -or @($value.acceptance_criteria).Count -eq 0) {
        throw 'acceptance_criteria missing'
    }
    return $value
}

function Start-Loop42WorkerSession {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$TaskManifestPath,
        [Parameter(Mandatory=$false)][string]$RuntimeRoot = 'C:\DeepThought'
    )

    $task = Read-Loop42TaskManifest -Path $TaskManifestPath
    if (-not (Test-Path -LiteralPath $RuntimeRoot -PathType Container)) {
        throw "Runtime root unavailable: $RuntimeRoot"
    }

    $sessionId = 'worker-' + $PID + '-' + [guid]::NewGuid().ToString('N')
    $state = [ordered]@{
        schema = $script:WorkerSessionSchema
        session_id = $sessionId
        task_id = [string]$task.task_id
        attempt_id = [string]$task.attempt_id
        process_id = [int]$PID
        progress_seq = 0
        progress_at = ([datetimeoffset]::Now.ToUniversalTime().ToString('o'))
    }

    $path = Join-Path $RuntimeRoot 'loop42-worker-session.json'
    Write-Loop42AtomicJson -Path $path -Value $state
    return [pscustomobject]$state
}

function Update-Loop42WorkerProgress {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$false)][string]$RuntimeRoot = 'C:\DeepThought'
    )

    $path = Join-Path $RuntimeRoot 'loop42-worker-session.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw 'worker session state is missing'
    }

    $state = (Get-Content -LiteralPath $path -Raw -Encoding UTF8) | ConvertFrom-Json
    if ($state.schema -ne $script:WorkerSessionSchema) { throw 'worker session schema mismatch' }
    if ([int]$state.process_id -ne $PID) { throw 'worker session belongs to a different process' }

    $next = [ordered]@{
        schema = $script:WorkerSessionSchema
        session_id = [string]$state.session_id
        task_id = [string]$state.task_id
        attempt_id = [string]$state.attempt_id
        process_id = [int]$PID
        progress_seq = ([int]$state.progress_seq + 1)
        progress_at = ([datetimeoffset]::Now.ToUniversalTime().ToString('o'))
    }
    Write-Loop42AtomicJson -Path $path -Value $next
    return [pscustomobject]$next
}

function Clear-Loop42WorkerSession {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$false)][string]$RuntimeRoot = 'C:\DeepThought'
    )

    $path = Join-Path $RuntimeRoot 'loop42-worker-session.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        return
    }

    $state = (Get-Content -LiteralPath $path -Raw -Encoding UTF8) | ConvertFrom-Json
    if ($state.schema -ne $script:WorkerSessionSchema) { throw 'worker session schema mismatch' }
    if ([int]$state.process_id -ne $PID) { throw 'refusing to clear another worker session' }
    Remove-Item -LiteralPath $path -Force
}

function Write-Loop42ProposalManifest {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$TaskManifestPath,
        [Parameter(Mandatory=$true)][string]$ContentPath,
        [Parameter(Mandatory=$true)][string]$WorkerSessionId,
        [Parameter(Mandatory=$true)][string]$PromptContractSha256,
        [Parameter(Mandatory=$true)][string]$ModelId,
        [Parameter(Mandatory=$false)][string]$ResultsRoot = 'G:\Meine Ablage\ChatGPT_Projekte\DeepThought_Away\10_Results'
    )

    $task = Read-Loop42TaskManifest -Path $TaskManifestPath
    if (-not (Test-Loop42Id $WorkerSessionId)) { throw 'invalid worker session id' }
    if (-not (Test-Loop42Fingerprint $PromptContractSha256)) {
        throw 'invalid prompt contract fingerprint'
    }
    if ([string]::IsNullOrWhiteSpace($ModelId) -or $ModelId.Length -gt 256) {
        throw 'invalid model id'
    }
    if (-not (Test-Path -LiteralPath $ResultsRoot -PathType Container)) {
        throw "Results root unavailable: $ResultsRoot"
    }
    if (-not (Test-Path -LiteralPath $ContentPath -PathType Leaf)) {
        throw "Proposal content unavailable: $ContentPath"
    }

    $contentItem = Get-Item -LiteralPath $ContentPath
    $resultsItem = Get-Item -LiteralPath $ResultsRoot
    if ($contentItem.Directory.FullName -ne $resultsItem.FullName) {
        throw 'proposal content must be a direct child of ResultsRoot'
    }

    $hash = (Get-FileHash -LiteralPath $ContentPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $proposal = [ordered]@{
        schema = $script:ProposalSchema
        task_id = [string]$task.task_id
        attempt_id = [string]$task.attempt_id
        source_revision = [string]$task.source_revision
        context_fingerprint = [string]$task.context_fingerprint
        observed_at = ([datetimeoffset]::Now.ToUniversalTime().ToString('o'))
        worker_session_id = $WorkerSessionId
        prompt_contract_sha256 = $PromptContractSha256
        model_id = $ModelId
        content_file = $contentItem.Name
        content_sha256 = $hash
    }

    $manifestName = '{0}__{1}.proposal.json' -f $task.task_id, $task.attempt_id
    $manifestPath = Join-Path $ResultsRoot $manifestName
    Write-Loop42AtomicJson -Path $manifestPath -Value $proposal
    return [pscustomobject]$proposal
}

Export-ModuleMember -Function @(
    'Start-Loop42WorkerSession',
    'Update-Loop42WorkerProgress',
    'Clear-Loop42WorkerSession',
    'Write-Loop42ProposalManifest'
)

param(
    [Parameter(Mandatory=$false)]
    [string]$DriveRoot = 'G:\Meine Ablage\ChatGPT_Projekte\DeepThought_Away',

    [Parameter(Mandatory=$false)]
    [string]$RuntimeRoot = 'C:\DeepThought',

    [Parameter(Mandatory=$false)]
    [string]$WorkerScriptPattern = 'DeepThought-Away\.ps1'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$HostSchema = 'loop42.drive-host-state.v1'
$WorkerSessionSchema = 'loop42.windows-worker-session.v1'
$Logs = Join-Path $DriveRoot '90_Logs'
$Target = Join-Path $Logs 'loop42-host-state.json'
$WorkerSessionFile = Join-Path $RuntimeRoot 'loop42-worker-session.json'
$OverheatFlag = Join-Path $RuntimeRoot 'STOPPED_OVERHEAT.flag'
$WatchdogFailFlag = Join-Path $RuntimeRoot 'WATCHDOG_FAILURE.flag'

function Test-Id([string]$Value) {
    return ($null -ne $Value -and $Value -match '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$')
}

function Read-WorkerSession([System.Diagnostics.Process[]]$WorkerProcesses) {
    if ($WorkerProcesses.Count -ne 1) {
        return [pscustomobject]@{
            Sessions = @()
            Unidentified = $WorkerProcesses.Count
            Error = if ($WorkerProcesses.Count -gt 1) { 'multiple_worker_processes' } else { $null }
        }
    }

    if (-not (Test-Path -LiteralPath $WorkerSessionFile -PathType Leaf)) {
        return [pscustomobject]@{
            Sessions = @()
            Unidentified = 1
            Error = 'worker_identity_missing'
        }
    }

    try {
        $raw = Get-Content -LiteralPath $WorkerSessionFile -Raw -Encoding UTF8
        $value = $raw | ConvertFrom-Json

        if ($value.schema -ne $WorkerSessionSchema) { throw 'worker session schema mismatch' }
        if (-not (Test-Id ([string]$value.session_id))) { throw 'invalid worker session_id' }
        if (-not (Test-Id ([string]$value.task_id))) { throw 'invalid task_id' }
        if (-not (Test-Id ([string]$value.attempt_id))) { throw 'invalid attempt_id' }

        $processId = [int]$value.process_id
        if ($processId -ne $WorkerProcesses[0].Id) { throw 'worker process_id mismatch' }

        $session = [ordered]@{
            session_id = [string]$value.session_id
            task_id = [string]$value.task_id
            attempt_id = [string]$value.attempt_id
        }

        if ($null -ne $value.progress_seq) {
            $progressSeq = [int]$value.progress_seq
            if ($progressSeq -lt 0) { throw 'negative progress_seq' }
            $session.progress_seq = $progressSeq
        }

        if ($null -ne $value.progress_at -and -not [string]::IsNullOrWhiteSpace([string]$value.progress_at)) {
            $progressAt = [datetimeoffset]::Parse([string]$value.progress_at)
            $session.progress_at = $progressAt.ToUniversalTime().ToString('o')
        }

        return [pscustomobject]@{
            Sessions = @([pscustomobject]$session)
            Unidentified = 0
            Error = $null
        }
    }
    catch {
        return [pscustomobject]@{
            Sessions = @()
            Unidentified = 1
            Error = 'worker_identity_invalid'
        }
    }
}

if (-not (Test-Path -LiteralPath $DriveRoot -PathType Container)) {
    throw "Drive root unavailable: $DriveRoot"
}
if (-not (Test-Path -LiteralPath $Logs -PathType Container)) {
    throw "Required Logs surface unavailable: $Logs"
}
if (-not (Test-Path -LiteralPath $RuntimeRoot -PathType Container)) {
    throw "Runtime root unavailable: $RuntimeRoot"
}

$os = Get-CimInstance Win32_OperatingSystem
$boot = [datetimeoffset]$os.LastBootUpTime
$hostSession = 'host-' + $boot.ToUniversalTime().ToString('yyyyMMddTHHmmssZ')

$workers = @(
    Get-CimInstance Win32_Process -ErrorAction Stop |
    Where-Object {
        $_.Name -match '^(powershell|pwsh)(\.exe)?$' -and
        $_.CommandLine -match $WorkerScriptPattern
    } |
    ForEach-Object { Get-Process -Id $_.ProcessId -ErrorAction Stop }
)

$workerEvidence = Read-WorkerSession $workers
$safetyStop = (Test-Path -LiteralPath $OverheatFlag -PathType Leaf) -or
              (Test-Path -LiteralPath $WatchdogFailFlag -PathType Leaf)

$payload = [ordered]@{
    schema = $HostSchema
    observed_at = ([datetimeoffset]::Now.ToUniversalTime().ToString('o'))
    session_id = $hostSession
    reachable = $true
    safety_stop = [bool]$safetyStop
    unidentified_worker_count = [int]$workerEvidence.Unidentified
    worker_sessions = @($workerEvidence.Sessions)
}

$json = $payload | ConvertTo-Json -Depth 8
$temp = Join-Path $Logs ('.loop42-host-state.{0}.{1}.tmp' -f $PID, [guid]::NewGuid().ToString('N'))

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($temp, $json + [Environment]::NewLine, $utf8NoBom)

    if (Test-Path -LiteralPath $Target -PathType Leaf) {
        [System.IO.File]::Replace($temp, $Target, $null)
    }
    else {
        [System.IO.File]::Move($temp, $Target)
    }
}
finally {
    if (Test-Path -LiteralPath $temp -PathType Leaf) {
        Remove-Item -LiteralPath $temp -Force
    }
}

[pscustomobject]@{
    host_state = $Target
    host_session_id = $hostSession
    worker_process_count = $workers.Count
    unidentified_worker_count = $workerEvidence.Unidentified
    worker_identity_error = $workerEvidence.Error
    safety_stop = [bool]$safetyStop
} | ConvertTo-Json -Depth 4

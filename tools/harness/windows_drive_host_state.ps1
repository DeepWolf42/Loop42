param(
    [Parameter(Mandatory=$false)]
    [string]$DriveRoot = 'G:\Meine Ablage\ChatGPT_Projekte\DeepThought_Away',

    [Parameter(Mandatory=$false)]
    [string]$RuntimeRoot = 'C:\DeepThought',

    [Parameter(Mandatory=$false)]
    [string]$WorkerScriptPattern = 'DeepThought-Away\.ps1',

    [Parameter(Mandatory=$false)]
    [string]$WatchdogScriptPattern = 'DeepThought-Watchdog\.ps1'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$HostSchema = 'loop42.drive-host-state.v1'
$WorkerSessionSchema = 'loop42.windows-worker-session.v1'
$Logs = Join-Path $DriveRoot '90_Logs'
$Target = Join-Path $Logs 'loop42-host-state.json'
$WorkerSessionFile = Join-Path $RuntimeRoot 'loop42-worker-session.json'
$RecoveryRoot = Join-Path $RuntimeRoot 'QueueRecovery'
$OverheatFlag = Join-Path $RuntimeRoot 'STOPPED_OVERHEAT.flag'
$WatchdogFailFlag = Join-Path $RuntimeRoot 'WATCHDOG_FAILURE.flag'
$WatchdogHeartbeat = Join-Path $RuntimeRoot 'WATCHDOG_HEARTBEAT.txt'

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

# Purely reads an existing legacy watchdog heartbeat; never starts or stops
# the watchdog or uses the heartbeat as proof of a physical safety guarantee.
function Read-Loop42WatchdogEvidence {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$HeartbeatPath,
        [Parameter(Mandatory=$true)][datetimeoffset]$ObservedAtUtc,
        [Parameter(Mandatory=$true)][int]$WatchdogProcessCount
    )

    if ($WatchdogProcessCount -ne 1) {
        return [pscustomobject]@{ Healthy = $false; Reason = 'watchdog_process_not_unique' }
    }
    if (-not (Test-Path -LiteralPath $HeartbeatPath -PathType Leaf)) {
        return [pscustomobject]@{ Healthy = $false; Reason = 'watchdog_heartbeat_missing' }
    }
    try {
        $item = Get-Item -LiteralPath $HeartbeatPath -ErrorAction Stop
        if ($item.Length -lt 1 -or $item.Length -gt 256) {
            throw 'watchdog heartbeat size invalid'
        }
        $line = (Get-Content -LiteralPath $HeartbeatPath -Raw -Encoding ASCII -ErrorAction Stop).Trim()
        $parts = $line -split '\|', 3
        if ($parts.Count -ne 3 -or $parts[1] -ne 'OK' -or $parts[2] -notmatch '^[0-9]{1,3}$') {
            throw 'watchdog heartbeat state invalid'
        }
        $at = [datetimeoffset]::ParseExact(
            $parts[0], 'o', [System.Globalization.CultureInfo]::InvariantCulture
        )
        $age = ($ObservedAtUtc.ToUniversalTime() - $at.ToUniversalTime()).TotalSeconds
        if ($age -lt 0 -or $age -gt 60) {
            throw 'watchdog heartbeat missing freshness'
        }
        if ([int]$parts[2] -ge 80) {
            throw 'watchdog reported high temperature'
        }
        return [pscustomobject]@{ Healthy = $true; Reason = 'fresh_watchdog_ok' }
    }
    catch {
        return [pscustomobject]@{ Healthy = $false; Reason = 'watchdog_heartbeat_invalid_or_unsafe' }
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
# An absent local recovery directory is UNKNOWN, not proof that no old work can replay.
if (-not (Test-Path -LiteralPath $RecoveryRoot -PathType Container)) {
    throw "Legacy recovery root unavailable: $RecoveryRoot"
}

$os = Get-CimInstance Win32_OperatingSystem
$boot = [datetimeoffset]$os.LastBootUpTime
$hostSession = 'host-' + $boot.ToUniversalTime().ToString('yyyyMMddTHHmmssZ')

# One authoritative process snapshot covers both the worker and the legacy
# supervisor. The latter can restore QueueRecovery backups without a DispatchPermit.
$processSnapshot = @(Get-CimInstance Win32_Process -ErrorAction Stop)
$workers = @(
    $processSnapshot |
    Where-Object {
        $_.Name -match '^(powershell|pwsh)(\.exe)?$' -and
        $_.CommandLine -match $WorkerScriptPattern
    } |
    ForEach-Object { Get-Process -Id $_.ProcessId -ErrorAction Stop }
)
$legacySupervisors = @(
    $processSnapshot |
    Where-Object {
        $_.Name -match '^(powershell|pwsh)(\.exe)?$' -and
        $_.CommandLine -match 'DeepThought-24x7\.ps1'
    }
)
$recoveryBackups = @(
    Get-ChildItem -LiteralPath $RecoveryRoot -File -Filter '*.jobbackup' -ErrorAction Stop
)
$watchdogs = @(
    $processSnapshot |
    Where-Object {
        $_.Name -match '^(powershell|pwsh)(\.exe)?$' -and
        $_.CommandLine -match $WatchdogScriptPattern
    }
)
$observedAtUtc = [datetimeoffset]::Now.ToUniversalTime()
$watchdogEvidence = Read-Loop42WatchdogEvidence `
    -HeartbeatPath $WatchdogHeartbeat `
    -ObservedAtUtc $observedAtUtc `
    -WatchdogProcessCount $watchdogs.Count

$workerEvidence = Read-WorkerSession $workers
# This is a dispatch-inhibiting gate, not a claim that overheating occurred.
$legacyRecoveryBlocked = ($legacySupervisors.Count -gt 0 -or $recoveryBackups.Count -gt 0)
$safetyStop = (Test-Path -LiteralPath $OverheatFlag -PathType Leaf) -or
              (Test-Path -LiteralPath $WatchdogFailFlag -PathType Leaf) -or
              $legacyRecoveryBlocked -or
              (-not $watchdogEvidence.Healthy)

$payload = [ordered]@{
    schema = $HostSchema
    observed_at = $observedAtUtc.ToString('o')
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
    legacy_supervisor_process_count = $legacySupervisors.Count
    legacy_recovery_backup_count = $recoveryBackups.Count
    legacy_recovery_blocks_dispatch = [bool]$legacyRecoveryBlocked
    watchdog_process_count = $watchdogs.Count
    watchdog_heartbeat_reason = $watchdogEvidence.Reason
    unidentified_worker_count = $workerEvidence.Unidentified
    worker_identity_error = $workerEvidence.Error
    safety_stop = [bool]$safetyStop
} | ConvertTo-Json -Depth 4

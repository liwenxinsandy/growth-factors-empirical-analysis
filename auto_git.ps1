# ============================================================
# auto_git.ps1 — 自动 Git 提交 + 推送 watcher
# 监听文件变动，停止编辑 5 分钟后自动 git add/commit/push
# ============================================================
param(
    [int]$QuietPeriodSeconds = 300
)

$ErrorActionPreference = "Continue"
$repo = "C:\Users\Lenovo\Documents\经济增长因素"
$logFile = Join-Path $repo "auto_git.log"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $Message" | Out-File -FilePath $logFile -Append -Encoding UTF8
    Write-Host "$ts  $Message"
}

Write-Log "=== auto-git started (quiet period: ${QuietPeriodSeconds}s) ==="

# 跨线程同步状态
$sync = [hashtable]::Synchronized(@{
    LastChange = Get-Date
    Running    = $true
    Committing = $false
})

# ---- FileSystemWatcher ----
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path                  = $repo
$watcher.IncludeSubdirectories = $true
$watcher.NotifyFilter          = [System.IO.NotifyFilters]::FileName -bor
                                 [System.IO.NotifyFilters]::LastWrite -bor
                                 [System.IO.NotifyFilters]::DirectoryName

$onChange = {
    if (-not $Event.MessageData.Committing) {
        $Event.MessageData.LastChange = Get-Date
    }
}

$createdEvent = Register-ObjectEvent $watcher "Created" -Action $onChange -MessageData $sync
$changedEvent = Register-ObjectEvent $watcher "Changed" -Action $onChange -MessageData $sync
$watcher.EnableRaisingEvents = $true

# ---- 主循环 ----
while ($sync.Running) {
    Start-Sleep -Seconds 30

    $elapsed = ((Get-Date) - $sync.LastChange).TotalSeconds
    if ($elapsed -lt $QuietPeriodSeconds) { continue }

    $sync.Committing = $true

    try {
        # 防止并发 git 操作
        if (Test-Path (Join-Path $repo ".git\index.lock")) {
            Write-Log "index.lock detected; waiting"
            $sync.Committing = $false
            continue
        }

        $status = git -C $repo status --porcelain 2>&1 | Out-String
        if ([string]::IsNullOrWhiteSpace($status.Trim())) {
            $sync.LastChange = Get-Date
            $sync.Committing = $false
            continue
        }

        # 提取变更文件名，生成 commit message
        $lines = git -C $repo status --porcelain 2>&1
        $names = $lines | ForEach-Object {
            if ($_ -match '^\s*[MADRCU?]{2}\s+"?(.+?)"?$') {
                Split-Path $matches[1] -Leaf
            } elseif ($_ -match '^\s*[MADRCU?]{2}\s+(.+)$') {
                Split-Path $matches[1] -Leaf
            }
        } | Select-Object -Unique

        $summary = ($names -join ", ")
        if ($summary.Length -gt 150) {
            $summary = $summary.Substring(0, 150) + "..."
        }

        $commitMsg = "auto: $(Get-Date -Format 'yyyy-MM-dd HH:mm') - $summary"

        git -C $repo add -A 2>&1 | Out-Null
        $commitOutput = git -C $repo commit -m $commitMsg 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Log "Committed: $summary"

            $pushOutput = git -C $repo push 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Push OK"
            } else {
                Write-Log "Push failed (will retry): $pushOutput"
            }
        } elseif ($commitOutput -match "nothing to commit") {
            Write-Log "Nothing to commit"
        } else {
            Write-Log "Commit issue: $commitOutput"
        }
    }
    catch {
        Write-Log "Error: $_"
    }
    finally {
        $sync.LastChange = Get-Date
        $sync.Committing = $false
    }
}

# ---- 清理 ----
$createdEvent | Unregister-Event -ErrorAction SilentlyContinue
$changedEvent | Unregister-Event -ErrorAction SilentlyContinue
$watcher.Dispose()
Write-Log "=== auto-git stopped ==="

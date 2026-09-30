# Sao lưu cơ sở dữ liệu SQLite an toàn.
# Dùng lệnh ".backup" của sqlite3 thay vì Copy-Item, tránh sao chép tệp đang được ghi.
#
# Cách dùng:  powershell -ExecutionPolicy Bypass -File scripts\backup-db.ps1
param(
    [string]$DatabasePath = "backend\app\learning_assistant.db",
    [int]$Keep = 14
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
$source = Join-Path $projectRoot $DatabasePath

if (-not (Test-Path $source)) {
    Write-Host "Không tìm thấy cơ sở dữ liệu: $source" -ForegroundColor Red
    exit 1
}

$python = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Không tìm thấy python trong môi trường ảo: $python" -ForegroundColor Red
    exit 1
}

$backupDir = Join-Path $projectRoot "backend\backups"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $backupDir "learning_assistant-$stamp.db"

$code = @"
import sqlite3
source = sqlite3.connect(r'$source')
target = sqlite3.connect(r'$target')
with target:
    source.backup(target)
target.close()
source.close()
"@
$code | & $python -

if ($LASTEXITCODE -ne 0) {
    Write-Host "Sao lưu thất bại." -ForegroundColor Red
    exit 1
}

# Chỉ giữ lại $Keep bản sao lưu gần nhất.
Get-ChildItem $backupDir -Filter "learning_assistant-*.db" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $Keep |
    Remove-Item -Force

Write-Host "Đã sao lưu: $target" -ForegroundColor Green

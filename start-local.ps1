param(
    [switch]$SkipFrontend
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'

if (-not (Test-Path $ollama)) {
    throw "Không tìm thấy Ollama tại $ollama"
}

$env:OLLAMA_MODELS = 'D:\TroLiThongMinh\ollama-models'
if (-not (Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    Start-Sleep -Seconds 4
}

$backend = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like '*uvicorn*app.main*' } |
    Select-Object -First 1
if (-not $backend) {
    $python = Join-Path $root 'backend\.venv\Scripts\python.exe'
    $env:OLLAMA_HOST = 'http://127.0.0.1:11434'
    $env:OLLAMA_MODEL = 'qwen2.5:3b'
    Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' `
        -WorkingDirectory (Join-Path $root 'backend') -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

if (-not $SkipFrontend) {
    $frontend = Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" |
        Where-Object { $_.CommandLine -like '*TroLiThongMinh*frontend*' -and $_.CommandLine -like '*vite*' } |
        Select-Object -First 1
    if (-not $frontend) {
        $npm = 'C:\Program Files\nodejs\npm.cmd'
        Start-Process -FilePath $npm -ArgumentList 'run', 'dev', '--', '--host', '127.0.0.1' `
            -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden
        Start-Sleep -Seconds 3
    }
}

Write-Host 'Mindora local da san sang:' -ForegroundColor Green
Write-Host '  Frontend: http://127.0.0.1:5173'
Write-Host '  Backend:  http://127.0.0.1:8000/docs'
Write-Host '  Model:    qwen2.5:3b (local, free)'

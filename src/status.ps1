# 投资决策支持系统 - 状态检查脚本（Windows PowerShell）
$srcDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $srcDir "logs\server.pid"

if (Test-Path $pidFile) {
    $pid = Get-Content $pidFile
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "服务状态: 运行中 (PID $pid)"
    } else {
        Write-Host "服务状态: 未运行"
        exit 1
    }
} else {
    Write-Host "服务状态: 未运行"
    exit 1
}

$venvPython = Join-Path $srcDir ".venv\Scripts\python.exe"
try {
    $port = & $venvPython -c "import json;print(json.load(open('config/app.json'))['server']['port'])"
} catch { $port = 8620 }
if (-not $port) { $port = 8620 }

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:${port}/api/health" -TimeoutSec 3
    Write-Host "健康检查: OK"
    Write-Host "访问地址: http://127.0.0.1:${port}"
} catch {
    Write-Host "健康检查: 失败（端口 $port 无响应）"
    exit 1
}

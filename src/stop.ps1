# 投资决策支持系统 - 停止脚本（Windows PowerShell）
$srcDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $srcDir "logs\server.pid"

if (-not (Test-Path $pidFile)) {
    Write-Host "[stop] 未找到 PID 文件，服务可能未运行"
    exit 0
}

$pid = Get-Content $pidFile
$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Host "[stop] 进程 $pid 不存在，清理 PID 文件"
    Remove-Item $pidFile -Force
    exit 0
}

Write-Host "[stop] 停止服务 (PID $pid)..."
Stop-Process -Id $pid -Force
Remove-Item $pidFile -Force
Write-Host "[stop] 服务已停止"

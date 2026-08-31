# 投资决策支持系统 - 启动脚本（Windows PowerShell）
$ErrorActionPreference = "Stop"

$srcDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $srcDir

$logDir = Join-Path $srcDir "logs"
$pidFile = Join-Path $logDir "server.pid"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# 1. Python 虚拟环境与依赖
$venvPython = Join-Path $srcDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[start] 创建 Python 虚拟环境..."
    python -m venv (Join-Path $srcDir ".venv")
}
& $venvPython -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[start] 安装依赖..."
    & $venvPython -m pip install --quiet -r (Join-Path $srcDir "requirements.txt")
}

# 2. 首次部署初始化 data/password.txt
$passwordFile = Join-Path $srcDir "data\password.txt"
if (-not (Test-Path $passwordFile)) {
    Write-Host "[start] 初始化 data/password.txt..."
    New-Item -ItemType Directory -Force -Path (Join-Path $srcDir "data") | Out-Null
    @'
# 格式: username:password:role  (role 取值: admin | user)
# admin 默认拥有所有页面权限；user 的可见页面由管理员在权限管理页配置。
# 修改本文件后，新用户在下次登录时会自动同步到数据库。
admin:admin123:admin
'@ | Set-Content -Path $passwordFile -Encoding UTF8
}

# 3. 若已运行则先停止
if (Test-Path $pidFile) {
    $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Host "[start] 服务已在运行 (PID $oldPid)，先停止..."
        & (Join-Path $srcDir "stop.ps1")
        Start-Sleep -Seconds 1
    }
}

# 4. 后台启动
Write-Host "[start] 启动服务..."
$proc = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "app.backend.main" `
    -WorkingDirectory $srcDir `
    -RedirectStandardOutput (Join-Path $logDir "startup.log") `
    -RedirectStandardError (Join-Path $logDir "startup.err.log") `
    -WindowStyle Hidden -PassThru
Set-Content -Path $pidFile -Value $proc.Id

# 5. 健康检查
try {
    $port = (& $venvPython -c "import json;print(json.load(open('config/app.json'))['server']['port'])") 2>$null
} catch { $port = 32080 }
if (-not $port) { $port = 32080 }

for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:${port}/api/health" -TimeoutSec 2
        Write-Host "[start] 服务启动成功: http://127.0.0.1:${port} (PID $($proc.Id))"
        exit 0
    } catch {
        if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
            Write-Host "[start] 启动失败，请查看 logs\startup.log"
            exit 1
        }
    }
}
Write-Host "[start] 服务进程已启动，但健康检查未通过"
exit 1

#!/usr/bin/env bash
# 投资决策支持系统 - 启动脚本（Linux/macOS）
set -e

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SRC_DIR"

PY="python3"
VENV="$SRC_DIR/.venv"
LOG_DIR="$SRC_DIR/logs"
PID_FILE="$LOG_DIR/server.pid"

mkdir -p "$LOG_DIR"

# 1. Python 虚拟环境与依赖
if [ ! -x "$VENV/bin/python" ]; then
    echo "[start] 创建 Python 虚拟环境..."
    "$PY" -m venv "$VENV"
fi
if ! "$VENV/bin/python" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
    echo "[start] 安装依赖..."
    "$VENV/bin/pip" install --quiet -r "$SRC_DIR/requirements.txt"
fi

# 2. 首次部署初始化 data 目录与 password.txt
if [ ! -f "$SRC_DIR/data/password.txt" ]; then
    echo "[start] 初始化 data/password.txt..."
    mkdir -p "$SRC_DIR/data"
    printf '# 格式: username:password:role  (role 取值: admin | user)\n# admin 默认拥有所有页面权限；user 的可见页面由管理员在权限管理页配置。\n# 修改本文件后，新用户在下次登录时会自动同步到数据库。\nadmin:admin123:admin\n' > "$SRC_DIR/data/password.txt"
fi

# 3. 若已运行则先停止
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "[start] 服务已在运行 (PID $(cat "$PID_FILE"))，先停止..."
    bash "$SRC_DIR/stop.sh" || true
    sleep 1
fi

# 4. 后台启动
echo "[start] 启动服务..."
cd "$SRC_DIR"
nohup "$VENV/bin/python" -m app.backend.main >> "$LOG_DIR/startup.log" 2>&1 &
echo $! > "$PID_FILE"

# 5. 健康检查
PORT=$("$VENV/bin/python" -c "import json;print(json.load(open('config/app.json'))['server']['port'])" 2>/dev/null || echo 8620)
for i in $(seq 1 15); do
    sleep 1
    if curl -sf "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
        echo "[start] 服务启动成功: http://127.0.0.1:${PORT} (PID $(cat "$PID_FILE"))"
        exit 0
    fi
    if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "[start] 启动失败，请查看 $LOG_DIR/startup.log"
        tail -20 "$LOG_DIR/startup.log" || true
        exit 1
    fi
done
echo "[start] 服务进程已启动，但健康检查未通过，请查看 $LOG_DIR/app.log"
exit 1

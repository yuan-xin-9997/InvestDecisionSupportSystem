#!/usr/bin/env bash
# 投资决策支持系统 - 状态检查脚本（Linux/macOS）
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SRC_DIR/logs/server.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    PID=$(cat "$PID_FILE")
    echo "服务状态: 运行中 (PID $PID)"
else
    echo "服务状态: 未运行"
    exit 1
fi

PORT=$("$SRC_DIR/.venv/bin/python" -c "import json;print(json.load(open('$SRC_DIR/config/app.json'))['server']['port'])" 2>/dev/null || echo 32080)
HEALTH=$(curl -sf "http://127.0.0.1:${PORT}/api/health" 2>/dev/null || true)
if [ -n "$HEALTH" ]; then
    echo "健康检查: OK ($HEALTH)"
    echo "访问地址: http://127.0.0.1:${PORT}"
else
    echo "健康检查: 失败（端口 ${PORT} 无响应）"
    exit 1
fi

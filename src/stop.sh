#!/usr/bin/env bash
# 投资决策支持系统 - 停止脚本（Linux/macOS）
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SRC_DIR/logs/server.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "[stop] 未找到 PID 文件，服务可能未运行"
    exit 0
fi

PID=$(cat "$PID_FILE")
if ! kill -0 "$PID" 2>/dev/null; then
    echo "[stop] 进程 $PID 不存在，清理 PID 文件"
    rm -f "$PID_FILE"
    exit 0
fi

echo "[stop] 停止服务 (PID $PID)..."
kill "$PID" 2>/dev/null || true
for i in $(seq 1 10); do
    sleep 1
    kill -0 "$PID" 2>/dev/null || break
done
if kill -0 "$PID" 2>/dev/null; then
    echo "[stop] 强制终止..."
    kill -9 "$PID" 2>/dev/null || true
fi
rm -f "$PID_FILE"
echo "[stop] 服务已停止"

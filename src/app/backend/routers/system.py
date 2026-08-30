"""系统信息与配置展示接口。"""

import platform
import subprocess
import time
from datetime import datetime

from fastapi import APIRouter, Depends

from ..core.config import get_config
from ..core.deps import require_admin
from ..core.timeutil import CST, now_cst, now_str, format_cst
from ..models import User

router = APIRouter(prefix="/api/system", tags=["system"])

_started_at = now_str()
_started_ts = time.time()


def get_version() -> str:
    """版本号：GitHub 提交数量（git rev-list --count），不可用时回退 0。"""
    try:
        cfg = get_config()
        out = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=cfg.base_dir, capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip().isdigit():
            return out.stdout.strip()
    except Exception:
        pass
    return "0"


@router.get("/info")
def system_info():
    cfg = get_config()
    return {
        "app_name": cfg.get("app.name"),
        "version": get_version(),
        "started_at": _started_at,
        "uptime_seconds": int(time.time() - _started_ts),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "server_time": now_str(),
        "timezone": "UTC+8 (北京时间)",
    }


@router.get("/config")
def system_config(_: User = Depends(require_admin)):
    """展示脱敏后的主配置与运行路径信息（仅管理员）。"""
    cfg = get_config()
    return {
        "config": cfg.masked_dict(),
        "paths": {
            "base_dir": str(cfg.base_dir),
            "config_file": str(cfg.config_path),
            "sqlite_file": str(cfg.sqlite_path),
            "logs_dir": str(cfg.logs_dir),
            "password_file": str(cfg.password_file),
        },
    }

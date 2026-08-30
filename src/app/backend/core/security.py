"""认证与安全：password.txt 解析、密码校验、token 生成。"""

import hmac
import secrets
from pathlib import Path

from .config import get_config


def parse_password_file(path: Path | None = None) -> list[dict[str, str]]:
    """解析 password.txt，返回 [{"username","password","role"}]。

    格式: username:password:role；# 开头为注释，空行与非法行忽略。
    """
    cfg = get_config()
    file_path = path or cfg.password_file
    users: list[dict[str, str]] = []
    if not file_path.exists():
        return users
    for raw in file_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        username, password, role = (p.strip() for p in parts)
        if not username or not password:
            continue
        if role not in ("admin", "user"):
            role = "user"
        users.append({"username": username, "password": password, "role": role})
    return users


def verify_password(plain: str, expected: str) -> bool:
    return hmac.compare_digest(plain.encode("utf-8"), expected.encode("utf-8"))


def generate_token() -> str:
    return secrets.token_hex(32)


def hash_for_display(value: str) -> str:
    """用于界面展示的脱敏。"""
    if not value:
        return ""
    return value[0] + "***" if len(value) > 1 else "***"

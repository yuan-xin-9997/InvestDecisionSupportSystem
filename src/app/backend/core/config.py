"""应用配置加载。

所有环境相关信息均保存在 config/app.json 中，代码中禁止硬编码 IP、端口、
用户名、密码、绝对路径。支持通过环境变量 IDSS_HOME 覆盖工程根目录（用于测试）。
"""

import copy
import json
import os
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {"password"}

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {"name": "投资决策支持系统"},
    "server": {"host": "0.0.0.0", "port": 8620},
    "database": {"sqlite_file": "data/app.sqlite3"},
    "postgres": {
        "host": "127.0.0.1",
        "port": 15432,
        "user": "vnpy",
        "password": "",
        "dbname": "vnpy",
        "connect_timeout": 10,
        "query_limit_max": 5000,
    },
    "auth": {"token_expire_days": 7},
    "log": {"level": "INFO", "dir": "logs", "retention_days": 30},
    "upload": {
        "journal_dir": "data/journal",
        "max_image_mb": 10,
        "max_long_edge": 2000,
    },
}


def get_base_dir() -> Path:
    """工程根目录（src 目录）。"""
    env_home = os.environ.get("IDSS_HOME")
    if env_home:
        return Path(env_home).resolve()
    # core/config.py -> backend -> app -> src
    return Path(__file__).resolve().parents[3]


class AppConfig:
    """包装 app.json 的配置对象，支持属性式访问与默认值合并。"""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else get_base_dir()
        self.config_path = self.base_dir / "config" / "app.json"
        self._data: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        merged = copy.deepcopy(DEFAULT_CONFIG)
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                file_data = json.load(f)
            _deep_merge(merged, file_data)
        self._data = merged

    def section(self, name: str) -> dict[str, Any]:
        return self._data.get(name, {})

    def get(self, dotted_key: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    # ---- 常用路径 ----
    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def sqlite_path(self) -> Path:
        rel = self.get("database.sqlite_file", "data/app.sqlite3")
        p = Path(rel)
        return p if p.is_absolute() else self.base_dir / p

    @property
    def logs_dir(self) -> Path:
        rel = self.get("log.dir", "logs")
        p = Path(rel)
        return p if p.is_absolute() else self.base_dir / p

    @property
    def password_file(self) -> Path:
        return self.data_dir / "password.txt"

    @property
    def journal_dir(self) -> Path:
        rel = self.get("upload.journal_dir", "data/journal")
        p = Path(rel)
        return p if p.is_absolute() else self.base_dir / p

    def masked_dict(self) -> dict[str, Any]:
        """返回脱敏后的配置副本（密码字段打码），用于接口展示。"""
        def mask(node: Any) -> Any:
            if isinstance(node, dict):
                return {
                    k: ("******" if k in SENSITIVE_KEYS and v else mask(v))
                    for k, v in node.items()
                }
            if isinstance(node, list):
                return [mask(i) for i in node]
            return node
        return mask(copy.deepcopy(self._data))


def _deep_merge(target: dict, source: dict) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


_config: AppConfig | None = None


def get_config() -> AppConfig:
    """全局配置单例（测试中可通过 set_config 替换）。"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def set_config(config: AppConfig | None) -> None:
    global _config
    _config = config

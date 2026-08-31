"""pytest 公共夹具：为每个测试会话构建独立的 IDSS_HOME 环境（临时目录）。"""

import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1]  # src 目录


class TestEnv:
    """独立测试环境：临时目录 + app.json + password.txt。"""

    def __init__(self, root: Path):
        self.root = root
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data").mkdir(parents=True, exist_ok=True)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "config" / "app.json").write_text(json.dumps({
            "server": {"host": "127.0.0.1", "port": 32080},
            "database": {"sqlite_file": "data/app.sqlite3"},
            "postgres": {"host": "127.0.0.1", "port": 1, "user": "x", "password": "x",
                         "dbname": "x", "connect_timeout": 1, "query_limit_max": 100},
            "auth": {"token_expire_days": 7},
            "log": {"level": "WARNING", "dir": "logs", "retention_days": 30},
            "upload": {"journal_dir": "data/journal", "max_image_mb": 5, "max_long_edge": 2000},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "data" / "password.txt").write_text(
            "# 测试用户\nadmin:admin123:admin\ntester:testpw:user\n", encoding="utf-8"
        )


@pytest.fixture(scope="session")
def test_env(tmp_path_factory):
    """构建环境并导入应用（每测试会话一次）。"""
    root = tmp_path_factory.mktemp("idss_home")
    env = TestEnv(root)
    old_home = os.environ.get("IDSS_HOME")
    os.environ["IDSS_HOME"] = str(root)
    sys.path.insert(0, str(SRC_DIR))

    # 全新导入，保证全局单例基于测试配置
    for mod_name in list(sys.modules):
        if mod_name == "app" or mod_name.startswith("app."):
            del sys.modules[mod_name]

    from app.backend.main import app  # noqa: F401 导入即建表
    env.app = app
    yield env

    if old_home is not None:
        os.environ["IDSS_HOME"] = old_home
    else:
        os.environ.pop("IDSS_HOME", None)
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture(scope="session")
def client(test_env):
    """TestClient 与登录后的公共 token。"""
    from fastapi.testclient import TestClient
    with TestClient(test_env.app) as c:
        resp = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200, resp.text
        token = resp.json()["token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


@pytest.fixture(scope="session")
def anon_client(test_env):
    """不带登录态的 TestClient（用于 401 冒烟验证）。"""
    from fastapi.testclient import TestClient
    with TestClient(test_env.app) as c:
        yield c


def make_png(width: int = 100, height: int = 80, color=(200, 30, 30)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()

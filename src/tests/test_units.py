"""核心模块单元测试：配置、时间、安全、行情查询参数。"""

import json

from app.backend.core.config import AppConfig
from app.backend.core.security import parse_password_file, verify_password
from app.backend.core.timeutil import now_cst, now_str, to_cst, format_cst
from app.backend.db import postgres as pg

from conftest import TestEnv


def test_parse_password_file(test_env):
    users = parse_password_file(test_env.root / "data" / "password.txt")
    by_name = {u["username"]: u for u in users}
    assert by_name["admin"]["role"] == "admin"
    assert by_name["admin"]["password"] == "admin123"
    assert by_name["tester"]["role"] == "user"


def test_parse_password_file_missing(tmp_path):
    data_dir = tmp_path / "no_data"
    data_dir.mkdir()
    assert parse_password_file(data_dir / "password.txt") == []


def test_verify_password():
    assert verify_password("abc123", "abc123")
    assert not verify_password("abc123", "abc124")
    assert not verify_password("", "x")


def test_masked_config_hides_password(tmp_path):
    env = TestEnv(tmp_path / "mask")
    cfg = AppConfig(tmp_path / "mask")
    masked = cfg.masked_dict()
    assert masked["postgres"]["password"] == "******"
    assert masked["postgres"]["host"] == "127.0.0.1"


def test_time_beijing_normalization():
    from datetime import datetime, timezone, timedelta
    # naive 时间视为北京时间，不做偏移
    naive = datetime(2026, 8, 30, 12, 0, 0)
    assert format_cst(naive) == "2026-08-30 12:00:00"
    # UTC 时间需转换为北京时间 +8
    utc = datetime(2026, 8, 30, 4, 0, 0, tzinfo=timezone.utc)
    assert format_cst(utc) == "2026-08-30 12:00:00"
    # 东九区转北京时间 -1
    jst = datetime(2026, 8, 30, 13, 0, 0, tzinfo=timezone(timedelta(hours=9)))
    assert format_cst(jst) == "2026-08-30 12:00:00"


def test_now_str_format():
    s = now_str()
    assert len(s) == 19 and s[4] == "-" and s[10] == " "
    assert now_cst().utcoffset().total_seconds() == 8 * 3600


def test_fetch_kline_param_validation():
    import pytest
    with pytest.raises(ValueError):
        pg.fetch_kline("600519", "SSE", "5m")  # 非法周期
    with pytest.raises(ValueError):
        pg.fetch_kline("", "SSE", "d")  # 空 symbol


def test_to_cst_keeps_beijing():
    dt = to_cst(now_cst())
    assert dt.utcoffset().total_seconds() == 8 * 3600

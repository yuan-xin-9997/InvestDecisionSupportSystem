"""行情数据库（PostgreSQL / vnpy）访问层。

连接信息全部来自 config/app.json 的 postgres 段。
"""

import logging
from contextlib import contextmanager
from typing import Any

from psycopg2.pool import SimpleConnectionPool
from sqlalchemy.engine import make_url

from ..core.config import get_config

logger = logging.getLogger("app.market")

_pool: SimpleConnectionPool | None = None


class MarketDBError(RuntimeError):
    """行情库访问失败。"""


def _pool_kwargs(cfg=None) -> dict[str, Any]:
    cfg = cfg or get_config().section("postgres")
    return dict(
        host=cfg.get("host"),
        port=int(cfg.get("port", 5432)),
        user=cfg.get("user"),
        password=cfg.get("password"),
        dbname=cfg.get("dbname"),
        connect_timeout=int(cfg.get("connect_timeout", 10)),
    )


def get_pool() -> SimpleConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        kwargs = _pool_kwargs()
        try:
            _pool = SimpleConnectionPool(minconn=1, maxconn=5, **kwargs)
        except Exception as exc:  # 网络不通、认证失败等
            logger.warning("连接行情数据库失败: %s", exc)
            raise MarketDBError(f"无法连接行情数据库: {exc}") from exc
    return _pool


def reset_pool() -> None:
    global _pool
    if _pool is not None:
        try:
            _pool.closeall()
        except Exception:
            pass
    _pool = None


@contextmanager
def get_connection():
    try:
        pool = get_pool()
    except MarketDBError:
        raise
    try:
        conn = pool.getconn()
    except MarketDBError:
        raise
    except Exception as exc:
        raise MarketDBError(f"获取行情数据库连接失败: {exc}") from exc
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            pool.putconn(conn)
        except Exception:
            pass


def test_connection() -> dict[str, Any]:
    """探活并返回核心表行数。"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.execute("SELECT COUNT(*) FROM dbbardata")
            bar_count = cur.fetchone()[0]
    return {"ok": True, "bar_count": bar_count}


def fetch_overview() -> dict[str, list[dict[str, Any]]]:
    """读取 K 线与 Tick 的数据概览（品种、周期、条数、起止时间）。"""
    bar_sql = (
        'SELECT symbol, exchange, "interval", count, start, "end" '
        "FROM dbbaroverview ORDER BY symbol, exchange, \"interval\""
    )
    tick_sql = (
        "SELECT symbol, exchange, count, start, \"end\" "
        "FROM dbtickoverview ORDER BY symbol, exchange"
    )
    result: dict[str, list[dict[str, Any]]] = {"bars": [], "ticks": []}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(bar_sql)
            for symbol, exchange, interval, count, start, end in cur.fetchall():
                result["bars"].append({
                    "symbol": symbol,
                    "exchange": exchange,
                    "interval": interval,
                    "count": count,
                    "start": start.strftime("%Y-%m-%d %H:%M:%S") if start else None,
                    "end": end.strftime("%Y-%m-%d %H:%M:%S") if end else None,
                })
            try:
                cur.execute(tick_sql)
                for symbol, exchange, count, start, end in cur.fetchall():
                    result["ticks"].append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "count": count,
                        "start": start.strftime("%Y-%m-%d %H:%M:%S") if start else None,
                        "end": end.strftime("%Y-%m-%d %H:%M:%S") if end else None,
                    })
            except Exception:
                conn.rollback()
                result["ticks"] = []
    return result


VALID_INTERVALS = {"d", "1m", "1h"}


def fetch_kline(
    symbol: str,
    exchange: str,
    interval: str,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """按品种/交易所/周期查询 K 线，返回时间正序的 bar 列表。

    datetime 在 vnpy 库中即为北京时间，原样格式化输出。
    """
    cfg = get_config()
    max_limit = int(cfg.get("postgres.query_limit_max", 5000))
    limit = max(1, min(int(limit or 800), max_limit))

    if interval not in VALID_INTERVALS:
        raise ValueError(f"不支持的周期: {interval}")
    if not symbol or not exchange:
        raise ValueError("symbol 和 exchange 不能为空")

    sql = (
        "SELECT datetime, open_price, high_price, low_price, close_price, "
        "volume, turnover, open_interest FROM dbbardata "
        "WHERE symbol = %s AND exchange = %s AND \"interval\" = %s"
    )
    params: list[Any] = [symbol, exchange, interval]
    if start:
        sql += " AND datetime >= %s"
        params.append(start)
    if end:
        sql += " AND datetime <= %s"
        params.append(f"{end} 23:59:59" if len(end) == 10 else end)
    sql += ' ORDER BY datetime DESC LIMIT %s'
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    bars = [
        {
            "datetime": r[0].strftime("%Y-%m-%d %H:%M:%S"),
            "open": r[1],
            "high": r[2],
            "low": r[3],
            "close": r[4],
            "volume": r[5],
            "turnover": r[6],
            "open_interest": r[7],
        }
        for r in rows
    ]
    bars.reverse()  # 时间正序，便于绘图
    return bars

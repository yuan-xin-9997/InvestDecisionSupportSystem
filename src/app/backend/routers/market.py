"""行情展示接口：连接 PostgreSQL 行情库（vnpy 格式）。"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.deps import require_page
from ..db import postgres as pg
from ..models import User

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview")
def overview(_: User = Depends(require_page("market"))):
    """K 线 / Tick 数据概览（品种、周期、记录数、起止时间）。"""
    try:
        return pg.fetch_overview()
    except pg.MarketDBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/kline")
def kline(
    symbol: str = Query(..., description="品种代码，如 600519 / au9999"),
    exchange: str = Query(..., description="交易所，如 SSE / SHFE / SGE"),
    interval: str = Query("d", description="周期: d | 1h | 1m"),
    start: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(800, ge=1, le=5000, description="最多返回根数"),
    _: User = Depends(require_page("market")),
):
    """K 线数据（时间正序），用于 ECharts 绘图或表格展示。"""
    try:
        bars = pg.fetch_kline(symbol, exchange, interval, start, end, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except pg.MarketDBError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {
        "symbol": symbol,
        "exchange": exchange,
        "interval": interval,
        "count": len(bars),
        "bars": bars,
    }

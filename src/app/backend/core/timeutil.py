"""时间工具：统一输出北京时间。"""

from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
FMT = "%Y-%m-%d %H:%M:%S"
FMT_DATE = "%Y-%m-%d"


def now_cst() -> datetime:
    return datetime.now(CST)


def now_str() -> str:
    return format_cst(now_cst())


def today_str() -> str:
    return now_cst().strftime(FMT_DATE)


def to_cst(dt: datetime) -> datetime:
    """把任意 datetime 归一化为北京时间。

    naive 时间视为已经是北京时间（行情数据库中存储的即为北京时间）；
    带 tzinfo 的时间则转换为北京时间。
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=CST)
    return dt.astimezone(CST)


def format_cst(dt: datetime) -> str:
    return to_cst(dt).strftime(FMT)


def format_date_cst(dt: datetime) -> str:
    return to_cst(dt).strftime(FMT_DATE)

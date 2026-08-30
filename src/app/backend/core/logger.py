"""日志模块：按天切割，当天为 app.log，历史为 app.YYYY-MM-DD.log。"""

import logging
from logging.handlers import TimedRotatingFileHandler

from .config import get_config

_configured = False


class _DayNamer:
    """把默认的 app.log.2026-08-30 重命名为 app.2026-08-30.log。"""

    def __call__(self, default_name: str) -> str:
        # default_name 形如 .../app.log.2026-08-29
        if ".log." in default_name:
            stem, _, date_part = default_name.rpartition(".log.")
            return f"{stem}.{date_part}.log"
        return default_name


def setup_logging() -> logging.Logger:
    global _configured
    cfg = get_config()
    logs_dir = cfg.logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, str(cfg.get("log.level", "INFO")).upper(), logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    file_handler = TimedRotatingFileHandler(
        logs_dir / "app.log", when="midnight", backupCount=int(cfg.get("log.retention_days", 30)),
        encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.namer = _DayNamer()
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    _configured = True
    return logging.getLogger("app")

"""本地 SQLite 数据库引擎与会话管理。"""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ..models import Base
from ..core.config import AppConfig, get_config

_engine = None
_SessionLocal: sessionmaker | None = None


def get_engine(cfg: AppConfig | None = None):
    global _engine, _SessionLocal
    if _engine is None:
        cfg = cfg or get_config()
        sqlite_path: Path = cfg.sqlite_path
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{sqlite_path}",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """关闭并清空全局引擎（测试环境切换目录时使用）。"""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_session_factory():
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db():
    """FastAPI 依赖：请求级会话。"""
    factory = get_session_factory()
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


def init_db(cfg: AppConfig) -> None:
    """建表并写入内置任务。"""
    get_engine(cfg)
    assert _engine is not None
    Base.metadata.create_all(_engine)

    from ..models import Task

    builtin_tasks = [
        Task(task_id="postgres_check", name="行情数据库连通性检查",
             description="连接 PostgreSQL 行情库执行探活查询，并汇报核心表行数"),
        Task(task_id="log_cleanup", name="历史日志清理",
             description="删除超过保留期的按天切割历史日志文件"),
        Task(task_id="journal_orphan_scan", name="日志附件一致性检查",
             description="检查投资日志图片文件与数据库记录是否一致，报告孤儿文件"),
    ]
    with Session(bind=_engine) as db:
        for task in builtin_tasks:
            exists = db.get(Task, task.task_id)
            if exists is None:
                db.add(task)
        db.commit()

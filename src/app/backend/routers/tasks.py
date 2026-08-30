"""任务中心接口：任务列表、立即执行、运行历史。"""

import glob
import time
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.config import get_config
from ..core.deps import require_page
from ..core.timeutil import now_str
from ..db.sqlite import get_db
from ..db import postgres as pg
from ..models import Task, TaskRun, User

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _latest_runs(db: Session) -> dict[str, TaskRun]:
    runs: dict[str, TaskRun] = {}
    rows = (
        db.query(TaskRun)
        .order_by(TaskRun.started_at.desc(), TaskRun.id.desc())
        .limit(200)
        .all()
    )
    for r in rows:
        if r.task_id not in runs:
            runs[r.task_id] = r
    return runs


@router.get("")
def list_tasks(_: User = Depends(require_page("tasks")), db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.task_id).all()
    latest = _latest_runs(db)
    items = []
    for t in tasks:
        run = latest.get(t.task_id)
        items.append({
            "task_id": t.task_id,
            "name": t.name,
            "description": t.description,
            "enabled": bool(t.enabled),
            "last_run": {
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "status": run.status,
                "message": run.message,
            } if run else None,
        })
    return {"items": items}


@router.post("/{task_id}/run")
def run_task(task_id: str, _: User = Depends(require_page("tasks")), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    handlers = {
        "postgres_check": _run_postgres_check,
        "log_cleanup": _run_log_cleanup,
        "journal_orphan_scan": _run_journal_orphan_scan,
    }
    handler = handlers.get(task_id)
    if handler is None:
        raise HTTPException(status_code=400, detail="该任务没有可执行处理器")

    run = TaskRun(task_id=task_id, started_at=now_str(), status="running", message="")
    db.add(run)
    db.commit()

    start = time.time()
    try:
        message = handler()
        run.status = "success"
        run.message = message
    except Exception as exc:
        run.status = "failed"
        run.message = f"{type(exc).__name__}: {exc}"
    run.finished_at = now_str()
    run.message = f"{run.message}（耗时 {time.time() - start:.2f} 秒）"
    db.commit()
    db.refresh(run)
    return {"run": _run_dict(run)}


@router.get("/{task_id}/runs")
def task_runs(task_id: str, limit: int = 20, _: User = Depends(require_page("tasks")),
              db: Session = Depends(get_db)):
    if db.get(Task, task_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    limit = max(1, min(limit, 100))
    rows = (
        db.query(TaskRun)
        .filter(TaskRun.task_id == task_id)
        .order_by(TaskRun.started_at.desc(), TaskRun.id.desc())
        .limit(limit)
        .all()
    )
    return {"items": [_run_dict(r) for r in rows], "total": len(rows)}


def _run_dict(r: TaskRun) -> dict:
    return {
        "id": r.id,
        "task_id": r.task_id,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "status": r.status,
        "message": r.message,
    }


# ---- 内置任务实现 ----

def _run_postgres_check() -> str:
    info = pg.test_connection()
    return f"行情数据库连接正常，K线记录 {info['bar_count']} 条"


def _run_log_cleanup() -> str:
    cfg = get_config()
    retention = int(cfg.get("log.retention_days", 30))
    logs_dir = cfg.logs_dir
    cutoff = datetime.now() - timedelta(days=retention)
    removed = 0
    for f in glob.glob(str(logs_dir / "app.*.log")):
        path = Path(f)
        try:
            date_str = path.name.removeprefix("app.").removesuffix(".log")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        if file_date < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return f"清理完成，删除 {removed} 个超过 {retention} 天的历史日志"


def _run_journal_orphan_scan() -> str:
    from sqlalchemy import select

    from ..db.sqlite import get_session_factory
    from ..models import JournalImage

    cfg = get_config()
    factory = get_session_factory()
    with Session(bind=factory.kw["bind"]) as db:  # type: ignore[attr-defined]
        known = {row.rel_path for row in db.execute(select(JournalImage.rel_path)).all()}

    journal_dir = cfg.journal_dir
    on_disk = {
        str(p.relative_to(cfg.base_dir)) for p in journal_dir.rglob("*") if p.is_file()
    }
    orphans = sorted(on_disk - known)
    missing = sorted(known - on_disk)
    return (
        f"磁盘文件 {len(on_disk)} 个，数据库记录 {len(known)} 条；"
        f"孤儿文件 {len(orphans)} 个，缺失文件 {len(missing)} 个"
    )

"""投资日志接口：图文上传、时间线查询、编辑删除。"""

import json
import re
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.config import get_config
from ..core.deps import get_current_user, require_page
from ..core.timeutil import now_str, today_str
from ..db.sqlite import get_db
from ..models import Journal, JournalImage, User

router = APIRouter(prefix="/api/journal", tags=["journal"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
ALLOWED_SUFFIX = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
MAX_IMAGES_PER_JOURNAL = 20


def _save_image(upload: UploadFile, user: str) -> dict:
    """校验并保存一张图片，返回 journal_images 行字段。"""
    cfg = get_config()
    max_bytes = int(cfg.get("upload.max_image_mb", 10)) * 1024 * 1024
    long_edge = int(cfg.get("upload.max_long_edge", 2000))

    suffix = Path(upload.filename or "").suffix.lower()
    if suffix and suffix not in ALLOWED_SUFFIX:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {suffix}")

    data = upload.file.read(max_bytes + 1)
    if not data:
        raise HTTPException(status_code=400, detail=f"图片为空: {upload.filename}")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"图片超过大小限制 {cfg.get('upload.max_image_mb', 10)}MB: {upload.filename}",
        )

    try:
        img = Image.open(BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"无法识别的图片文件: {upload.filename}") from exc

    # 过大图片等比压缩到 max_long_edge 以内
    w, h = img.size
    if max(w, h) > long_edge:
        scale = long_edge / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)))
    if img.mode in ("P", "RGBA") and suffix not in (".png", ".gif", ".webp"):
        img = img.convert("RGB")

    day = today_str().split("-")
    rel_dir = Path(cfg.get("upload.journal_dir", "data/journal")) / day[0] / day[1] / day[2]
    abs_dir = cfg.base_dir / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)

    if not suffix:
        suffix = ".png" if (img.format == "PNG") else ".jpg"
    save_name = f"{uuid.uuid4().hex}{suffix}"
    abs_path = abs_dir / save_name
    img.save(abs_path)

    return {
        "original_name": upload.filename or save_name,
        "rel_path": str(rel_dir / save_name).replace("\\", "/"),
        "size": abs_path.stat().st_size,
    }


def _journal_dict(db: Session, j: Journal) -> dict:
    images = (
        db.query(JournalImage)
        .filter(JournalImage.journal_id == j.id)
        .order_by(JournalImage.id)
        .all()
    )
    return {
        "id": j.id,
        "content": j.content,
        "trade_date": j.trade_date,
        "created_by": j.created_by,
        "created_at": j.created_at,
        "updated_at": j.updated_at,
        "images": [
            {
                "id": img.id,
                "original_name": img.original_name,
                "size": img.size,
                "url": f"/api/journal/images/{img.id}",
                "rel_path": img.rel_path,
            }
            for img in images
        ],
    }


class JournalCreate(BaseModel):
    content: str = ""
    trade_date: str | None = None


@router.post("")
async def create_journal(
    content: str = Form(default=""),
    trade_date: str | None = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新建投资日志（multipart：正文 + 可选多张图片）。"""
    if not content.strip() and not files:
        raise HTTPException(status_code=400, detail="正文与图片不能同时为空")
    if len(files) > MAX_IMAGES_PER_JOURNAL:
        raise HTTPException(status_code=400, detail=f"单篇日志最多上传 {MAX_IMAGES_PER_JOURNAL} 张图片")

    if trade_date:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", trade_date):
            raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
    else:
        trade_date = today_str()

    journal = Journal(content=content.strip(), trade_date=trade_date, created_by=user.username)
    db.add(journal)
    db.commit()
    db.refresh(journal)

    saved = []
    try:
        for f in files:
            fields = _save_image(f, user.username)
            row = JournalImage(journal_id=journal.id, **fields)
            db.add(row)
            saved.append(row)
        db.commit()
    except Exception:
        # 保存失败的图片回滚，不留脏文件
        for row in saved:
            (get_config().base_dir / row.rel_path).unlink(missing_ok=True)
        raise

    db.refresh(journal)
    return {"journal": _journal_dict(db, journal)}


@router.get("")
def list_journals(
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 10,
    _: User = Depends(require_page("journal")),
    db: Session = Depends(get_db),
):
    """按时间线倒序查询日志：支持日期范围与关键词筛选。"""
    page = max(1, page)
    page_size = max(1, min(page_size, 50))

    q = db.query(Journal)
    if start_date:
        q = q.filter(Journal.trade_date >= start_date)
    if end_date:
        q = q.filter(Journal.trade_date <= end_date)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(Journal.content.like(like))

    total = q.count()
    rows = (
        q.order_by(Journal.trade_date.desc(), Journal.created_at.desc(), Journal.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"total": total, "page": page, "page_size": page_size,
            "items": [_journal_dict(db, j) for j in rows]}


@router.get("/images/{image_id}")
def get_image(image_id: int, _: User = Depends(require_page("journal")), db: Session = Depends(get_db)):
    img = db.get(JournalImage, image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="图片不存在")
    abs_path = get_config().base_dir / img.rel_path
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="图片文件已丢失")
    return FileResponse(abs_path)


@router.get("/{journal_id}")
def get_journal(journal_id: int, _: User = Depends(require_page("journal")), db: Session = Depends(get_db)):
    j = db.get(Journal, journal_id)
    if j is None:
        raise HTTPException(status_code=404, detail="日志不存在")
    return {"journal": _journal_dict(db, j)}


class JournalUpdate(BaseModel):
    content: str | None = None
    trade_date: str | None = None


@router.put("/{journal_id}")
def update_journal(
    journal_id: int,
    req: JournalUpdate,
    _: User = Depends(require_page("journal")),
    db: Session = Depends(get_db),
):
    j = db.get(Journal, journal_id)
    if j is None:
        raise HTTPException(status_code=404, detail="日志不存在")
    if req.content is not None:
        j.content = req.content.strip()
    if req.trade_date is not None:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", req.trade_date):
            raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
        j.trade_date = req.trade_date
    j.updated_at = now_str()
    db.commit()
    db.refresh(j)
    return {"journal": _journal_dict(db, j)}


@router.post("/{journal_id}/images")
async def append_images(
    journal_id: int,
    files: list[UploadFile] = File(...),
    _: User = Depends(require_page("journal")),
    db: Session = Depends(get_db),
):
    j = db.get(Journal, journal_id)
    if j is None:
        raise HTTPException(status_code=404, detail="日志不存在")
    existing = db.query(func.count(JournalImage.id)).filter(JournalImage.journal_id == journal_id).scalar() or 0
    if existing + len(files) > MAX_IMAGES_PER_JOURNAL:
        raise HTTPException(status_code=400, detail=f"单篇日志最多 {MAX_IMAGES_PER_JOURNAL} 张图片")
    for f in files:
        fields = _save_image(f, j.created_by)
        db.add(JournalImage(journal_id=journal_id, **fields))
    j.updated_at = now_str()
    db.commit()
    db.refresh(j)
    return {"journal": _journal_dict(db, j)}


@router.delete("/{journal_id}/images/{image_id}")
def delete_image(
    journal_id: int, image_id: int,
    _: User = Depends(require_page("journal")),
    db: Session = Depends(get_db),
):
    img = db.get(JournalImage, image_id)
    if img is None or img.journal_id != journal_id:
        raise HTTPException(status_code=404, detail="图片不存在")
    (get_config().base_dir / img.rel_path).unlink(missing_ok=True)
    db.delete(img)
    db.commit()
    return {"ok": True}


@router.delete("/{journal_id}")
def delete_journal(
    journal_id: int,
    _: User = Depends(require_page("journal")),
    db: Session = Depends(get_db),
):
    j = db.get(Journal, journal_id)
    if j is None:
        raise HTTPException(status_code=404, detail="日志不存在")
    for img in db.query(JournalImage).filter(JournalImage.journal_id == journal_id).all():
        (get_config().base_dir / img.rel_path).unlink(missing_ok=True)
        db.delete(img)
    db.delete(j)
    db.commit()
    return {"ok": True}

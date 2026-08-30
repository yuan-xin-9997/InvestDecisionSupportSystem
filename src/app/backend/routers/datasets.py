"""数据管理接口：宏观/微观等跟踪数据集及其记录的增删改查、CSV 导入导出。"""

import csv
import io
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.deps import require_page
from ..core.timeutil import now_str
from ..db.sqlite import get_db
from ..models import Dataset, DatasetRecord, User

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

VALID_CATEGORIES = ["宏观", "微观", "其他"]


def _check_date(date: str) -> str:
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"日期格式应为 YYYY-MM-DD: {date}")
    return date


def _dataset_dict(db: Session, d: Dataset) -> dict:
    cnt = (
        db.query(func.count(DatasetRecord.id))
        .filter(DatasetRecord.dataset_id == d.id)
        .scalar() or 0
    )
    latest = (
        db.query(DatasetRecord)
        .filter(DatasetRecord.dataset_id == d.id)
        .order_by(DatasetRecord.date.desc())
        .first()
    )
    return {
        "id": d.id,
        "name": d.name,
        "category": d.category,
        "unit": d.unit,
        "description": d.description,
        "record_count": cnt,
        "latest_date": latest.date if latest else None,
        "latest_value": latest.value if latest else None,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }


class DatasetCreate(BaseModel):
    name: str
    category: str = "宏观"
    unit: str = ""
    description: str = ""


@router.get("")
def list_datasets(
    category: str | None = None,
    _: User = Depends(require_page("datasets")),
    db: Session = Depends(get_db),
):
    q = db.query(Dataset)
    if category:
        q = q.filter(Dataset.category == category)
    rows = q.order_by(Dataset.category, Dataset.name).all()
    return {"items": [_dataset_dict(db, d) for d in rows], "total": len(rows)}


@router.post("")
def create_dataset(
    req: DatasetCreate,
    _: User = Depends(require_page("datasets")),
    db: Session = Depends(get_db),
):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="数据集名称不能为空")
    if req.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"分类只能是 {'/'.join(VALID_CATEGORIES)}")
    if db.query(Dataset).filter(Dataset.name == name).first():
        raise HTTPException(status_code=400, detail="同名数据集已存在")
    d = Dataset(name=name, category=req.category, unit=req.unit.strip(), description=req.description)
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"dataset": _dataset_dict(db, d)}


class DatasetUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    unit: str | None = None
    description: str | None = None


@router.put("/{dataset_id}")
def update_dataset(
    dataset_id: int,
    req: DatasetUpdate,
    _: User = Depends(require_page("datasets")),
    db: Session = Depends(get_db),
):
    d = db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    if req.name is not None:
        name = req.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="数据集名称不能为空")
        dup = db.query(Dataset).filter(Dataset.name == name, Dataset.id != dataset_id).first()
        if dup:
            raise HTTPException(status_code=400, detail="同名数据集已存在")
        d.name = name
    if req.category is not None:
        if req.category not in VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"分类只能是 {'/'.join(VALID_CATEGORIES)}")
        d.category = req.category
    if req.unit is not None:
        d.unit = req.unit.strip()
    if req.description is not None:
        d.description = req.description
    db.commit()
    db.refresh(d)
    return {"dataset": _dataset_dict(db, d)}


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    _: User = Depends(require_page("datasets")),
    db: Session = Depends(get_db),
):
    d = db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id).delete()
    db.delete(d)
    db.commit()
    return {"ok": True}


@router.get("/{dataset_id}/records")
def list_records(
    dataset_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    page_size: int = 20,
    order: str = "desc",
    _: User = Depends(require_page("datasets")),
    db: Session = Depends(get_db),
):
    if db.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    q = db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id)
    if start_date:
        q = q.filter(DatasetRecord.date >= start_date)
    if end_date:
        q = q.filter(DatasetRecord.date <= end_date)
    total = q.count()
    order_col = DatasetRecord.date.desc() if order != "asc" else DatasetRecord.date.asc()
    rows = q.order_by(order_col).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_record_dict(r) for r in rows],
    }


def _record_dict(r: DatasetRecord) -> dict:
    return {
        "id": r.id,
        "date": r.date,
        "value": r.value,
        "note": r.note,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


class RecordUpsert(BaseModel):
    date: str
    value: float | None = None
    note: str = ""


@router.post("/{dataset_id}/records")
def upsert_record(
    dataset_id: int,
    req: RecordUpsert,
    _: User = Depends(require_page("datasets")),
    db: Session = Depends(get_db),
):
    if db.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    _check_date(req.date)
    row = (
        db.query(DatasetRecord)
        .filter(DatasetRecord.dataset_id == dataset_id, DatasetRecord.date == req.date)
        .first()
    )
    if row is None:
        row = DatasetRecord(dataset_id=dataset_id, date=req.date, value=req.value, note=req.note)
        db.add(row)
    else:
        row.value = req.value
        row.note = req.note
    db.commit()
    db.refresh(row)
    return {"record": _record_dict(row)}


@router.delete("/records/{record_id}")
def delete_record(
    record_id: int,
    _: User = Depends(require_page("datasets")),
    db: Session = Depends(get_db),
):
    row = db.get(DatasetRecord, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/{dataset_id}/import")
async def import_csv(
    dataset_id: int,
    file: UploadFile = File(...),
    _: User = Depends(require_page("datasets")),
    db: Session = Depends(get_db),
):
    """CSV 批量导入（表头: date,value,note），同日期覆盖更新。"""
    d = db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(status_code=404, detail="数据集不存在")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gbk")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="CSV 文件编码需为 UTF-8 或 GBK")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "date" not in [f.strip().lower() for f in reader.fieldnames]:
        raise HTTPException(status_code=400, detail="CSV 需包含表头: date,value,note")

    inserted, updated, skipped = 0, 0, 0
    for i, row in enumerate(reader, start=2):
        norm = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        date = norm.get("date", "")
        if not date:
            skipped += 1
            continue
        try:
            date = _check_date(date)
        except HTTPException:
            skipped += 1
            continue
        value: float | None
        raw_value = norm.get("value", "")
        if raw_value == "":
            value = None
        else:
            try:
                value = float(raw_value)
            except ValueError:
                skipped += 1
                continue
        existing = (
            db.query(DatasetRecord)
            .filter(DatasetRecord.dataset_id == dataset_id, DatasetRecord.date == date)
            .first()
        )
        if existing:
            existing.value = value
            existing.note = norm.get("note", "")
            updated += 1
        else:
            db.add(DatasetRecord(
                dataset_id=dataset_id, date=date, value=value, note=norm.get("note", ""),
            ))
            inserted += 1
    db.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


@router.get("/{dataset_id}/export")
def export_csv(
    dataset_id: int,
    _: User = Depends(require_page("datasets")),
    db: Session = Depends(get_db),
):
    d = db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    rows = (
        db.query(DatasetRecord)
        .filter(DatasetRecord.dataset_id == dataset_id)
        .order_by(DatasetRecord.date)
        .all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "value", "note"])
    for r in rows:
        writer.writerow([r.date, "" if r.value is None else r.value, r.note])
    buf.seek(0)
    filename = f"{d.name}_{datetime.now().strftime('%Y%m%d')}.csv"
    quoted = quote(filename)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )

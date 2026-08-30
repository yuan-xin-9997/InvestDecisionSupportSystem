"""权限管理接口（仅管理员）：维护可登录用户与页面权限。

用户名单来自 data/password.txt（登录时自动同步进库），本模块负责维护
角色与可见页面，不修改密码文件本身。
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.deps import require_admin
from ..core.security import parse_password_file
from ..core.timeutil import now_str
from ..db.sqlite import get_db
from ..models import User

router = APIRouter(prefix="/api/users", tags=["users"])

PAGE_KEYS = ["dashboard", "market", "journal", "datasets", "tasks", "users", "config"]


class UserUpdate(BaseModel):
    role: str | None = None
    pages: list[str] | None = None


@router.get("/pages")
def list_pages(user: User = Depends(require_admin)):
    """返回可分配的页面清单。"""
    return {"pages": PAGE_KEYS}


@router.get("")
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """用户列表 = 数据库中的用户 ∪ password.txt 中的用户（标注是否已同步）。"""
    file_users = parse_password_file()
    db_users = {u.username: u for u in db.query(User).all()}

    items = []
    for u in db_users.values():
        d = u.to_dict()
        if u.role == "admin":
            d["pages"] = list(PAGE_KEYS)  # admin 恒拥有全部页面，仅作展示
        d["in_password_file"] = any(f["username"] == u.username for f in file_users)
        items.append(d)
    seen = set(d["username"] for d in items)
    for f in file_users:
        if f["username"] not in seen:
            items.append({
                "id": None,
                "username": f["username"],
                "role": f["role"],
                "pages": [] if f["role"] != "admin" else PAGE_KEYS,
                "created_at": "",
                "updated_at": "",
                "last_login_at": "",
                "in_password_file": True,
                "not_synced": True,
            })
    items.sort(key=lambda x: (x["role"] != "admin", x["username"]))
    return {"items": items, "total": len(items)}


@router.put("/{username}")
def update_user(
    username: str,
    req: UserUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在（尚未登录同步过）")

    if req.role is not None:
        if req.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="角色只能是 admin 或 user")
        if user.role == "admin" and req.role == "user":
            admins = [u for u in db.query(User).all() if u.role == "admin"]
            if len(admins) <= 1:
                raise HTTPException(status_code=400, detail="系统至少需要保留一名管理员")
        user.role = req.role

    if req.pages is not None:
        bad = [p for p in req.pages if p not in PAGE_KEYS]
        if bad:
            raise HTTPException(status_code=400, detail=f"未知页面: {','.join(bad)}")
        user.pages = json.dumps(req.pages)
        if user.role == "admin":
            user.pages = json.dumps(PAGE_KEYS)  # admin 恒为全部页面

    db.commit()
    db.refresh(user)
    return {"user": user.to_dict()}


@router.post("/sync")
def sync_from_file(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """手动触发：把 password.txt 中的用户同步进数据库。"""
    created, updated = [], []
    for f in parse_password_file():
        user = db.query(User).filter(User.username == f["username"]).first()
        if user is None:
            pages = PAGE_KEYS if f["role"] == "admin" else ["dashboard"]
            db.add(User(
                username=f["username"], role=f["role"], pages=json.dumps(pages),
                created_at=now_str(),
            ))
            created.append(f["username"])
        elif user.role != f["role"]:
            user.role = f["role"]
            updated.append(f["username"])
    db.commit()
    return {"created": created, "updated": updated}

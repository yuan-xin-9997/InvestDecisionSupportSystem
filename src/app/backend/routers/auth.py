"""登录认证接口。"""

import json

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.config import get_config
from ..core.deps import get_current_user
from ..core.security import generate_token, parse_password_file, verify_password
from ..core.timeutil import now_str
from ..db.sqlite import get_db
from ..models import Token, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

PAGE_KEYS = ["dashboard", "market", "journal", "datasets", "tasks", "users", "config"]


class LoginRequest(BaseModel):
    username: str
    password: str


def sync_user_to_db(db: Session, username: str, role: str) -> User:
    """登录时把 password.txt 中的用户同步进数据库（新用户插入，角色变化更新）。"""
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        default_pages = [] if role == "admin" else ["dashboard"]
        user = User(username=username, role=role, pages=json.dumps(default_pages))
        db.add(user)
    elif user.role != role:
        user.role = role
    db.commit()
    db.refresh(user)
    return user


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    file_users = {u["username"]: u for u in parse_password_file()}
    match = file_users.get(req.username)
    if match is None or not verify_password(req.password, match["password"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user = sync_user_to_db(db, match["username"], match["role"])

    # 清理过期 token 与该用户旧 token（保持单会话）
    now = now_str()
    db.query(Token).filter(Token.expires_at < now).delete()
    db.query(Token).filter(Token.username == user.username).delete()

    expire_days = int(get_config().get("auth.token_expire_days", 7))
    expires_at = _shift_days(now, expire_days)
    token = generate_token()
    db.add(Token(token=token, username=user.username, created_at=now, expires_at=expires_at))
    user.last_login_at = now
    db.commit()

    return {"token": token, "expires_at": expires_at, "user": user.to_dict()}


@router.post("/logout")
def logout(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        db.query(Token).filter(Token.token == token).delete()
        db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user": user.to_dict()}


def _shift_days(ts: str, days: int) -> str:
    from datetime import datetime, timedelta

    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") + timedelta(days=days)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

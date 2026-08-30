"""FastAPI 依赖：登录态校验与权限控制。"""

import json

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..db.sqlite import get_db
from ..models import Token, User
from ..core.timeutil import now_str

ALL_PAGES = ["dashboard", "market", "journal", "datasets", "tasks", "users", "config"]


def _unauthorized(msg: str = "未登录或登录已过期") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)


def _forbidden(msg: str = "没有访问该页面的权限") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized()
    token = authorization.removeprefix("Bearer ").strip()
    row = db.get(Token, token)
    if row is None:
        raise _unauthorized()
    if row.expires_at and row.expires_at < now_str():
        db.delete(row)
        db.commit()
        raise _unauthorized("登录已过期，请重新登录")
    user = db.query(User).filter(User.username == row.username).first()
    if user is None:
        raise _unauthorized("用户不存在，请重新登录")
    return user


def require_page(page_key: str):
    """页面级权限依赖：admin 全部可访问，user 需 pages 中包含 page_key。"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role == "admin":
            return user
        pages = json.loads(user.pages or "[]")
        if page_key not in pages:
            raise _forbidden()
        return user

    return checker


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise _forbidden("该操作仅管理员可执行")
    return user

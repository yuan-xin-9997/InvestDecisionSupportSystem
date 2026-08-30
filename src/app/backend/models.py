"""SQLAlchemy ORM 模型（本地 SQLite 库）。

时间字段统一使用字符串存储，内容为北京时间 "YYYY-MM-DD HH:MM:SS"。
"""

from sqlalchemy import Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .core.timeutil import now_str

ALL_PAGES = ["dashboard", "market", "journal", "datasets", "tasks", "users", "config"]


class Base(DeclarativeBase):
    pass


class User(Base):
    """可登录用户（信息与 password.txt 同步，权限由本表维护）。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16), default="user")
    pages: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[str] = mapped_column(String(19), default=now_str)
    updated_at: Mapped[str] = mapped_column(String(19), default=now_str, onupdate=now_str)
    last_login_at: Mapped[str] = mapped_column(String(19), default="")

    def to_dict(self) -> dict:
        import json

        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "pages": json.loads(self.pages or "[]"),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login_at": self.last_login_at,
        }


class Token(Base):
    """登录会话 token。"""

    __tablename__ = "tokens"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[str] = mapped_column(String(19), default=now_str)
    expires_at: Mapped[str] = mapped_column(String(19))


class Journal(Base):
    """投资日志。"""

    __tablename__ = "journals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, default="")
    trade_date: Mapped[str] = mapped_column(String(10), index=True)
    created_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[str] = mapped_column(String(19), default=now_str)
    updated_at: Mapped[str] = mapped_column(String(19), default=now_str, onupdate=now_str)


class JournalImage(Base):
    """投资日志附件图片。"""

    __tablename__ = "journal_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journal_id: Mapped[int] = mapped_column(Integer, index=True)
    original_name: Mapped[str] = mapped_column(String(255), default="")
    rel_path: Mapped[str] = mapped_column(String(255))  # 相对工程根目录的存储路径
    size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(19), default=now_str)


class Dataset(Base):
    """跟踪数据集（宏观、微观或其他自定义跟踪指标）。"""

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    category: Mapped[str] = mapped_column(String(32), default="宏观", index=True)
    unit: Mapped[str] = mapped_column(String(32), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(19), default=now_str)
    updated_at: Mapped[str] = mapped_column(String(19), default=now_str, onupdate=now_str)


class DatasetRecord(Base):
    """数据集记录：同一数据集同一天只保留一条（导入时覆盖更新）。"""

    __tablename__ = "dataset_records"
    __table_args__ = (UniqueConstraint("dataset_id", "date", name="uq_dataset_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(Integer, index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    value: Mapped[float] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(19), default=now_str)
    updated_at: Mapped[str] = mapped_column(String(19), default=now_str, onupdate=now_str)


class Task(Base):
    """任务定义。"""

    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(19), default=now_str)


class TaskRun(Base):
    """任务运行历史与日志。"""

    __tablename__ = "task_runs"
    __table_args__ = (Index("ix_task_runs_task_started", "task_id", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[str] = mapped_column(String(19))
    finished_at: Mapped[str] = mapped_column(String(19), default="")
    status: Mapped[str] = mapped_column(String(16), default="running")  # running/success/failed
    message: Mapped[str] = mapped_column(Text, default="")

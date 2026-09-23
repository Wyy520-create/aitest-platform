"""平台数据模型：用户 / 配置化用例 / 执行记录 / 用例结果。"""
from datetime import datetime

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    """平台用户（演示环境只有一个管理员，结构留好以后扩展）。"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))


class ConfigCase(Base):
    """配置化用例：不写代码、以 JSON 描述的接口用例。

    source: manual=人工创建 / ai=LLM 生成
    status: draft=待评审 / reviewed=已采纳 / rejected=已驳回
    request_json: {"method","path","headers","body","auth": bool}
    expect_json:  {"status_code", "json_contains": {...局部匹配}}
    """
    __tablename__ = "config_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    module: Mapped[str] = mapped_column(String(32), default="general")
    source: Mapped[str] = mapped_column(String(16), default="manual")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    request_json: Mapped[str] = mapped_column(Text)
    expect_json: Mapped[str] = mapped_column(Text, default="{}")
    review_note: Mapped[str] = mapped_column(Text, default="")
    # 统一用 Python 端本地时间默认值（SQLite 的 func.now() 是 UTC，会与
    # runner.py 里 finished_at 的 datetime.now() 差 8 小时）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Execution(Base):
    """一次执行（跑 pytest 套件或跑配置化用例）。"""
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    trigger: Mapped[str] = mapped_column(String(16), default="manual")   # manual/ci
    exec_type: Mapped[str] = mapped_column(String(16), default="suite")  # suite/config
    status: Mapped[str] = mapped_column(String(16), default="running")   # running/passed/failed/error
    total: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    bug_found: Mapped[int] = mapped_column(Integer, default=0)            # 命中的 bug_detection 数
    duration: Mapped[float] = mapped_column(Float, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ExecutionResult(Base):
    """单条用例结果。"""
    __tablename__ = "execution_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("executions.id"), index=True)
    case_name: Mapped[str] = mapped_column(String(256))
    outcome: Mapped[str] = mapped_column(String(16))       # passed/failed/error
    duration: Mapped[float] = mapped_column(Float, default=0)
    message: Mapped[str] = mapped_column(Text, default="")  # 失败摘要
    is_bug_detection: Mapped[int] = mapped_column(Integer, default=0)

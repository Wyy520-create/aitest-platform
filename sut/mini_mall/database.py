"""数据库连接层：引擎、会话工厂、Base 基类。

三个角色记清楚（面试可能问 SQLAlchemy 核心组件）：
- engine   引擎：管理"程序 <-> 数据库"的底层连接池
- Session  会话：一次"工作对话"，事务的载体（begin -> 干活 -> commit）
- Base     所有 ORM 类的爹，它帮翻译官记账"哪些类对应哪些表"
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import DATABASE_URL

# SQLite 的一个特殊设定：它默认不允许跨线程使用同一个连接，
# 而 FastAPI 处理请求是多线程的，所以要关掉这个检查。
# （MySQL 等服务器型数据库没有这个问题，这个参数就不需要了）
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# session 工厂：每个请求从工厂里"领"一个全新会话，用完归还
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型类的基类。"""
    pass


def get_db():
    """FastAPI 依赖：给每个请求发一个数据库会话，请求结束自动关闭。

    用 yield 是 FastAPI 的"依赖注入"写法：
    yield 之前的代码 = 请求进来时执行（开会话）
    yield 之后的代码 = 请求结束后执行（关会话，无论成功还是报错）
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

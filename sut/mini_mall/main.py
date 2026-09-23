"""mini_mall 被测系统主入口。

启动方式（在 sut/ 目录下）：
    uvicorn mini_mall.main:app --reload --port 8000

启动后：
- 接口地址:   http://localhost:8000/api/...
- 交互式文档: http://localhost:8000/docs   <- FastAPI 白送的，测试平台 AI 模块直接拿它当输入
"""
from fastapi import FastAPI

from .database import Base, engine, SessionLocal
from .routers import auth, products, cart, orders
from . import models


def create_tables():
    """按 models.py 的定义自动建表（表已存在则跳过）。

    开发期用它"零配置起库"；生产环境应该用 Alembic 迁移工具管理表结构变更，
    那是 M3 之后的话题。
    """
    # models 已在文件顶部导入，Base.metadata 因此认识所有表
    Base.metadata.create_all(bind=engine)


def seed_products():
    """库是空的就播种 6 件商品，方便一启动就有数据可测。

    注意价格是精心挑的：
    - 0.1  / 19.9：二进制浮点数无法精确表示 -> 喂给 BUG-03 的精度陷阱
    - 价格跨度大：方便后续性能测试造数据分布
    """
    db = SessionLocal()
    try:
        if db.query(models.Product).count() > 0:
            return
        products_data = [
            ("机械键盘 87 键", "青轴，白光", 199.0, 50, "digital"),
            ("鼠标无线静音", "2.4G 连接", 89.5, 100, "digital"),
            ("贴纸包 0.1 元", "浮点精度测试专用商品", 0.1, 999, "trinket"),
            ("马克杯", "留形科技周边", 19.9, 200, "trinket"),
            ("显示器支架", "单臂铝合金", 259.0, 30, "digital"),
            ("USB-C 数据线", "100W 快充 2 米", 29.9, 500, "digital"),
        ]
        for name, desc, price, stock, cat in products_data:
            db.add(models.Product(
                name=name, description=desc, price=price, stock=stock, category=cat,
            ))
        db.commit()
    finally:
        db.close()


app = FastAPI(
    title="mini-mall 被测系统",
    description="aitest-platform 的测试靶子：一个带注入缺陷的迷你电商",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup():
    create_tables()
    seed_products()


# 注册路由：prefix 已在各 router 里声明（/api/auth、/api/products...）
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)


@app.get("/")
def root():
    """根路径健康检查——之后测试引擎的第一个冒烟用例就打它。"""
    return {"app": "mini-mall", "status": "ok"}

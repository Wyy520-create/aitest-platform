"""测试平台后端主入口。

启动: uvicorn app.main:app --port 8100
默认管理员: admin / admin123 (环境变量 PLATFORM_ADMIN_PASSWORD 可改)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, SessionLocal
from . import models  # noqa: F401 确保建表时模型已注册
from .security import ensure_admin, router as auth_router
from .routers import executions, cases, ai, dashboard, qa

app = FastAPI(
    title="aitest-platform 测试平台",
    description="接口自动化测试平台：用例管理 / 执行调度 / 报告 / AI 用例生成",
    version="0.1.0",
)

# 本地开发时前端走 5500 端口（静态服务器），需要跨域；
# compose 环境里 nginx 网关同源反代，此配置无副作用。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_admin(db)
    finally:
        db.close()


app.include_router(auth_router)
app.include_router(executions.router)
app.include_router(cases.router)
app.include_router(ai.router)
app.include_router(dashboard.router)
app.include_router(qa.router)


@app.get("/api/health")
def health():
    return {"app": "aitest-platform", "status": "ok"}

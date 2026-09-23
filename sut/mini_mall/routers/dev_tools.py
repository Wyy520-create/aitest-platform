"""测试数据准备接口（仅 TEST_MODE=1 时注册）。

为什么需要它：测试引擎有时要把前置条件摆到指定状态（如把秒杀商品
库存重置为 5）。本地开发时引擎直连 SQLite 即可；但容器化/CI 环境里
引擎与被测系统不在同一台机器上，直连数据库不可行，只能走 HTTP。

业界通行做法：QA 环境预置一个"数据工厂"接口，生产环境绝不注册
（不暴露攻击面）。这就是环境差异化配置的意义。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product

router = APIRouter(prefix="/api/dev", tags=["测试工具(仅TEST_MODE)"])


class ResetStockIn(BaseModel):
    product_id: int
    stock: int = Field(ge=0)


@router.post("/reset-stock")
def reset_stock(payload: ResetStockIn, db: Session = Depends(get_db)):
    """把指定商品库存重置为指定值（测试前置条件准备）。"""
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(404, "商品不存在")
    product.stock = payload.stock
    db.commit()
    return {"product_id": payload.product_id, "stock": payload.stock}

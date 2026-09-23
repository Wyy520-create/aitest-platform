"""商品模块：列表 / 搜索 / 详情。

接口清单：
    GET /api/products          分页列表，支持 ?keyword= ?category= ?page= ?size=
    GET /api/products/{id}     商品详情
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product
from ..schemas import ProductOut, ProductPageOut

router = APIRouter(prefix="/api/products", tags=["商品"])


@router.get("", response_model=ProductPageOut)
def list_products(
    keyword: str = Query(default="", description="按名称模糊搜索"),
    category: str = Query(default="", description="按分类精确过滤"),
    page: int = Query(default=1, description="页码，从 1 开始"),
    size: int = Query(default=10, ge=1, le=100, description="每页条数 1-100"),
    db: Session = Depends(get_db),
):
    """商品分页列表：搜索 + 过滤 + 分页三合一。

    【BUG-05 · 注入缺陷】page 参数只声明了类型没声明 ge=1，
    所以 page=0 也能通过校验：(0-1)*10 = -10 的负 offset。
    在 SQLite/MySQL 中负 offset 不报错，静默当作 0 处理——
    结果 page=0 和 page=1 返回完全相同的数据。

    这类"静默缺陷"比崩溃更危险：调用方拿到数据以为分页正常，
    错误会顺着数据流往下游蔓延（报表、缓存、前端翻页组件全部算错）。

    正确写法：page: int = Query(default=1, ge=1)，让 0 直接被 422 拒掉。
    我们的测试引擎会用边界值用例（page=0 / page=1 / page=巨大值）抓住它。
    """
    query = db.query(Product)

    # 关键字模糊搜索（SQLAlchemy 自动参数化，不会 SQL 注入）
    if keyword:
        query = query.filter(Product.name.like(f"%{keyword}%"))
    if category:
        query = query.filter(Product.category == category)

    total = query.count()          # 先记总数（分页不影响 total）
    items = (
        query.order_by(Product.id)  # 排序：保证翻页顺序稳定（测试断言依赖这一点）
        .offset((page - 1) * size)  # BUG-05 所在行：page=0 时 offset 为负
        .limit(size)
        .all()
    )
    return ProductPageOut(items=items, total=total, page=page, size=size)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """商品详情。不存在时返回 404——
    注意这里 product_id: int 的类型声明：传 "abc" 会被 422 挡下，
    传不存在的 id 才走到业务逻辑给 404。两种"错的姿势"要分开测。"""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product

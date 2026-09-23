"""购物车模块：查看 / 加购 / 改数量 / 删除。

接口清单：
    GET    /api/cart                我的购物车（需登录）
    POST   /api/cart                加入购物车（需登录）【BUG-04 入口】
    PUT    /api/cart/{item_id}      修改数量（需登录）【BUG-04 入口】
    DELETE /api/cart/{item_id}      删除条目（需登录）

安全设计说明：本模块的改/删操作【正确地】校验了条目归属
（filter user_id == me.id），拿别人的 item_id 会得到 404——
这是正确写法的示范。真正的越权缺陷(BUG-01)埋在订单详情接口，两者形成对照。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CartItem, Product, User
from ..schemas import CartItemAdd, CartItemUpdate, CartItemOut
from .auth import get_current_user

router = APIRouter(prefix="/api/cart", tags=["购物车"])


@router.get("", response_model=list[CartItemOut])
def my_cart(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的购物车，按加购时间排序。"""
    return (
        db.query(CartItem)
        .filter(CartItem.user_id == me.id)
        .order_by(CartItem.id)
        .all()
    )


@router.post("", response_model=CartItemOut, status_code=201)
def add_to_cart(
    payload: CartItemAdd,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """加入购物车。

    【BUG-04 · 注入缺陷】quantity 没有 gt=0 校验：
    POST {"product_id":1, "quantity":-5} 会成功返回 201。
    连锁反应见下单接口——总金额变负数、库存反而增加。

    业务规则：同一商品重复加购应"合并数量"而不是插新行
    （配合表上的 UniqueConstraint）。
    """
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    existing = (
        db.query(CartItem)
        .filter(CartItem.user_id == me.id, CartItem.product_id == payload.product_id)
        .first()
    )
    if existing:
        existing.quantity += payload.quantity
        db.commit()
        db.refresh(existing)
        return existing

    item = CartItem(user_id=me.id, product_id=payload.product_id,
                    quantity=payload.quantity)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=CartItemOut)
def update_quantity(
    item_id: int,
    payload: CartItemUpdate,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改数量。注意这里的 filter 同时校验了条目 id 和归属
    ——别人的购物车条目在这里查不到，返回 404（正确示范）。"""
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.user_id == me.id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="购物车条目不存在")

    item.quantity = payload.quantity  # BUG-04：负数照收不误
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def remove_item(
    item_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除条目。同样做了归属校验。204 = 删除成功，响应体为空。"""
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.user_id == me.id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="购物车条目不存在")
    db.delete(item)
    db.commit()

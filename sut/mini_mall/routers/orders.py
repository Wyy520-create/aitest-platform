"""订单模块：结算下单 / 我的订单 / 订单详情。

接口清单：
    POST /api/orders           结算购物车生成订单（需登录）【BUG-02/03 现场】
    GET  /api/orders           我的订单列表（需登录）
    GET  /api/orders/{id}      订单详情（需登录）【BUG-01 越权现场】
"""
from concurrent.futures import ThreadPoolExecutor  # noqa: F401 (文档注释用)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CartItem, Order, OrderItem, Product, User
from ..schemas import OrderOut, OrderPageOut
from .auth import get_current_user

router = APIRouter(prefix="/api/orders", tags=["订单"])


@router.post("", response_model=OrderOut, status_code=201)
def create_order(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """结算购物车：校验库存 -> 逐条扣减 -> 生成订单明细 -> 清空购物车。

    【BUG-02 · 注入缺陷 · 并发超卖】
    "检查库存"和"扣减库存"之间没有加锁（没有 SELECT ... FOR UPDATE，
    也没有数据库行锁/乐观锁）。并发时序：
        线程A: 读到 stock=5 -> 检查通过(买3) -> 写 stock=2
        线程B: 读到 stock=5 -> 检查通过(买3) -> 写 stock=2   <- 覆盖了A的写入！
    结果：卖出 6 件但库存只少了 3 件，超卖。
    正确做法其一：UPDATE products SET stock = stock - :qty
                  WHERE id=:id AND stock >= :qty，检查受影响行数。
    测试引擎用 10 线程并发下单库存 5 的商品来抓住它。

    【BUG-03 · 金额精度】total 用 float 累加：0.1 元商品 x3
    会得到 0.30000000000000004 而不是 0.3。
    """
    cart_items = (
        db.query(CartItem).filter(CartItem.user_id == me.id).all()
    )
    if not cart_items:
        raise HTTPException(status_code=400, detail="购物车为空，无法下单")

    # 阶段一：校验（并发缺陷就在这——校验和扣减之间可以被插入其他请求）
    for ci in cart_items:
        product = db.get(Product, ci.product_id)
        if product.stock < ci.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"库存不足：{product.name} 剩余 {product.stock}",
            )

    order = Order(user_id=me.id, total_amount=0)
    db.add(order)
    db.flush()  # flush 立刻拿到 order.id（还没 commit）

    total = 0.0
    # 阶段二：扣库存 + 生成明细
    for ci in cart_items:
        product = db.get(Product, ci.product_id)
        product.stock -= ci.quantity            # BUG-02：非原子的读-改-写
        total += product.price * ci.quantity    # BUG-03：float 累加
        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,          # 价格/名称快照
            price=product.price,
            quantity=ci.quantity,
        ))

    order.total_amount = total

    # 阶段三：清空购物车
    db.query(CartItem).filter(CartItem.user_id == me.id).delete()
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=OrderPageOut)
def my_orders(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的订单列表。这里【正确地】只查自己的订单（filter user_id）。"""
    orders = (
        db.query(Order)
        .filter(Order.user_id == me.id)
        .order_by(Order.id.desc())
        .all()
    )
    return OrderPageOut(items=orders, total=len(orders))


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """订单详情。

    【BUG-01 · 注入缺陷 · 水平越权】
    只校验了登录（get_current_user），没有校验 order.user_id == me.id。
    任何登录用户拿到别人的 order_id 就能看到别人的订单金额和购买明细——
    这就是"水平越权"（同为普通用户，越过了数据归属边界）。
    正确写法：
        if order.user_id != me.id:
            raise HTTPException(status_code=403, detail="无权查看该订单")
    攻击者可以写脚本遍历 order_id（1,2,3...）拖走全站订单数据。

    测试引擎的抓法：用户A下单 -> 用户B访问A的订单id -> 预期403，实际200。
    """
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    # BUG-01：这里少了归属校验，直接返回了别人的订单
    return order

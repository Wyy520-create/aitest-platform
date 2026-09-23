"""ORM 模型：5 张表定义整个电商的数据世界。

表关系（数据库设计基本功，面试爱画）：
    User 1--N CartItem N--1 Product          购物车
    User 1--N Order   1--N OrderItem N--1 Product   订单
"""
from datetime import datetime

from sqlalchemy import String, Integer, Float, ForeignKey, UniqueConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    """用户表：只存账号信息，绝不存明文密码（存的是哈希值）。"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="user")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Product(Base):
    """商品表。

    【BUG-03 · 注入缺陷】price 用了 Float。
    正确写法是 Numeric(10, 2)（精确十进制），因为二进制浮点数无法精确
    表示 0.1 这样的十进制小数：0.1 + 0.2 == 0.30000000000000004。
    金额计算用 Float 会累积精度误差——我们的测试引擎后面会用
    边界值用例（0.1 元商品 x 3 件）抓住它。
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(String(512), default="")
    # BUG-03: 正确应为 mapped_column(Numeric(10, 2))
    price: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer, default=0)   # 库存
    category: Mapped[str] = mapped_column(String(32), default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CartItem(Base):
    """购物车条目：某用户把某商品加了 N 件。

    UniqueConstraint：同一用户对同一商品在购物车里只能有一行
    （再点"加入购物车"应该是加数量，而不是多一行记录）。
    """
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_user_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    user: Mapped["User"] = relationship(back_populates="cart_items")
    product: Mapped["Product"] = relationship()


class Order(Base):
    """订单：一次结算生成一张。"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # 订单总金额。同样受 BUG-03 精度问题影响
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(16), default="paid")  # paid / cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    """订单明细：订单里的每一件商品。

    price 是"下单那一刻的价格快照"——之后商品改价、下架，
    历史订单的金额都不能变。这是电商系统的经典设计。
    """
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(128))     # 名称快照
    price: Mapped[float] = mapped_column(Float)                # 价格快照（同样受 BUG-03 影响）
    quantity: Mapped[int] = mapped_column(Integer)

    order: Mapped["Order"] = relationship(back_populates="items")

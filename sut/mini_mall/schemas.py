"""Pydantic Schema：接口的"契约"。

测试开发视角：接口测试的本质 = 验证服务端是否遵守契约。
- 请求 Schema：声明接口"收什么样的数据"，不合法的直接 422 拒之门外
- 响应 Schema：声明接口"吐什么样的数据"（也顺便过滤字段，防止泄露 password_hash）
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- 用户相关 ----------

class UserRegister(BaseModel):
    """注册请求体：POST /api/auth/register 的契约。

    Field 里的约束就是"参数校验规则"——之后测试引擎设计"异常参数用例"
    就专门往这些规则的边缘打（空用户名、超长用户名、超短密码...）。
    """
    username: str = Field(min_length=3, max_length=32, description="用户名 3-32 字符")
    password: str = Field(min_length=6, max_length=64, description="密码 6-64 字符")


class UserLogin(BaseModel):
    """登录请求体。"""
    username: str
    password: str


class UserOut(BaseModel):
    """用户信息响应：注意没有 password_hash 字段——
    响应模型同时承担"字段过滤"职责，敏感字段不出门。"""
    model_config = ConfigDict(from_attributes=True)  # 允许从 ORM 对象直接读取

    id: int
    username: str
    created_at: datetime


class TokenOut(BaseModel):
    """登录成功响应：返回 JWT。"""
    access_token: str
    token_type: str = "bearer"


# ---------- 商品相关 ----------

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: float
    stock: int
    category: str


class ProductPageOut(BaseModel):
    """商品分页列表响应：items + 分页元信息。

    分页三件套 total/page/size 是接口测试的经典断言对象：
    - total 恒定不变（翻页不影响总数）
    - page=1 的第一条 == 不分页时的第一条
    - 超出最后一页应返回空列表而不是报错
    """
    items: list[ProductOut]
    total: int
    page: int
    size: int


# ---------- 购物车相关 ----------

class CartItemAdd(BaseModel):
    """加购请求体。

    【BUG-04 · 注入缺陷】quantity 只声明了 int 类型，没有 gt=0 校验，
    所以 -5 也能通过——负数数量会导致下单时"倒贴钱 + 库存反向增加"。
    正确写法：quantity: int = Field(gt=0, le=999)
    """
    product_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    """修改数量请求体。同样不校验正数（BUG-04 的第二入口）。"""
    quantity: int


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    # 嵌套展示商品快照，前端购物车页不用二次查询
    product: Optional[ProductOut] = None


# ---------- 订单相关 ----------

class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    price: float
    quantity: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_amount: float
    status: str
    created_at: datetime
    items: list[OrderItemOut] = []


class OrderPageOut(BaseModel):
    items: list[OrderOut]
    total: int

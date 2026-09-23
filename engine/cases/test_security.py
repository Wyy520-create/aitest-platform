"""安全与质量专项用例：越权 / 并发 / 金额精度（本项目的高光用例集）。

这里每条用例都断言"正确行为"，失败 = 发现注入缺陷（docs/BUGS.md）。
"""
import threading

import pytest

from core.client import ApiClient
from core.helpers import random_username, random_password
from api.auth_api import AuthApi
from api.cart_api import CartApi
from api.order_api import OrderApi


def _new_user_client(base_url):
    """开一个新用户客户端（越权/并发测试都要多用户）。"""
    c = ApiClient(base_url)
    auth = AuthApi(c)
    u, p = random_username(), random_password()
    auth.register(u, p)
    auth.login_and_set_token(u, p)
    return c


@pytest.mark.bug_detection
def test_horizontal_privilege_escalation(base_url):
    """【BUG-01 检测】水平越权：用户B访问用户A的订单详情应 403。

    攻击路径还原：A 下单拿到 order_id -> B 携带自己的合法 token 访问
    /api/orders/{A的id}。正确行为是 403（认证通过但无权访问该资源）。
    实际返回 200 + A 的订单数据 = 任何登录用户可遍历拖走全站订单。
    """
    client_a = _new_user_client(base_url)
    CartApi(client_a).add(product_id=1, quantity=1)
    order = OrderApi(client_a).create().json()

    client_b = _new_user_client(base_url)
    resp = OrderApi(client_b).get(order["id"])
    assert resp.status_code == 403, (
        f"越权漏洞: 用户B成功(200)读取了用户A的订单 {order['id']}"
    )


@pytest.mark.bug_detection
def test_concurrent_no_oversell(base_url, rush_product, product_api):
    """【BUG-02 检测】并发超卖：库存 5 的商品，10 并发下单成功数必须 <= 5。

    检查库存与扣减库存非原子 -> 竞态窗口 -> 超卖/丢失更新。
    这是电商资损类缺陷的经典复现方式（秒杀场景模型）。
    """
    initial_stock = product_api.get(rush_product).json()["stock"]
    assert initial_stock == 5

    clients = [_new_user_client(base_url) for _ in range(10)]
    results = [None] * 10

    def buy(idx):
        c = clients[idx]
        CartApi(c).add(product_id=rush_product, quantity=1)
        results[idx] = OrderApi(c).create().status_code

    threads = [threading.Thread(target=buy, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    success = sum(1 for c in results if c == 201)
    final_stock = product_api.get(rush_product).json()["stock"]

    assert success <= initial_stock, (
        f"超卖! 库存{initial_stock}件却成交{success}单 "
        f"(剩余库存{final_stock}, 应扣减{success}件)"
    )
    assert final_stock == initial_stock - success, (
        f"库存扣减不一致: 成交{success}单但库存只从{initial_stock}变为{final_stock}"
    )


@pytest.mark.bug_detection
def test_amount_precision(user, cart_api, order_api):
    """【BUG-03 检测】金额精度：0.1 元商品 x3 的订单总额必须精确等于 0.3。

    金额用 float 累加产生 0.30000000000000004 —— 单笔误差虽小，
    百万笔订单累计后对账必炸。金融/电商系统的红线缺陷。
    """
    cart_api.add(product_id=3, quantity=3)  # 商品3: 0.1 元
    order = order_api.create().json()
    assert order["total_amount"] == 0.3, (
        f"金额精度缺陷: 0.1 x 3 = {order['total_amount']}"
    )


@pytest.mark.bug_detection
def test_negative_quantity_order_amount(user, cart_api, order_api):
    """【BUG-04 连锁检测】负数数量下单后订单总额不得为负。

    加购 -5 (BUG-04) -> 下单 -> 总额 -495.0：平台倒贴钱 + 库存反向增加。
    验证"校验缺失沿业务链放大"的连锁效应。
    """
    cart_api.add(product_id=1, quantity=-5)  # BUG-04: 这里应该已经 422
    resp = order_api.create()
    if resp.status_code == 201:
        assert resp.json()["total_amount"] >= 0, (
            f"负数订单: 总额 {resp.json()['total_amount']} 元, 平台倒贴!"
        )

"""购物车模块用例：CRUD + 归属校验(正确行为) + BUG-04 检测。"""
import pytest

from core.client import ApiClient
from core.helpers import random_username, random_password
from api.auth_api import AuthApi
from api.cart_api import CartApi


def test_add_to_cart_success(user, cart_api):
    resp = cart_api.add(product_id=1, quantity=2)
    assert resp.status_code == 201
    body = resp.json()
    assert body["product_id"] == 1 and body["quantity"] == 2
    # 嵌套商品快照（前端免二次查询）
    assert body["product"]["id"] == 1


def test_add_same_product_merges_quantity(user, cart_api):
    """同一商品重复加购应合并数量，不是插新行。"""
    cart_api.add(product_id=1, quantity=1)
    resp = cart_api.add(product_id=1, quantity=2)
    assert resp.status_code == 201
    items = cart_api.my().json()
    assert len(items) == 1
    assert items[0]["quantity"] == 3


def test_update_quantity(user, cart_api):
    cart_api.add(product_id=1, quantity=1)
    item_id = cart_api.my().json()[0]["id"]
    resp = cart_api.update(item_id, quantity=5)
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 5


def test_remove_item(user, cart_api):
    cart_api.add(product_id=1, quantity=1)
    item_id = cart_api.my().json()[0]["id"]
    assert cart_api.remove(item_id).status_code == 204
    assert cart_api.my().json() == []


def test_cart_requires_login(cart_api):
    assert cart_api.my().status_code == 401


def test_add_nonexistent_product(user, cart_api):
    assert cart_api.add(product_id=99999, quantity=1).status_code == 404


def test_cannot_touch_others_cart_item(user, cart_api, base_url):
    """归属校验(正确行为)：B 改/删 A 的购物车条目应 404。

    用第二个独立客户端模拟另一个用户（与 BUG-01 的订单详情形成对照：
    购物车做对了，订单没做）。
    """
    cart_api.add(product_id=1, quantity=1)
    item_id = cart_api.my().json()[0]["id"]

    client_b = ApiClient(base_url)
    auth_b = AuthApi(client_b)
    username, password = random_username(), random_password()
    auth_b.register(username, password)
    auth_b.login_and_set_token(username, password)

    cart_b = CartApi(client_b)
    assert cart_b.update(item_id, 10).status_code == 404
    assert cart_b.remove(item_id).status_code == 404


@pytest.mark.bug_detection
def test_negative_quantity_should_be_rejected(user, cart_api):
    """【BUG-04 检测】quantity=-5 是非法值，契约应拒绝(422)。

    实际返回 201——负数数量进入下单链路后：总金额为负(平台倒贴)、
    库存反向增加。单点校验缺失沿业务链放大成资金风险。
    """
    assert cart_api.add(product_id=1, quantity=-5).status_code == 422


@pytest.mark.bug_detection
def test_zero_quantity_should_be_rejected(user, cart_api):
    """【BUG-04 检测】quantity=0 同样非法（"买0件"无业务意义）。"""
    assert cart_api.add(product_id=1, quantity=0).status_code == 422

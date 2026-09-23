"""订单模块正向业务用例：下单链路的完整验证。"""
from core.client import ApiClient
from core.helpers import random_username, random_password
from api.auth_api import AuthApi


def test_create_order_empty_cart(user, order_api):
    """空购物车下单：400（业务规则拒绝）。"""
    assert order_api.create().status_code == 400


def test_create_order_success(user, cart_api, order_api, product_api):
    """正常下单全链路：加购 -> 下单 -> 断言金额/明细/扣库存/清购物车。"""
    product = product_api.get(1).json()
    cart_api.add(product_id=1, quantity=2)

    resp = order_api.create()
    assert resp.status_code == 201
    order = resp.json()

    # 金额正确
    assert order["total_amount"] == product["price"] * 2
    # 明细快照正确
    assert len(order["items"]) == 1
    item = order["items"][0]
    assert item["product_name"] == product["name"]
    assert item["price"] == product["price"]
    assert item["quantity"] == 2
    # 库存已扣减
    assert product_api.get(1).json()["stock"] == product["stock"] - 2
    # 购物车已清空
    assert cart_api.my().json() == []


def test_order_insufficient_stock(user, cart_api, order_api, product_api):
    """库存不足：400 且报错信息含商品名（可定位性断言）。"""
    product = product_api.get(1).json()
    resp = cart_api.add(product_id=1, quantity=product["stock"] + 1)
    # BUG-04 的存在让超大数量能进购物车——这里 quantity 本身是正数，不受影响
    resp = order_api.create()
    assert resp.status_code == 400
    assert product["name"] in resp.json()["detail"]


def test_my_orders_only_shows_own(user, cart_api, order_api, base_url):
    """订单列表只包含自己的订单（正确行为，与详情接口的 BUG-01 对照）。"""
    cart_api.add(product_id=1, quantity=1)
    order_api.create()

    # 用户B 登录，他的订单列表应为空
    client_b = ApiClient(base_url)
    auth_b = AuthApi(client_b)
    u, p = random_username(), random_password()
    auth_b.register(u, p)
    auth_b.login_and_set_token(u, p)

    from api.order_api import OrderApi
    body = OrderApi(client_b).my().json()
    assert body["total"] == 0
    assert body["items"] == []

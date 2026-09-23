"""pytest 全局夹具（fixture 层）。

分层: cases(用例) -> api(接口对象) -> core(客户端) ，夹具在这层组装注入。
用例文件里不 import 任何底层类，全部通过 fixture 拿——依赖倒置。
"""
import os
import sqlite3
from pathlib import Path

import pytest
import requests

from core.client import ApiClient
from core.helpers import random_username, random_password
from api.auth_api import AuthApi
from api.product_api import ProductApi
from api.cart_api import CartApi
from api.order_api import OrderApi

BASE_URL = os.getenv("SUT_BASE_URL", "http://localhost:8000")

# 被测系统 SQLite 库文件（仅用于测试数据准备，如重置秒杀库存）
SUT_DB = Path(__file__).resolve().parent.parent / "sut" / "mini_mall.db"

# 秒杀商品 id（种子数据：库存 5，专测 BUG-02）
RUSH_PRODUCT_ID = 7


@pytest.fixture(scope="session")
def base_url():
    """session 级：整个测试会话只检查一次服务存活。"""
    try:
        resp = requests.get(BASE_URL + "/", timeout=3)
        assert resp.status_code == 200
    except Exception:
        pytest.exit(
            f"\n被测系统未启动！请先运行:\n"
            f"  cd sut && uvicorn mini_mall.main:app --port 8000\n"
            f"(当前探测地址: {BASE_URL})",
            returncode=4,
        )
    return BASE_URL


@pytest.fixture
def client(base_url):
    """每个用例一个全新客户端（token 独立，用例间零污染）。"""
    return ApiClient(base_url)


@pytest.fixture
def auth_api(client):
    return AuthApi(client)


@pytest.fixture
def product_api(client):
    return ProductApi(client)


@pytest.fixture
def cart_api(client):
    return CartApi(client)


@pytest.fixture
def order_api(client):
    return OrderApi(client)


@pytest.fixture
def user(auth_api):
    """注册+登录+token 已装进 client 的用户。返回 (username, password)。"""
    username, password = random_username(), random_password()
    auth_api.register(username, password)
    auth_api.login_and_set_token(username, password)
    return username, password


@pytest.fixture
def rush_product(base_url):
    """并发测试专用：把秒杀商品库存重置为 5。

    数据准备两级降级（灰盒 -> 纯黑盒）：
    1. 本地开发：引擎与 SUT 同机，直连 SQLite 重置（最快）
    2. 容器/CI：引擎与 SUT 隔离，走 SUT 的 TEST_MODE 数据工厂接口
       （POST /api/dev/reset-stock，生产环境不注册该路由）

    验证阶段始终纯黑盒（只通过 HTTP 断言）。测试环境的数据准备
    直连库或走数据工厂，被测行为验证走接口——公司里的标准做法。
    """
    def _reset(stock: int):
        if SUT_DB.exists():
            conn = sqlite3.connect(SUT_DB)
            conn.execute("UPDATE products SET stock = ? WHERE id = ?", (stock, RUSH_PRODUCT_ID))
            conn.commit()
            conn.close()
        else:
            resp = requests.post(
                f"{BASE_URL}/api/dev/reset-stock",
                json={"product_id": RUSH_PRODUCT_ID, "stock": stock}, timeout=10,
            )
            if resp.status_code == 404:
                pytest.skip("SUT 未开启 TEST_MODE（无数据工厂接口）且非本地开发模式")
            resp.raise_for_status()

    _reset(5)
    yield RUSH_PRODUCT_ID
    _reset(5)  # 收尾：再重置，不影响后续用例

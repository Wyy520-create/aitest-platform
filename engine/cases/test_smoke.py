"""冒烟用例：服务基本可用性。任何一条挂了，其余用例的结果都无意义。"""
import pytest


@pytest.mark.smoke
def test_health(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.smoke
def test_docs_available(client):
    """交互式文档可访问（AI 生成用例模块会读取 OpenAPI）。"""
    resp = client.get("/docs")
    assert resp.status_code == 200


@pytest.mark.smoke
def test_products_seeded(product_api):
    """种子商品已就位（依赖种子数据的用例前置）。"""
    resp = product_api.list(size=100)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 6

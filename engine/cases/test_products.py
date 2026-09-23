"""商品模块用例：分页/搜索/过滤/详情 + BUG-05 检测。"""
import pytest


def test_list_default_pagination(product_api):
    resp = product_api.list()
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1 and body["size"] == 10
    assert len(body["items"]) <= 10


def test_paging_no_overlap(product_api):
    """翻页正确性：第1页与第2页的商品 id 不得重叠。"""
    p1 = product_api.list(page=1, size=3).json()
    p2 = product_api.list(page=2, size=3).json()
    ids1 = {i["id"] for i in p1["items"]}
    ids2 = {i["id"] for i in p2["items"]}
    assert not (ids1 & ids2), f"第1/2页出现重复商品: {ids1 & ids2}"


def test_total_constant_across_pages(product_api):
    """total 与页码无关（分页元数据一致性）。"""
    t1 = product_api.list(page=1, size=2).json()["total"]
    t2 = product_api.list(page=5, size=2).json()["total"]
    assert t1 == t2


def test_page_beyond_last_returns_empty(product_api):
    """超出末页：返回空列表而不是报错（健壮性）。"""
    body = product_api.list(page=999, size=10).json()
    assert body["items"] == []


def test_keyword_search(product_api):
    body = product_api.list(keyword="USB").json()
    assert body["total"] >= 1
    assert all("USB" in i["name"] for i in body["items"])


def test_category_filter(product_api):
    body = product_api.list(category="trinket").json()
    assert all(i["category"] == "trinket" for i in body["items"])


def test_combined_filter(product_api):
    body = product_api.list(keyword="USB", category="digital").json()
    assert all("USB" in i["name"] and i["category"] == "digital"
               for i in body["items"])


def test_get_product_success(product_api):
    resp = product_api.get(1)
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


def test_get_product_not_found(product_api):
    assert product_api.get(99999).status_code == 404


def test_get_product_invalid_id_format(product_api):
    """id 传非数字：422（类型校验层拦截），而不是 500。"""
    assert product_api.get("abc").status_code == 422


def test_size_zero_rejected(product_api):
    """size=0 有下界校验（ge=1），应 422——正确行为对照组。"""
    assert product_api.list(size=0).status_code == 422


@pytest.mark.bug_detection
def test_page_zero_should_be_rejected(product_api):
    """【BUG-05 检测】page=0 是非法页码，服务端应拒绝(422/400)。

    实际返回 200 且数据与 page=1 相同——负 offset 被静默吞掉。
    静默错误会沿数据流蔓延（报表/缓存/前端翻页全错）。
    """
    assert product_api.list(page=0).status_code == 422

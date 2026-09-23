"""接口对象层：商品模块。"""
from core.client import ApiClient


class ProductApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def list(self, keyword: str = None, category: str = None,
             page: int = None, size: int = None):
        """商品列表。None 的参数不发送（用服务端默认值）。"""
        params = {k: v for k, v in {
            "keyword": keyword, "category": category,
            "page": page, "size": size}.items() if v is not None}
        return self.client.get("/api/products", params=params)

    def get(self, product_id):
        return self.client.get(f"/api/products/{product_id}")

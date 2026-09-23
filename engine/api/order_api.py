"""接口对象层：订单模块。"""
from core.client import ApiClient


class OrderApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def create(self):
        """结算购物车生成订单。"""
        return self.client.post("/api/orders")

    def my(self):
        return self.client.get("/api/orders")

    def get(self, order_id: int):
        return self.client.get(f"/api/orders/{order_id}")

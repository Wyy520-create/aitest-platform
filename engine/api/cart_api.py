"""接口对象层：购物车模块。"""
from core.client import ApiClient


class CartApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def my(self):
        return self.client.get("/api/cart")

    def add(self, product_id: int, quantity: int = 1):
        return self.client.post("/api/cart",
                                json={"product_id": product_id,
                                      "quantity": quantity})

    def update(self, item_id: int, quantity: int):
        return self.client.put(f"/api/cart/{item_id}",
                               json={"quantity": quantity})

    def remove(self, item_id: int):
        return self.client.delete(f"/api/cart/{item_id}")

"""接口对象层：auth 模块。

每个业务接口封装成一个方法——用例代码里只出现业务语义
(auth_api.login(...))，不出现 URL/JSON 细节。
接口路径变了只改这一个文件，这就是"接口对象层"的价值。
"""
from core.client import ApiClient
from core.helpers import random_username, random_password


class AuthApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def register(self, username: str = None, password: str = None):
        """注册。不传参则随机生成（大多数用例只需要"一个能用的账号"）。"""
        body = {"username": username or random_username(),
                "password": password or random_password()}
        return self.client.post("/api/auth/register", json=body)

    def login(self, username: str, password: str):
        return self.client.post("/api/auth/login",
                                json={"username": username, "password": password})

    def login_and_set_token(self, username: str, password: str):
        """登录并把 token 装进 client（之后请求自动带）。"""
        resp = self.login(username, password)
        self.client.set_token(resp.json()["access_token"])
        return resp

    def me(self):
        return self.client.get("/api/auth/me")

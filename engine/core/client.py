"""HTTP 客户端封装（core 层）。

职责：统一 base_url、请求头、token 管理、日志。
所有接口对象(api 层)都通过它发请求——换 HTTP 库/加超时/加重试只改这里。
"""
import requests


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token: str | None = None   # 登录后自动携带
        self.session = requests.Session()

    def set_token(self, token: str):
        """登录成功后调用；之后所有请求自动带 Authorization 头。"""
        self.token = token

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, method: str, path: str, **kwargs):
        """统一入口：拼 URL、带头、带超时。返回原始 Response 对象。"""
        url = self.base_url + path
        return self.session.request(
            method, url,
            headers=self._headers(),
            timeout=self.timeout,
            **kwargs,
        )

    # 语义化快捷方法，接口对象层用起来更顺手
    def get(self, path, **kw):     return self.request("GET", path, **kw)
    def post(self, path, **kw):    return self.request("POST", path, **kw)
    def put(self, path, **kw):     return self.request("PUT", path, **kw)
    def delete(self, path, **kw):  return self.request("DELETE", path, **kw)

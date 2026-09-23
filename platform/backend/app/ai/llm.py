"""LLM 客户端：DeepSeek API 封装 + Mock 降级。

设计原则：没配 API key 时自动降级为 MockLLM——整个平台的
AI 流程（生成->评审->执行）依然可以完整演示，只是"生成"环节
由规则模板代替大模型。这让开源项目 clone 下来就能跑。
"""
import json

import requests

from ..config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


class RealLLM:
    """DeepSeek Chat API。"""
    name = "deepseek"

    def chat(self, system: str, user: str) -> str:
        resp = requests.post(
            f"{LLM_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,   # 测试用例生成要稳定，低温度
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class MockLLM:
    """规则模板"生成器"：无 key 时的可演示替身。"""
    name = "mock"

    def chat(self, system: str, user: str) -> str:
        """user 里带 openapi 摘要(JSON)，按模板吐出同格式结果。"""
        # 从 prompt 中截取 JSON 部分（首 { 到尾 }），
        # 避免 prompt 尾部的文字说明混进来导致解析失败静默降级
        start, end = user.find("{"), user.rfind("}")
        try:
            spec = json.loads(user[start:end + 1]) if start != -1 else {}
        except json.JSONDecodeError:
            spec = {}
        paths = spec.get("paths", {})
        cases = []
        for path, methods in list(paths.items())[:4]:  # 每次最多处理4个路径
            for method, info in methods.items():
                if method not in ("get", "post", "put", "delete"):
                    continue
                cases.append({
                    "name": f"[mock] {method.upper()} {path} 正常请求",
                    "module": info.get("tags", ["general"])[0],
                    "request": {"method": method.upper(), "path": path, "auth": True},
                    "expect": {"status_code": 200},
                    "rationale": "Mock 模板: 冒烟级正向用例",
                })
                if method == "get" and "{" not in path:
                    cases.append({
                        "name": f"[mock] {method.upper()} {path} 异常参数",
                        "module": info.get("tags", ["general"])[0],
                        "request": {"method": "GET", "path": path + "?page=-1", "auth": False},
                        "expect": {"status_code": 422},
                        "rationale": "Mock 模板: 异常参数用例",
                    })
        return json.dumps(cases, ensure_ascii=False)


def get_llm():
    """工厂：有 key 用真模型，没 key 用 Mock。"""
    return RealLLM() if LLM_API_KEY else MockLLM()

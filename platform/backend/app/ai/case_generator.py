"""AI 用例生成器：OpenAPI -> Prompt -> 结构化用例草稿。

Prompt 工程要点（这段 prompt 本身就是面试展示物）：
- 给角色（资深测试开发）+ 明确任务 + 输出格式约束（纯 JSON）
- 要求覆盖正向/边界值/异常参数/越权四类设计方法
- 要求每条带 rationale（设计依据），供人工评审参考
"""
import json
import re

import requests

from ..config import SUT_BASE_URL
from ..database import SessionLocal
from ..models import ConfigCase
from .llm import get_llm

SYSTEM_PROMPT = """你是资深测试开发工程师，擅长接口测试用例设计。
给定一组 REST API 定义，为每个接口设计测试用例，要求：
1. 覆盖四类设计方法：正向功能、边界值（长度/数值/分页边界）、异常参数（类型错误/缺失/非法值）、安全（越权/未登录）。
2. 每条用例输出: name(中文名), module(接口tag), request{method,path,body?,auth}, expect{status_code,json_contains?}, rationale(一句话设计依据)。
3. 只输出 JSON 数组，不要输出任何其他文字、不要 markdown 代码块标记。"""

USER_PROMPT_TMPL = """接口清单如下:
{spec}

请基于以上接口设计 8-15 条最有价值的测试用例，按系统要求的 JSON 数组格式输出。"""


def fetch_openapi() -> dict:
    """从被测系统拉 OpenAPI 规范并瘦身（只保留路径/方法/参数摘要，省 token）。"""
    spec = requests.get(f"{SUT_BASE_URL}/openapi.json", timeout=15).json()
    slim = {"paths": {}}
    for path, methods in spec.get("paths", {}).items():
        slim["paths"][path] = {}
        for method, info in methods.items():
            if method not in ("get", "post", "put", "delete"):
                continue
            slim["paths"][path][method] = {
                "tags": info.get("tags", ["general"]),
                "summary": info.get("summary", ""),
                "params": [p.get("name") for p in info.get("parameters", [])],
            }
    return slim


def parse_llm_cases(raw: str) -> list[dict]:
    """从 LLM 输出中提取 JSON（容忍 markdown 代码块包裹等噪声）。"""
    text = raw.strip()
    text = re.sub(r"^```(json)?\s*|\s*```$", "", text)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        cases = json.loads(text[start:end + 1])
        return [c for c in cases if isinstance(c, dict) and "request" in c]
    except json.JSONDecodeError:
        return []


def generate_and_save() -> dict:
    """完整流程：拉接口文档 -> LLM 生成 -> 解析 -> 存为 draft 草稿。"""
    llm = get_llm()
    spec = fetch_openapi()
    raw = llm.chat(SYSTEM_PROMPT, USER_PROMPT_TMPL.format(spec=json.dumps(spec, ensure_ascii=False)))
    cases = parse_llm_cases(raw)

    db = SessionLocal()
    saved_ids = []
    try:
        for c in cases:
            req = c["request"]
            if req.get("method") not in ("GET", "POST", "PUT", "DELETE"):
                continue
            if not str(req.get("path", "")).startswith("/"):
                continue
            case = ConfigCase(
                name=str(c.get("name", "未命名用例"))[:120],
                module=str(c.get("module", "general"))[:30],
                source="ai", status="draft",
                request_json=json.dumps({
                    "method": req["method"], "path": req["path"],
                    "body": req.get("body"), "auth": bool(req.get("auth", False)),
                }, ensure_ascii=False),
                expect_json=json.dumps(c.get("expect", {}), ensure_ascii=False),
                review_note=str(c.get("rationale", ""))[:500],
            )
            db.add(case)
            db.commit()
            db.refresh(case)
            saved_ids.append(case.id)
    finally:
        db.close()
    return {"llm": llm.name, "generated": len(saved_ids), "case_ids": saved_ids}

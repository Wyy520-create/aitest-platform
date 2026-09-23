"""执行引擎调度：subprocess 跑 pytest 套件 / requests 跑配置化用例。

两类执行器各司其职（面试点：代码化用例 vs 配置化用例的适用边界）：
- suite  = engine/ 下的 Pytest 代码套件。表达力强（并发、多用户、复杂断言），
           但修改需要发版。适合核心回归。
- config = 平台数据库里的 JSON 用例。非程序员也能在网页上建，
           即时生效。适合快速补充、AI 生成用例的载体。
"""
import json
import subprocess
import time
import xml.etree.ElementTree as ET

import requests as http

from .config import ENGINE_RUN, SUT_BASE_URL
from .database import SessionLocal
from .models import Execution, ExecutionResult, ConfigCase


def _run_suite(execution_id: int):
    """后台线程：跑 pytest 套件，解析 junitxml，结果入库。"""
    db = SessionLocal()
    xml_path = f"/tmp/pytest-exec-{execution_id}.xml"
    try:
        start = time.time()
        proc = subprocess.run(
            [str(ENGINE_RUN), f"--junitxml={xml_path}", "-q", "--tb=line"],
            capture_output=True, text=True, timeout=600,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin", "SUT_BASE_URL": SUT_BASE_URL},
        )
        duration = time.time() - start

        tree = ET.parse(xml_path)
        suite = tree.getroot()

        total = passed = failed = bug_found = 0
        for case in suite.iter("testcase"):
            classname = case.get("classname", "")
            name = f"{classname}::{case.get('name')}"
            # pytest 的 marker 不会写进 junitxml，故用命名约定识别缺陷检测用例：
            # test_bug 前缀 = 主动探测缺陷的用例（见 docs/BUGS.md）
            is_bug = 1 if "test_bug" in classname or "test_bug" in name else 0

            failure = case.find("failure")
            error = case.find("error")
            if failure is not None:
                outcome, msg = "failed", (failure.get("message") or failure.text or "")[:500]
            elif error is not None:
                outcome, msg = "error", (error.get("message") or error.text or "")[:500]
            else:
                outcome, msg = "passed", ""

            total += 1
            passed += outcome == "passed"
            failed += outcome != "passed"
            bug_found += is_bug and outcome != "passed"
            db.add(ExecutionResult(
                execution_id=execution_id, case_name=name, outcome=outcome,
                duration=float(case.get("time", 0)), message=msg, is_bug_detection=is_bug,
            ))

        exec_rec = db.get(Execution, execution_id)
        exec_rec.total, exec_rec.passed = total, passed
        exec_rec.failed, exec_rec.bug_found = failed, bug_found
        exec_rec.duration = duration
        exec_rec.status = "failed" if failed else "passed"
        if proc.returncode not in (0, 1):  # pytest: 0=全过 1=有失败; 其他=引擎自身出错
            exec_rec.status = "error"
    except Exception as e:
        exec_rec = db.get(Execution, execution_id)
        exec_rec.status = "error"
        db.add(ExecutionResult(
            execution_id=execution_id, case_name="ENGINE", outcome="error",
            message=str(e)[:500],
        ))
    finally:
        from datetime import datetime
        exec_rec = db.get(Execution, execution_id)
        exec_rec.finished_at = datetime.now()
        db.commit()
        db.close()


def _assert_json_contains(actual: dict, expected: dict, path: str = "") -> str:
    """局部匹配断言：expected 的每个键值都必须出现在 actual 中（支持嵌套）。
    比全等断言实用：响应多字段/字段顺序不影响判定。"""
    for key, want in expected.items():
        if key not in actual:
            return f"缺少字段 {path}{key}"
        got = actual[key]
        if isinstance(want, dict):
            if not isinstance(got, dict):
                return f"{path}{key} 应为对象"
            sub = _assert_json_contains(got, want, f"{path}{key}.")
            if sub:
                return sub
        elif got != want:
            return f"{path}{key}: 期望 {want!r}, 实际 {got!r}"
    return ""


def _run_one_config_case(case: ConfigCase, token: str | None) -> tuple[str, str, float]:
    """执行单条配置化用例，返回 (outcome, message, duration)。"""
    req = json.loads(case.request_json)
    expect = json.loads(case.expect_json or "{}")
    start = time.time()
    try:
        headers = dict(req.get("headers") or {})
        if req.get("auth") and token:
            headers["Authorization"] = f"Bearer {token}"
        resp = http.request(
            req["method"], SUT_BASE_URL + req["path"],
            json=req.get("body"), headers=headers, timeout=15,
        )
        duration = time.time() - start

        want_code = expect.get("status_code")
        if want_code is not None and resp.status_code != want_code:
            return "failed", f"状态码 期望{want_code} 实际{resp.status_code}: {resp.text[:200]}", duration

        if expect.get("json_contains"):
            try:
                mismatch = _assert_json_contains(resp.json(), expect["json_contains"])
            except Exception:
                return "failed", f"响应不是 JSON: {resp.text[:200]}", duration
            if mismatch:
                return "failed", f"断言不匹配: {mismatch}", duration
        return "passed", "", duration
    except Exception as e:
        return "error", f"请求异常: {e}", time.time() - start


def _run_config(execution_id: int, case_ids: list[int] | None):
    """后台线程：跑配置化用例（reviewed 状态的，或指定 id 的）。"""
    db = SessionLocal()
    try:
        query = db.query(ConfigCase)
        if case_ids:
            cases = query.filter(ConfigCase.id.in_(case_ids)).all()
        else:
            cases = query.filter(ConfigCase.status == "reviewed").all()

        # 登录态预取：用 sut 的演示账号换 token，auth=true 的用例共用
        token = None
        try:
            r = http.post(f"{SUT_BASE_URL}/api/auth/login",
                          json={"username": "qa_platform", "password": "pass123456"}, timeout=10)
            if r.status_code != 200:  # 账号不存在则注册后重试
                http.post(f"{SUT_BASE_URL}/api/auth/register",
                          json={"username": "qa_platform", "password": "pass123456"}, timeout=10)
                r = http.post(f"{SUT_BASE_URL}/api/auth/login",
                              json={"username": "qa_platform", "password": "pass123456"}, timeout=10)
            token = r.json().get("access_token")
        except Exception:
            token = None

        total = passed = failed = 0
        start = time.time()
        for case in cases:
            outcome, msg, dur = _run_one_config_case(case, token)
            total += 1
            passed += outcome == "passed"
            failed += outcome != "passed"
            db.add(ExecutionResult(
                execution_id=execution_id, case_name=f"[config] {case.name}",
                outcome=outcome, duration=dur, message=msg,
            ))
        exec_rec = db.get(Execution, execution_id)
        exec_rec.total, exec_rec.passed, exec_rec.failed = total, passed, failed
        exec_rec.duration = time.time() - start
        exec_rec.status = "failed" if failed else ("passed" if total else "error")
    except Exception as e:
        db.get(Execution, execution_id).status = "error"
    finally:
        from datetime import datetime
        db.get(Execution, execution_id).finished_at = datetime.now()
        db.commit()
        db.close()


def start_execution(execution_id: int, exec_type: str, case_ids: list[int] | None = None):
    """调度入口：起后台线程执行，立即返回（前端轮询状态）。"""
    import threading
    if exec_type == "suite":
        threading.Thread(target=_run_suite, args=(execution_id,), daemon=True).start()
    else:
        threading.Thread(target=_run_config, args=(execution_id, case_ids), daemon=True).start()

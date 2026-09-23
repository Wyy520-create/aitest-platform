"""校验测试套件行为是否符合"预期签名"。

本仓库是缺陷注入型项目：套件跑出 7 条失败是【正确】表现——
它们全部是命中注入缺陷的缺陷检测用例（test_bug 前缀）。
CI 不能断言"全绿"，而要断言"失败模式符合预期"：
    45 条用例 / 38 过 / 7 失败 / 7 条失败全部命中缺陷
一旦任何一条注入缺陷被修复（或套件被改坏），签名变化，CI 立刻报警。

用法: python3 scripts/verify_suite.py <junit.xml 路径>
退出码: 0=符合预期  1=不符合
"""
import sys
import xml.etree.ElementTree as ET

EXPECTED = dict(total=45, passed=38, failed=7, bug_failed=7)


def main(path: str) -> int:
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    total = len(cases)

    def failed(c) -> bool:
        return c.find("failure") is not None or c.find("error") is not None

    failed_n = sum(1 for c in cases if failed(c))
    bug_failed = sum(
        1 for c in cases
        if failed(c) and "test_bug" in c.get("name", "")
    )
    actual = dict(total=total, passed=total - failed_n,
                  failed=failed_n, bug_failed=bug_failed)

    if actual != EXPECTED:
        print(f"[FAIL] 套件行为偏离预期签名!")
        print(f"        期望: {EXPECTED}")
        print(f"        实际: {actual}")
        return 1

    print(f"[OK] 套件行为符合预期签名: {total} 用例 / {total - failed_n} 通过 / "
          f"{failed_n} 失败(全部命中注入缺陷)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "junit.xml"))

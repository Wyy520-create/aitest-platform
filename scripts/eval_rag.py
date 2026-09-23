"""RAG 检索层质量评测（CLI 入口，CI 直接跑，无需起服务）。

用法:
    python3 scripts/eval_rag.py
退出码: 0=全部用例通过  1=有不通过（CI 挂红）

说明: 评测只覆盖检索层（hit@3 / MRR / 拒答），确定性输出，可稳定断言。
生成层（LLM 回答质量）波动大，属于人工评审范畴，不在 CI 断言。
"""
import sys
from pathlib import Path

# 让脚本能直接 import 平台后端代码（不装包、不起服务）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "platform" / "backend"))

from app.rag.evaluator import evaluate  # noqa: E402


def main() -> int:
    report = evaluate()

    print("=" * 60)
    print("RAG 检索层质量评测报告")
    print("=" * 60)
    print(f"用例总数:       {report['total']}")
    print(f"hit@3:          {report['hit_at_k']}")
    print(f"MRR:            {report['mrr']}")
    print(f"拒答正确率:     {report['refuse_accuracy']}  (阈值 {report['threshold']})")
    print("-" * 60)
    for cat, s in report["by_category"].items():
        flag = "OK " if s["rate"] == 1.0 else "!! "
        print(f"{flag}{cat}: {s['ok']}/{s['total']} (通过率 {s['rate']})")
    print("-" * 60)

    for d in report["details"]:
        if not d["ok"]:
            print(f"[未通过] {d['id']} [{d['category']}] {d['question']}")
            print(f"         期望: {d['expect']}")
            print(f"         实际: {d['top_titles']} (top_score={d['top_score']})")

    if report["all_passed"]:
        print("\n结论: 全部通过 ✓  (hit@3 与拒答均达标)")
        return 0
    print("\n结论: 存在未通过用例 ✗")
    return 1


if __name__ == "__main__":
    sys.exit(main())

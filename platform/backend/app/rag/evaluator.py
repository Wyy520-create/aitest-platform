"""RAG 质量评测器：对 6 类场景评测集跑检索层指标。

只评测"检索层"（hit@3 / MRR / 拒答判定），不评测生成层——
检索层是确定性的（同样输入永远同样输出），可以在 CI 里稳定断言；
生成层质量依赖 LLM 输出波动，属于人工/LLM-as-judge 的范畴。

指标定义：
- hit@3:  期望片段出现在 top-3 召回里（知识问答的可用性底线）
- MRR:    第一个命中片段的排名倒数（1.0=第一名命中）
- refuse: 知识库外问题被正确拒答（幻觉防护底线）
"""
import json
from pathlib import Path

from . import REFUSE_THRESHOLD
from .knowledge import get_index

DATASET = Path(__file__).parent / "eval_dataset.json"


def evaluate(top_k: int = 3) -> dict:
    """跑全部评测用例，返回总体指标 + 逐条明细。"""
    cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
    index = get_index()

    details = []
    hit_n = mrr_sum = 0
    non_refuse_n = 0
    refuse_ok_n = refuse_n = 0

    for case in cases:
        hits = index.search(case["question"], top_k=top_k)
        top_titles = [d.title for d, _ in hits]
        # 拒答判定用「得分率」而非 BM25 绝对分：绝对分与查询长度正相关，
        # 口语化短查询会被误杀（踩坑与推导见 bm25.py.ideal_score）。
        ideal = index.ideal_score(case["question"])
        top_score = (hits[0][1] / ideal) if hits and ideal else 0.0

        if case.get("expect") == "refuse":
            refused = top_score < REFUSE_THRESHOLD
            refuse_n += 1
            refuse_ok_n += refused
            details.append(dict(
                id=case["id"], category=case["category"], question=case["question"],
                expect="refuse", refused=refused, ok=refused,
                top_titles=top_titles, top_score=round(top_score, 3),
            ))
            continue

        non_refuse_n += 1
        expected = set(case["expected_titles"])
        rank = next((i + 1 for i, t in enumerate(top_titles) if t in expected), None)
        hit = rank is not None
        hit_n += hit
        if hit:
            mrr_sum += 1 / rank
        details.append(dict(
            id=case["id"], category=case["category"], question=case["question"],
            expect=case["expected_titles"], hit=hit, rank=rank, ok=hit,
            top_titles=top_titles, top_score=round(top_score, 2),
        ))

    # 分类别汇总（每类通过率）
    by_category: dict[str, dict] = {}
    for d in details:
        c = by_category.setdefault(d["category"], dict(total=0, ok=0))
        c["total"] += 1
        c["ok"] += d["ok"]

    return {
        "total": len(details),
        "hit_at_k": round(hit_n / non_refuse_n, 3) if non_refuse_n else None,
        "mrr": round(mrr_sum / non_refuse_n, 3) if non_refuse_n else None,
        "refuse_accuracy": round(refuse_ok_n / refuse_n, 3) if refuse_n else None,
        "threshold": REFUSE_THRESHOLD,
        "by_category": {
            k: dict(total=v["total"], ok=v["ok"],
                    rate=round(v["ok"] / v["total"], 3))
            for k, v in by_category.items()
        },
        "details": details,
        "all_passed": all(d["ok"] for d in details),
    }

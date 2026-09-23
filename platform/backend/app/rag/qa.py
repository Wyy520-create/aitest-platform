"""RAG 问答链：检索 -> 组 Prompt -> LLM 生成（无 key 降级为检索直出）。

拒答机制：知识库外的问题（相关度得分率低于阈值）直接回答"知识库无法回答"，
而不是让模型自由发挥——幻觉防护是 RAG 质量的底线。
"""
from ..ai.llm import get_llm
from .knowledge import get_index
from . import REFUSE_THRESHOLD

SYSTEM_PROMPT = """你是 aitest-platform 的测试领域问答助手。
规则：
1. 只依据给定的知识片段回答，不要编造片段里没有的内容。
2. 片段不足以回答时，明确说"知识库中没有足够信息"。
3. 用中文简洁回答，句末标注引用来源（片段标题）。"""

USER_PROMPT_TMPL = """知识片段：
{context}

用户问题：{question}"""


def ask(question: str, top_k: int = 3) -> dict:
    """完整问答：返回 answer + 引用片段 + 是否拒答 + 相关度得分率（供评测）。"""
    index = get_index()
    hits = index.search(question, top_k=top_k)
    # 拒答判定用「得分率」= 绝对分 / 该查询理论满分：BM25 绝对分与查询
    # 长度正相关（长查询 10 分正常、短查询 3 分也可能是高质量命中），
    # 除以 ideal 后跨查询长度可比，阈值才有意义。见 bm25.py.ideal_score。
    ideal = index.ideal_score(question)
    top_score = round((hits[0][1] / ideal) if hits and ideal else 0.0, 3)

    if top_score < REFUSE_THRESHOLD:
        return {
            "answer": "知识库中没有与该问题相关的内容，无法回答。",
            "refused": True,
            "llm": "rule",
            "citations": [],
            "top_score": top_score,
        }

    citations = [{"title": d.title, "source": d.source,
                  "score": round(s / ideal, 3), "snippet": d.content[:160]} for d, s in hits]

    context = "\n\n".join(f"[{i+1}] {d.title}\n{d.content}" for i, (d, s) in enumerate(hits))
    llm = get_llm()
    if llm.name == "mock":
        # 无 key 降级：不硬造回答，直接把最相关片段"检索直出"。
        # 这本身是可用的问答形态（图书馆式），且诚实标注了生成器身份。
        best = hits[0][0]
        answer = (f"（检索直出模式，未接 LLM）\n"
                  f"根据知识片段「{best.title}」：\n{best.content}")
        llm_name = "mock(检索直出)"
    else:
        answer = llm.chat(SYSTEM_PROMPT, USER_PROMPT_TMPL.format(
            context=context, question=question))
        llm_name = llm.name

    return {
        "answer": answer,
        "refused": False,
        "llm": llm_name,
        "citations": citations,
        "top_score": round(top_score, 2),
    }

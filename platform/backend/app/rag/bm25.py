"""自实现 BM25 检索器（零第三方依赖）。

BM25 是工业界最常用的稀疏检索算法（Elasticsearch 默认打分）。
公式: score(q, d) = Σ IDF(qi) * (f(qi,d)*(k1+1)) / (f(qi,d) + k1*(1-b+b*|d|/avgdl))

中文分词策略：不依赖 jieba 等分词库，用「英文按词 + 中文按字符 bigram」
——中文单字歧义大，相邻两字组词能力接近浅层分词，是嵌入式检索的
经典免依赖方案（面试点：如何在无分词环境下做中文 BM25）。
"""
import math
import re
from collections import Counter
from dataclasses import dataclass, field

# 经验参数：k1 控制词频饱和（1.2~2.0），b 控制文档长度归一化强度（0.75 通用）
K1 = 1.5
B = 0.75

_WORD_RE = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """英文/数字按整词，中文先拆单字再做相邻 bigram。

    例: "越权漏洞bug" -> ["越权", "权漏", "漏洞", "bug"]
    bigram 让"越权"这种双字词在 query 与文档间形成交集。
    """
    tokens: list[str] = []
    chars = [m.group() for m in _WORD_RE.finditer(text)]
    prev_cjk = None
    for t in chars:
        if len(t) > 1 or not re.match(r"[\u4e00-\u9fff]", t):
            tokens.append(t.lower())
            prev_cjk = None
        else:
            if prev_cjk:
                tokens.append(prev_cjk + t)  # 中文 bigram
            prev_cjk = t
    return tokens


@dataclass
class Doc:
    title: str          # 片段标题（引用来源展示给用户）
    source: str         # 出处文件
    content: str        # 片段正文
    terms: list[str] = field(default_factory=list, repr=False)
    tf: Counter = field(default_factory=Counter, repr=False)
    length: int = 0


class BM25Index:
    """建一次索引，多次检索（线程安全读）。"""

    def __init__(self, docs: list[dict]):
        self.docs: list[Doc] = []
        for d in docs:
            doc = Doc(title=d["title"], source=d["source"], content=d["content"])
            doc.terms = tokenize(f"{d['title']} {d['content']}")
            doc.tf = Counter(doc.terms)
            doc.length = len(doc.terms)
            self.docs.append(doc)

        self.n = len(self.docs)
        self.avgdl = (sum(d.length for d in self.docs) / self.n) if self.n else 0
        self.df: Counter = Counter()
        for doc in self.docs:
            self.df.update(set(doc.terms))

    def _idf(self, term: str) -> float:
        """标准 BM25 IDF（带平滑，避免负值）。"""
        return math.log((self.n - self.df[term] + 0.5) / (self.df[term] + 0.5) + 1)

    def search(self, query: str, top_k: int = 3) -> list[tuple[Doc, float]]:
        """返回 [(doc, score)] 按 score 降序，只保留 top_k。"""
        q_terms = tokenize(query)
        scored = []
        for doc in self.docs:
            score = 0.0
            for t in q_terms:
                f = doc.tf.get(t, 0)
                if not f:
                    continue
                norm = f * (K1 + 1) / (f + K1 * (1 - B + B * doc.length / self.avgdl))
                score += self._idf(t) * norm
            scored.append((doc, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def ideal_score(self, query: str) -> float:
        """该查询的 BM25 理论满分：每个 token 都在最强文档中词频饱和 (f→∞)。
        单 token 贡献上限 = IDF * (k1+1)（与具体文档无关），对查询 tokens 求和即可。

        用途：把绝对分归一化成「得分率」score/ideal ∈ (0,1)。
        踩坑背景：BM25 绝对分与查询长度正相关——长查询 10 分正常、短查询
        3 分也可能是高质量命中。实测 8 字口语查询"秒杀为什么超卖" raw=4.1，
        与拒答类问题（"帮我写股票预测代码" raw=4.1）完全重叠，绝对阈值无解；
        得分率跨查询长度可比，拒答阈值才有意义（见 rag/__init__.py）。
        """
        return sum(self._idf(t) for t in tokenize(query)) * (K1 + 1)

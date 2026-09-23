"""知识库：把项目文档切成自包含的知识片段（chunk）。

切片策略：markdown 按 `##` 二级标题切块——每节在写作时就要求自包含
（见 RAG_KNOWLEDGE.md 开头说明），单独被召回即可读。
"""
from functools import lru_cache
from pathlib import Path

from ..config import KNOWLEDGE_DIR
from .bm25 import BM25Index

# 语料清单：顺序即优先级说明。RAG_KNOWLEDGE.md 是领域知识主语料，
# BUGS.md 是缺陷事实语料。
# 注意：README.md 刻意不进语料——它是变动最频繁的导航文档（重写一次
# 就漂移一次评测分数），检索语料必须"稳定 + 自包含"，本地/容器/CI
# 三端评测输入才能完全一致（曾因容器多拷了一份 README 导致 MRR 与
# 本地不一致，属"环境差异导致评测不可比"的坏味道）。
DOC_FILES = [
    "RAG_KNOWLEDGE.md",
    "BUGS.md",
]


def load_chunks() -> list[dict]:
    """扫描语料目录，按 ## 标题切片。返回 [{title, source, content}]。"""
    chunks: list[dict] = []
    for name in DOC_FILES:
        path = Path(KNOWLEDGE_DIR) / name
        if not path.exists():
            continue  # 语料缺失不致命（比如裁剪部署），只是召回少一路
        lines = path.read_text(encoding="utf-8").splitlines()
        current_title, buf = None, []
        for line in lines:
            if line.startswith("## "):
                if current_title is not None and buf:
                    chunks.append(dict(
                        title=current_title, source=name,
                        content="\n".join(buf).strip(),
                    ))
                current_title, buf = line[3:].strip(), []
            elif current_title is not None:
                buf.append(line)
        if current_title is not None and buf:
            chunks.append(dict(
                title=current_title, source=name,
                content="\n".join(buf).strip(),
            ))
    return chunks


@lru_cache(maxsize=1)
def get_index() -> BM25Index:
    """进程级单例索引。文档改动后重启进程生效（lru_cache 天然的热更新边界）。"""
    return BM25Index(load_chunks())

"""RAG 问答接口。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..rag.qa import ask
from ..rag.evaluator import evaluate
from ..security import get_current_user

router = APIRouter(prefix="/api/qa", tags=["RAG 问答"])


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=256)


@router.post("/ask")
def do_ask(payload: AskIn, _=Depends(get_current_user)):
    """RAG 问答：检索知识库 -> LLM 基于片段作答（无 key 降级检索直出）。"""
    return ask(payload.question)


@router.get("/eval")
def run_eval(_=Depends(get_current_user)):
    """跑 6 类场景评测集，返回检索层质量指标（CI 也跑同一份逻辑）。"""
    return evaluate()

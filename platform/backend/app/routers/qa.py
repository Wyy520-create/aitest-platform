"""RAG 问答接口。"""
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..rag.qa import ask
from ..rag.evaluator import evaluate
from ..ai.llm import upstream_error
from ..security import get_current_user

router = APIRouter(prefix="/api/qa", tags=["RAG 问答"])


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=256)


@router.post("/ask")
def do_ask(payload: AskIn, _=Depends(get_current_user)):
    """RAG 问答：检索知识库 -> LLM 基于片段作答（无 key 降级检索直出）。"""
    try:
        return ask(payload.question)
    except requests.HTTPError as e:
        # 与 /api/ai/generate 同理：上游 LLM 故障透传 502 + 真实消息。
        raise HTTPException(status_code=502, detail=upstream_error(e))


@router.get("/eval")
def run_eval(_=Depends(get_current_user)):
    """跑 7 类场景评测集，返回检索层质量指标（CI 也跑同一份逻辑）。"""
    return evaluate()

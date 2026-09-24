"""AI 工作台接口。"""
import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import ConfigCase
from ..ai.case_generator import generate_and_save
from ..ai.llm import upstream_error
from ..security import get_current_user

router = APIRouter(prefix="/api/ai", tags=["AI 工作台"])


@router.post("/generate")
def generate(_=Depends(get_current_user)):
    """触发一次 AI 用例生成。生成的用例 status=draft，等待人工评审。"""
    try:
        return generate_and_save()
    except requests.HTTPError as e:
        # 上游 LLM 故障透传成 502 + 真实错误消息（key 失效/余额不足/网络
        # 问题一眼区分），而不是笼统 500——见 llm.upstream_error。
        raise HTTPException(status_code=502, detail=upstream_error(e))


@router.get("/stats")
def stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """AI 用例采纳率统计——"度量 AI 而不只是使用 AI"的落地。"""
    rows = (db.query(ConfigCase.source, ConfigCase.status, func.count())
            .filter(ConfigCase.source == "ai")
            .group_by(ConfigCase.status).all())
    result = {"draft": 0, "reviewed": 0, "rejected": 0}
    for _, status, count in rows:
        result[status] = count
    total = result["reviewed"] + result["rejected"]
    result["acceptance_rate"] = (
        round(result["reviewed"] / total * 100, 1) if total else None
    )
    return result

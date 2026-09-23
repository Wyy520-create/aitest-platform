"""AI 工作台接口。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import ConfigCase
from ..ai.case_generator import generate_and_save
from ..security import get_current_user

router = APIRouter(prefix="/api/ai", tags=["AI 工作台"])


@router.post("/generate")
def generate(_=Depends(get_current_user)):
    """触发一次 AI 用例生成。生成的用例 status=draft，等待人工评审。"""
    return generate_and_save()


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

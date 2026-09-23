"""看板：首页统计数据。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Execution, ConfigCase
from ..security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["看板"])


@router.get("")
def overview(db: Session = Depends(get_db), _=Depends(get_current_user)):
    execs = db.query(Execution).order_by(Execution.id.desc()).limit(50).all()
    cases = db.query(ConfigCase).all()

    return {
        "executions_total": len(execs),
        "last_execution": ({
            "id": execs[0].id, "status": execs[0].status,
            "passed": execs[0].passed, "failed": execs[0].failed,
            "bug_found": execs[0].bug_found,
        } if execs else None),
        # 趋势数据（近 N 次，时间正序，给 ECharts 折线图）
        "trend": [{
            "id": e.id, "passed": e.passed, "failed": e.failed,
            "bug_found": e.bug_found, "duration": round(e.duration, 1),
        } for e in reversed(execs[:15])],
        "cases": {
            "total": len(cases),
            "ai_draft": sum(1 for c in cases if c.source == "ai" and c.status == "draft"),
            "reviewed": sum(1 for c in cases if c.status == "reviewed"),
        },
        "bug_found_total": sum(e.bug_found for e in execs),
    }

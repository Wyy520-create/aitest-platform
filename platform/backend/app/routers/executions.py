"""执行管理：触发执行 / 查询状态 / 查询结果。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Execution, ExecutionResult
from ..runner import start_execution
from ..security import get_current_user

router = APIRouter(prefix="/api/executions", tags=["执行管理"])


class StartIn(BaseModel):
    exec_type: str = "suite"      # suite=跑pytest套件 / config=跑配置化用例
    case_ids: list[int] | None = None
    trigger: str = "manual"


class ExecutionOut(BaseModel):
    id: int
    trigger: str
    exec_type: str
    status: str
    total: int
    passed: int
    failed: int
    bug_found: int
    duration: float
    started_at: datetime
    finished_at: datetime | None


class ResultOut(BaseModel):
    id: int
    case_name: str
    outcome: str
    duration: float
    message: str
    is_bug_detection: int


@router.post("", response_model=ExecutionOut, status_code=201)
def start(payload: StartIn, db: Session = Depends(get_db),
          _=Depends(get_current_user)):
    """触发一次执行。立即返回 running 状态的记录，后台线程干活，前端轮询。"""
    if payload.exec_type not in ("suite", "config"):
        raise HTTPException(422, "exec_type 必须是 suite 或 config")

    exec_rec = Execution(trigger=payload.trigger, exec_type=payload.exec_type,
                         status="running")
    db.add(exec_rec)
    db.commit()
    db.refresh(exec_rec)

    start_execution(exec_rec.id, payload.exec_type, payload.case_ids)
    return _to_out(exec_rec)


def _to_out(e: Execution) -> ExecutionOut:
    return ExecutionOut(
        id=e.id, trigger=e.trigger, exec_type=e.exec_type, status=e.status,
        total=e.total, passed=e.passed, failed=e.failed, bug_found=e.bug_found,
        duration=e.duration, started_at=e.started_at, finished_at=e.finished_at,
    )


@router.get("", response_model=list[ExecutionOut])
def list_executions(limit: int = 20, db: Session = Depends(get_db),
                    _=Depends(get_current_user)):
    rows = db.query(Execution).order_by(Execution.id.desc()).limit(limit).all()
    return [_to_out(e) for e in rows]


@router.get("/{execution_id}", response_model=ExecutionOut)
def get_execution(execution_id: int, db: Session = Depends(get_db),
                  _=Depends(get_current_user)):
    e = db.get(Execution, execution_id)
    if e is None:
        raise HTTPException(404, "执行记录不存在")
    return _to_out(e)


@router.get("/{execution_id}/results", response_model=list[ResultOut])
def get_results(execution_id: int, db: Session = Depends(get_db),
                _=Depends(get_current_user)):
    rows = (db.query(ExecutionResult)
            .filter(ExecutionResult.execution_id == execution_id)
            .order_by(ExecutionResult.id)
            .all())
    return [ResultOut(id=r.id, case_name=r.case_name, outcome=r.outcome,
                      duration=r.duration, message=r.message,
                      is_bug_detection=r.is_bug_detection) for r in rows]

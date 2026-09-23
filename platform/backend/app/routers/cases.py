"""配置化用例管理：CRUD + 评审流。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models import ConfigCase
from ..security import get_current_user

router = APIRouter(prefix="/api/cases", tags=["用例管理"])


class CaseIn(BaseModel):
    name: str = Field(max_length=128)
    module: str = "general"
    request: dict          # {"method","path","headers","body","auth"}
    expect: dict = {}      # {"status_code","json_contains"}


class CaseOut(BaseModel):
    id: int
    name: str
    module: str
    source: str
    status: str
    request: dict
    expect: dict
    review_note: str
    created_at: datetime


class ReviewIn(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    note: str = ""


def _to_out(c: ConfigCase) -> CaseOut:
    return CaseOut(
        id=c.id, name=c.name, module=c.module, source=c.source, status=c.status,
        request=json.loads(c.request_json), expect=json.loads(c.expect_json or "{}"),
        review_note=c.review_note, created_at=c.created_at,
    )


@router.get("", response_model=list[CaseOut])
def list_cases(status: str = None, source: str = None,
               db: Session = Depends(get_db), _=Depends(get_current_user)):
    query = db.query(ConfigCase)
    if status:
        query = query.filter(ConfigCase.status == status)
    if source:
        query = query.filter(ConfigCase.source == source)
    return [_to_out(c) for c in query.order_by(ConfigCase.id.desc()).all()]


@router.post("", response_model=CaseOut, status_code=201)
def create_case(payload: CaseIn, db: Session = Depends(get_db),
                _=Depends(get_current_user)):
    _validate_request(payload.request)
    case = ConfigCase(
        name=payload.name, module=payload.module, source="manual", status="reviewed",
        request_json=json.dumps(payload.request, ensure_ascii=False),
        expect_json=json.dumps(payload.expect, ensure_ascii=False),
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return _to_out(case)


def _validate_request(request: dict):
    if request.get("method") not in ("GET", "POST", "PUT", "DELETE"):
        raise HTTPException(422, "method 必须是 GET/POST/PUT/DELETE")
    if not str(request.get("path", "")).startswith("/"):
        raise HTTPException(422, "path 必须以 / 开头")


@router.put("/{case_id}", response_model=CaseOut)
def update_case(case_id: int, payload: CaseIn,
                db: Session = Depends(get_db), _=Depends(get_current_user)):
    case = db.get(ConfigCase, case_id)
    if case is None:
        raise HTTPException(404, "用例不存在")
    _validate_request(payload.request)
    case.name, case.module = payload.name, payload.module
    case.request_json = json.dumps(payload.request, ensure_ascii=False)
    case.expect_json = json.dumps(payload.expect, ensure_ascii=False)
    db.commit()
    db.refresh(case)
    return _to_out(case)


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: int, db: Session = Depends(get_db),
                _=Depends(get_current_user)):
    case = db.get(ConfigCase, case_id)
    if case is None:
        raise HTTPException(404, "用例不存在")
    db.delete(case)
    db.commit()


@router.post("/{case_id}/review", response_model=CaseOut)
def review_case(case_id: int, payload: ReviewIn,
                db: Session = Depends(get_db), _=Depends(get_current_user)):
    """评审流：AI 生成的草稿 -> 人工 approve(采纳)/reject(驳回)。

    这是"AI 产出不直接信任"原则的落地：LLM 生成的用例必须过人工门禁。
    """
    case = db.get(ConfigCase, case_id)
    if case is None:
        raise HTTPException(404, "用例不存在")
    if case.status != "draft":
        raise HTTPException(400, f"该用例当前状态 {case.status}，无需评审")
    case.status = "reviewed" if payload.action == "approve" else "rejected"
    case.review_note = payload.note
    db.commit()
    db.refresh(case)
    return _to_out(case)

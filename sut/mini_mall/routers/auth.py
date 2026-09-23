"""用户模块：注册 / 登录 / 查看当前用户。

接口清单（这些路径+方法之后会成为测试引擎的"接口对象层"）：
    POST /api/auth/register   注册
    POST /api/auth/login      登录，返回 JWT
    GET  /api/auth/me         当前用户信息（需要 Bearer Token）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt as pyjwt

from ..database import get_db
from ..models import User
from ..schemas import UserRegister, UserLogin, UserOut, TokenOut
from ..security import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["用户"])

# HTTPBearer：告诉 FastAPI 这个路由组用 "Authorization: Bearer xxx" 头部验票
# 它还会让 /docs 里的接口旁边出现一把小锁，可以点开填 token 调试
bearer = HTTPBearer()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """注册：用户名查重 -> 哈希密码 -> 入库。

    status_code=201：RESTful 惯例，"创建资源成功"用 201 而不是 200。
    """
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        # 400 vs 422：422 是"格式不对"（Pydantic 挡的），400 是"业务规则不允许"
        raise HTTPException(status_code=400, detail="用户名已被注册")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)   # 拿回数据库生成的 id、created_at
    return user


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """登录：验密码 -> 发 JWT 票。

    安全细节：用户不存在和密码错误返回同一个提示——
    不让攻击者通过报错差异"探测"哪些用户名存在（用户枚举攻击）。
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return TokenOut(access_token=create_token(user.id, user.username))


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """鉴权依赖：所有需要登录的接口都声明我，我负责"验票"。

    验票失败的三种情况都翻译成 401：
    - token 过期 / 签名不对 / 格式错误  -> PyJWT 抛异常
    - token 合法但用户已被删除         -> 数据库查不到
    """
    try:
        payload = decode_token(credentials.credentials)
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail="token 无效或已过期")

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


@router.get("/me", response_model=UserOut)
def read_me(me: User = Depends(get_current_user)):
    """当前用户信息。参数里的 Depends(get_current_user) 就是"此接口需要登录"。"""
    return me

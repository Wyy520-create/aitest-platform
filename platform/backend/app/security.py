"""平台鉴权：管理员登录 + JWT（pbkdf2 哈希复用 sut 同款算法）。"""
import hashlib
import hmac
import os
import time

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .config import SECRET_KEY, ADMIN_USER, ADMIN_PASSWORD
from .database import get_db
from .models import User

router = APIRouter(prefix="/api/auth", tags=["平台鉴权"])
bearer = HTTPBearer()

PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                     bytes.fromhex(salt_hex), PBKDF2_ITERATIONS)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except ValueError:
        return False


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def ensure_admin(db: Session):
    """启动时保证管理员存在（密码以环境变量为准，方便运维改密）。"""
    user = db.query(User).filter(User.username == ADMIN_USER).first()
    if user is None:
        db.add(User(username=ADMIN_USER, password_hash=hash_password(ADMIN_PASSWORD)))
        db.commit()
    elif not verify_password(ADMIN_PASSWORD, user.password_hash):
        user.password_hash = hash_password(ADMIN_PASSWORD)  # 环境变量改了密码
        db.commit()


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = jwt.encode(
        {"sub": str(user.id), "username": user.username, "exp": int(time.time()) + 12 * 3600},
        SECRET_KEY, algorithm="HS256",
    )
    return TokenOut(access_token=token)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user

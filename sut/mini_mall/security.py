"""安全模块：密码哈希 + JWT 签发/校验。

为什么手写而不用现成库：校招生能讲清原理 > 会调包。
- pbkdf2_hmac：业界标准的"慢哈希"，循环 10 万次让暴力破解变得不划算
- hmac.compare_digest：常数时间比较，防"逐字节试错"的时序攻击
"""
import hashlib
import hmac
import os
import time

import jwt

from .config import SECRET_KEY, JWT_EXPIRE_MINUTES

# 哈希迭代次数。10 万次在 2026 年的 CPU 上约几十毫秒，登录可接受，爆破很痛苦
PBKDF2_ITERATIONS = 100_000


# ---------- 密码部分 ----------

def hash_password(password: str) -> str:
    """明文 -> "盐$哈希值" 存库格式。每次调用随机生成新盐。"""
    salt = os.urandom(16)                                   # 16 字节随机盐
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    # 存储格式: "盐的hex$哈希的hex"，校验时按 $ 拆开
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验明文密码是否匹配库里存的 "盐$哈希值"。"""
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            bytes.fromhex(salt_hex), PBKDF2_ITERATIONS,
        )
        # 不用 == 而用 compare_digest：== 会在第一个不同的字节提前返回，
        # 攻击者可借此逐字节猜哈希（时序攻击）
        return hmac.compare_digest(digest.hex(), digest_hex)
    except ValueError:
        # 库里的格式不对（被篡改/损坏），一律视为校验失败
        return False


# ---------- JWT 部分 ----------

def create_token(user_id: int, username: str) -> str:
    """签发 JWT。payload 就是"票面上印的信息"：
    - sub: 用户 id（JWT 标准字段，subject）
    - username: 方便日志/前端显示
    - exp: 过期时间戳，超过这个时间验票直接失败
    """
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": int(time.time()) + JWT_EXPIRE_MINUTES * 60,
    }
    # HS256 = 用同一个 SECRET_KEY 既做签名也做校验（对称加密）
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """校验并解出 JWT 载荷。

    - 签名不对 / 过期 / 格式错误都会抛 jwt.PyJWTError 的子类
    - 调用方只需 try/except，把一切异常都翻译成 401
    """
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

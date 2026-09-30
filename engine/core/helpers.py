"""工具函数（core 层）。"""
import random
import string
import uuid


def random_username(prefix: str = "qa") -> str:
    """生成唯一用户名，保证并行及快速连续执行时互不冲突。

    用户名最长 32 位：保留最多 11 位业务前缀，追加 20 位 UUID。
    """
    safe_prefix = prefix[:11]
    return f"{safe_prefix}_{uuid.uuid4().hex[:20]}"


def random_password() -> str:
    """符合契约(6-64位)的随机密码。"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=12))

"""工具函数（core 层）。"""
import random
import string
import time


def random_username(prefix: str = "qa") -> str:
    """生成随机用户名，保证用例之间互不冲突、可重复执行。

    命名习惯：前缀说明来源(qa=自动化)，时间戳+随机数保证唯一。
    """
    tail = f"{int(time.time())}{random.randint(100, 999)}"
    return f"{prefix}_{tail}"


def random_password() -> str:
    """符合契约(6-64位)的随机密码。"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=12))

"""平台配置。全部走环境变量，默认值只用于本地开发。"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("PLATFORM_DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'platform.db'}")
SECRET_KEY = os.getenv("PLATFORM_SECRET_KEY", "platform-dev-secret")

# 平台管理员（本地演示账号，生产环境务必用环境变量覆盖）
ADMIN_USER = os.getenv("PLATFORM_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("PLATFORM_ADMIN_PASSWORD", "admin123")

# 被测系统地址（引擎打它；compose 里是服务名 sut:8000）
SUT_BASE_URL = os.getenv("SUT_BASE_URL", "http://localhost:8000")

# 测试引擎入口（绝对路径，subprocess 用）
ENGINE_RUN = BACKEND_DIR.parent.parent / "engine" / "run.sh"

# LLM 配置：DeepSeek。没配 key 时自动降级为 MockLLM（保证全流程可演示）
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
LLM_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

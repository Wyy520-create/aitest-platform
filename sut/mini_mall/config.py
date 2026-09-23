"""全局配置。

所有"可能会变的东西"集中放这里，不要把配置散落在各个文件里硬编码——
这是工程代码和"课程作业"的第一个区别。
"""
import os

# 数据库连接地址。
# 默认用 SQLite：整个数据库就是当前目录下的一个文件 mini_mall.db，零配置。
# 以后切 MySQL 只需设环境变量，例如：
#   DATABASE_URL="mysql+pymysql://root:123456@localhost:3306/mini_mall"
# 这就是 ORM 的好处：业务代码一行不用改。
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mini_mall.db")

# JWT 签名密钥。生产环境必须通过环境变量注入，绝不能把真实密钥提交到 git。
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key-do-not-use-in-prod")

# 登录态有效期（分钟）：token 发出去 2 小时后自动失效
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

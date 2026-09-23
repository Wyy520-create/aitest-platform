# 平台后端镜像：后端 + 测试引擎合体。
#
# 为什么不拆两个镜像？后端通过 subprocess 调 engine/run.sh 跑套件，
# 两者必须同容器文件系统（或者把 engine 做成独立服务走远程执行——
# 那是后续"动态容器执行"的演进方向）。
#
# 注意：本 Dockerfile 的构建上下文必须是仓库根目录（因为要 COPY engine/），
# 即：docker build -f platform/backend/Dockerfile .
FROM python:3.10-slim

# 容器内布局（与 config.py 的默认相对推导保持一致）：
#   /app/backend/   平台后端（WORKDIR）
#   /app/engine/    测试引擎
WORKDIR /app/backend

# 先只拷 requirements 再装依赖——利用 Docker 层缓存：
# 代码天天改，依赖不常动，改代码不用重装一遍包
COPY engine/requirements.txt /app/engine/requirements.txt
COPY platform/backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir \
    -r /app/engine/requirements.txt \
    -r /app/backend/requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY engine/ /app/engine/
COPY platform/backend/app/ /app/backend/app/
# RAG 知识库语料：只拷 docs/（检索语料）。README.md 刻意不进语料——
# 它变动频繁，拷进容器会使本地/容器评测输入不一致（见 knowledge.py）
COPY docs/ /app/docs/

# 防御 git 权限丢失导致 run.sh 不可执行（subprocess 直接调它）
RUN chmod +x /app/engine/run.sh

# SQLite 落 /data 卷：容器重建，执行历史/用例数据不丢
VOLUME ["/data"]
ENV PLATFORM_DATABASE_URL="sqlite:////data/platform.db"

# 容器布局与本地不同（本地是 <repo>/platform/backend，上两级即 repo 根；
# 容器是 /app/backend，上两级是 /，推导会得出错误路径）——显式声明引擎入口
ENV ENGINE_RUN="/app/engine/run.sh"
ENV KNOWLEDGE_DIR="/app/docs"

EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]

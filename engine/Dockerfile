# 测试引擎镜像：CI 与"一次性容器执行"用（非常驻服务）。
# 用法：docker compose run --rm engine   （打 compose 网络里的 sut）
#      docker run --rm -e SUT_BASE_URL=... engine  （打任意地址的 SUT）
FROM python:3.10-slim

WORKDIR /engine

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

RUN chmod +x run.sh

# run.sh 内部已处理：PYTEST_DISABLE_PLUGIN_AUTOLOAD、SUT_BASE_URL 默认值、
# venv 缺失时退回系统 python——容器与本地行为完全一致
ENTRYPOINT ["./run.sh"]

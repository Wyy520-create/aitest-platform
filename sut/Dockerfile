# 被测系统镜像：mini-mall
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY mini_mall/ ./mini_mall/

# SQLite 数据放卷里，容器重建数据不丢
VOLUME ["/data"]
ENV DATABASE_URL="sqlite:////data/mini_mall.db"

EXPOSE 8000
CMD ["uvicorn", "mini_mall.main:app", "--host", "0.0.0.0", "--port", "8000"]

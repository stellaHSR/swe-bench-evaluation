#!/bin/bash

# 指定你的 FastAPI 应用和 Celery worker 的工作目录
WORKDIR="/path/to/your/fastapi/app"
# 指定虚拟环境的路径
VENV="/path/to/your/venv"

# 激活虚拟环境
source "$VENV/bin/activate"

# 进入工作目录
cd "$WORKDIR"

# 启动 FastAPI 应用，输出重定向到 fastapi.log
echo "Starting FastAPI app..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > fastapi.log 2>&1 &

# 启动 Celery worker，输出重定向到 celery.log
echo "Starting Celery worker..."
nohup celery -A celery_worker.app worker --loglevel=info > celery.log 2>&1 &

echo "Services started."

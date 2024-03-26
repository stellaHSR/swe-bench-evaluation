
# 队列任务管理

- 使用 FastAPI 创建一个简单的 web 服务，用于创建和管理 Celery 任务。

## 安装流程

### 1. 安装所需的库

你需要安装 FastAPI 和 Uvicorn 作为 web 服务器，以及用于队列管理的 Celery，
还需要选择一个后端来存储 Celery 的任务状态和结果，比如这里使用 Redis 作为后端。

```bash
pip install fastapi uvicorn celery[redis] redis
```

### 2. 开启 celery_worker 服务

注意：在运行 celery 之前，确保你已经安装了 Redis 并且 Redis 服务已经启动。（`redis-server /usr/local/etc/redis.conf`）

```bash
celery -A queue_task.celery_worker.app worker --loglevel=info --concurrency=1
```

### 3. 创建 FastAPI 应用

然后，在另一个终端，启动 FastAPI 应用：

```bash
uvicorn queue_task.fastapi_server:app --reload
```

## 使用方法

1. 通过向 `/tasks/` 发送 POST 请求来创建新任务
2. 通过向 `/tasks/{task_id}` 发送 GET 请求来获取任务状态和结果
3. 通过向 `/tasks/` 发送 GET 请求来获取所有任务的状态和结果
4. 通过向 `/tasks/` 发送 DELETE 请求来删除所有任务

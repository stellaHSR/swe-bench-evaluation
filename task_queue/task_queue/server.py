#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/25 19:46
@Author  : alexanderwu
@File    : server.py
"""
import json

from fastapi import FastAPI, HTTPException
from redis import Redis
from pydantic import BaseModel

from task_queue.worker import execute_task
from task_queue.model import BaseTaskQueue
from celery.result import AsyncResult

app = FastAPI()

redis_client = Redis(host='localhost', port=6379, db=0)


class TaskInput(BaseModel):
    """input for task creation"""
    operation: str
    data: dict


class TaskQueueServerImp(BaseTaskQueue):
    """Server Imp"""

    def add_task(self, task_input: TaskInput):
        """create task based on input"""
        if task_input.operation == "square":
            x = task_input.data.get("x")
            if x is None:
                raise HTTPException(status_code=400, detail="Missing 'x' in data")
            task = execute_task.delay(x)
            return {"task_id": task.id}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {task_input.operation}")

    def get_task_status(self, task_id: str):
        """get task based on task_id"""
        task_result = AsyncResult(task_id, app=execute_task.app)
        if task_result.ready():
            return {"status": task_result.status, "result": task_result.result}
        else:
            return {"status": task_result.status}

    def list_tasks(self):
        # 注意: 这里使用的键模式 'celery-task-meta-*' 是基于 Celery 默认配置的
        # 如果你修改了 Celery 的任务结果存储键的模式，你需要相应地更新这里
        keys = redis_client.keys('celery-task-meta-*')
        tasks = []
        for key in keys:
            # 获取任务结果
            task_result_raw = redis_client.get(key)
            if task_result_raw:
                task_result = json.loads(task_result_raw)
                tasks.append(task_result)
        return tasks

    def clear_tasks(self):
        keys = redis_client.keys('celery-task-meta-*')
        for key in keys:
            redis_client.delete(key)
        return {"detail": "All task records cleared."}


imp = TaskQueueServerImp()


@app.post("/tasks/")
async def add_task(task_input: TaskInput):
    """create task based on input"""
    return imp.add_task(task_input)


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """get task based on task_id"""
    return imp.get_task_status(task_id)


@app.get("/tasks/")
async def list_tasks():
    return imp.list_tasks()


@app.delete("/tasks/")
async def clear_tasks():
    return imp.clear_tasks()

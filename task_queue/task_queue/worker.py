#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/25 19:48
@Author  : alexanderwu
@File    : worker.py
"""

from celery import Celery

# 配置 Celery 使用 Redis 作为消息代理
app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')


@app.task
def execute_task(x):
    # 模拟一个耗时的计算任务
    import time
    time.sleep(5)
    return (x, x * x)

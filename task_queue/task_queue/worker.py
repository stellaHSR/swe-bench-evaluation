#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/25 19:48
@Author  : alexanderwu
@File    : worker.py
"""
import os
import subprocess
from celery import Celery

from metrics.report import get_model_report

# 配置 Celery 使用 Redis 作为消息代理
app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')


@app.task
def execute_task(x):
    # 模拟一个耗时的计算任务
    import time
    time.sleep(5)
    os.chdir("/evaluation/harness")
    os.system(". run_eval.sh")
    # result = get_model_report(model="", predictions_path="", swe_bench_tasks="", log_dir="")
    # todo update result to redis
    # return result
    return x

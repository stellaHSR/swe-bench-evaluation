#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/25 19:48
@Author  : alexanderwu
@File    : worker.py
"""
import os
import redis
import subprocess
from celery import Celery

# from metrics.report import get_model_report

# 配置 Celery 使用 Redis 作为消息代理
app = Celery('tasks', broker='redis://lcoalhost:6379/0', backend='redis://lcoalhost:6379/0')
# 创建Redis连接（用于直接操作Redis）
redis_client = redis.Redis(host="localhost", port=6379, db=0)

import runpy
import sys

from loguru import logger

@app.task
def execute_task(x):
    print("Run bash")
    import time
    time.sleep(5)
    try:
        # 切换到脚本所在的目录
        os.chdir("/evaluation/harness")
        # # 使用subprocess.run代替os.system更安全地执行命令
        # result = subprocess.run(["./run_eval.sh"], capture_output=True, text=True, check=True)
        #
        # # 假设脚本的输出是我们需要的结果，你可以根据需要调整
        # output = result.stdout
        logger.info(f"enter evaluation dir {os.getcwd()}")
        original_argv = sys.argv.copy()

        try:
            # 设置你想要传递给脚本的命令行参数
            sys.argv = ["local_engine_evaluation.py", "--predictions_path",
                        f"/evaluation/predictions/result.json",
                        "--log_dir", "/evaluation/log",
                        "--testbed", "/repos",
                        "--venv", "scikit-learn__scikit-learn__0.22",
                        "--timeout", "900",
                        "--instance_id", "scikit-learn__scikit-learn-11578",
                        "--path_conda", "/data/conda"
                        ]
            # 执行脚本
            runpy.run_path(path_name="local_engine_evaluation.py", run_name="__main__")
            logger.info("start run")
        finally:
            # 恢复原始的sys.argv以避免对后续代码的潜在影响
            sys.argv = original_argv
        
        # 模拟结果更新到Redis
        # 这里假设x是任务的唯一标识符，可以根据实际情况调整键名
        redis_key = f"task-result:{x}"
        # redis_client.set(redis_key, output)
        
        # 返回一个结果标识符，客户端可以用它来查询具体结果
        return redis_key
    except subprocess.CalledProcessError as e:
        # 如果脚本执行失败，返回错误信息
        print(e.output)
        return {"error": "脚本执行失败"}


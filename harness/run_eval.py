# -*- coding: utf-8 -*-
# @Author  : stellahong (stellahong@fuzhi.ai)
# @Desc    :
import runpy
import sys

original_argv = sys.argv.copy()

try:
    # 设置你想要传递给脚本的命令行参数
    sys.argv = ["local_engine_evaluation.py", "--predictions_path",
                f"/evaluation/predictions/result.json",
                "--log_dir", "/evaluation/log",
                "--testbed", "/repos",
                "--venv", "scikit-learn__scikit-learn__0.22",
                "--timeout", "900",
                "--path_conda", "/data/conda"
                ]
    # 执行脚本
    runpy.run_path(path_name="local_engine_evaluation.py", run_name="__main__")
finally:
    # 恢复原始的sys.argv以避免对后续代码的潜在影响
    sys.argv = original_argv

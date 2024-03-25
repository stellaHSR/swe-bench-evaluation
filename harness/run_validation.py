# -*- coding: utf-8 -*-
# @Author  : stellahong (stellahong@fuzhi.ai)
# @Desc    :
import runpy
import sys

original_argv = sys.argv.copy()
ids = [
    "scikit-learn__scikit-learn-11578",
    "scikit-learn__scikit-learn-11542",
    "scikit-learn__scikit-learn-10870",
    "scikit-learn__scikit-learn-10459",
    "scikit-learn__scikit-learn-10297",
    "scikit-learn__scikit-learn-10198",
]

try:
    
    # 执行脚本
    import os
    from contextlib import redirect_stdout
    for id in ids:
        # 设置你想要传递给脚本的命令行参数
        sys.argv = ["local_engine_evaluation.py",
                    "--instances_path", f"/evaluation/predictions/result.json",
                    "--log_dir", "/evaluation/log",
                    "--testbed", "/repos",
                    "--instance_id", f"{id}",
                    "--timeout", "900",
                    "--path_conda", "/data/conda"
                    ]
        # runpy.run_path(path_name="local_engine_validation.py", run_name="__main__")
        log_file = f"/evaluation/log/{id}_runtime_val.log"
        with open(log_file, "w") as f:
            with redirect_stdout(f):
                runpy.run_path(path_name="local_engine_validation.py", run_name="__main__")
finally:
    # 恢复原始的sys.argv以避免对后续代码的潜在影响
    sys.argv = original_argv

#!/bin/bash
set -x
# 正确定义数组
ids=(
    "scikit-learn__scikit-learn-11578"
    "scikit-learn__scikit-learn-11542"
    "scikit-learn__scikit-learn-10870"
    "scikit-learn__scikit-learn-10459"
    "scikit-learn__scikit-learn-10297"
    "scikit-learn__scikit-learn-10198"
)

model="gpt-4-turbo-preview"
# 遍历数组
for id in "${ids[@]}"; do
    # 构建日志文件路径
    log_file="/evaluation/log/${id}_${model}_runtime_val.log"

    # 执行 Python 脚本并重定向输出到日志文件
    python local_engine_evaluation.py \
        --predictions_path "/evaluation/predictions/result.json" \
        --log_dir "/evaluation/log" \
        --testbed "/repos" \
        --venv "scikit-learn__scikit-learn__0.20" \
        --instance_id "${id}" \
        --timeout "900" \
        --num_workers "1" \
        --path_conda "/data/conda" > "${log_file}" 2>&1
done
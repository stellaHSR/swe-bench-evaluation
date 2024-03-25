#!/bin/bash
python run_evaluation.py \
    --predictions_path "F:\deepWisdom\metaGPT\SWE-DI\MetaGPT\swe_bench\inference\outputs\react_mode\gpt-4-turbo-preview__SWE-bench_oracle__test.jsonl" \
    --swe_bench_tasks "<path to `swe-bench.json`>" \
    --log_dir "F:\deepWisdom\metaGPT\SWE-bench\log" \
    --testbed "F:\deepWisdom\metaGPT\SWE-DI\MetaGPT\data\repos\scikit-learn__scikit-learn" \
    --skip_existing \
    --timeout 900 \
    --verbose

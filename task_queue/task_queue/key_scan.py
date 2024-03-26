# -*- coding: utf-8 -*-
# @Author  : stellahong (stellahong@fuzhi.ai)
# @Desc    :
import redis
import json

# 创建Redis连接
redis_client = redis.Redis(host='192.168.50.74', port=32582, password='Onelawgpt321!')

# 自定义键模式，如果你更改了Celery配置
custom_pattern = 'celery-task-meta-*'  # 根据需要调整这里

# 初始化游标
cursor = 0

# 存储匹配到的键
keys_found = []

# 使用SCAN命令迭代查找匹配的键
while True:
    cursor, keys = redis_client.scan(cursor=cursor, match=custom_pattern, count=1000)
    keys_found.extend(keys)
    # 如果游标返回0，说明迭代结束
    if cursor == 0:
        break

# 存储任务结果
tasks_results = []

# 遍历找到的键并获取结果
for key in keys_found:
    task_result_raw = redis_client.get(key)
    if task_result_raw:
        # 假设结果是JSON格式存储
        try:
            task_result = json.loads(task_result_raw.decode('utf-8'))
            tasks_results.append(task_result)
        except json.JSONDecodeError:
            print(f"解析失败: 键 {key}")

# 输出任务结果
for result in tasks_results:
    print(result)

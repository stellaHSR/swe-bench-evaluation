#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/26 13:46
@Author  : alexanderwu
@File    : model.py
"""

from abc import ABC, abstractmethod


class BaseTaskQueue(ABC):
    """任务队列的抽象基类"""

    @abstractmethod
    def add_task(self, task_data):
        """添加一个新的任务"""

    @abstractmethod
    def get_task_status(self, task_id):
        """获取指定任务的状态"""

    @abstractmethod
    def list_tasks(self):
        """列出所有任务"""

    @abstractmethod
    def clear_tasks(self):
        """清除所有任务记录"""

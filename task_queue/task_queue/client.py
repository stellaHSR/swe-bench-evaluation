#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/26 13:59
@Author  : alexanderwu
@File    : client.py
"""

import requests
from task_queue.model import BaseTaskQueue


API_BASE_URL = "http://localhost:8000"


class TaskQueueClientImp(BaseTaskQueue):
    def __init__(self, server_url):
        self.server_url = server_url

    def _send_request(self, method, path, payload=None):
        url = f"{self.server_url}{path}"
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=payload)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
        else:
            raise ValueError("Unsupported HTTP method")
        return response.json()

    def add_task(self, task_data):
        return self._send_request("POST", "/tasks/", task_data)

    def get_task_status(self, task_id):
        return self._send_request("GET", f"/tasks/{task_id}")

    def list_tasks(self):
        return self._send_request("GET", "/tasks/")

    def clear_tasks(self):
        return self._send_request("DELETE", "/tasks/")


if __name__ == '__main__':
    client = TaskQueueClientImp(API_BASE_URL)
    print(client.list_tasks())
    print(client.add_task({"operation": "square", "data": {"x": 10}}))
    print(client.list_tasks())
    print(client.get_task_status("1"))
    print(client.clear_tasks())
    print(client.list_tasks())

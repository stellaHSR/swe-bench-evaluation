#!/usr/bin/env bash

celery -A task_queue.worker.app worker --loglevel=info --concurrency=1

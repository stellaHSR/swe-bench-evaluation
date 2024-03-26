#!/usr/bin/env bash

celery -A task_queue.celery_worker.app worker --loglevel=info --concurrency=1
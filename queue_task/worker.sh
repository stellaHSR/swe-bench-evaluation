#!/usr/bin/env bash

celery -A queue_task.celery_worker.app worker --loglevel=info --concurrency=1
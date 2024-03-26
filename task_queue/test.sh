#!/usr/bin/env bash

curl -X 'POST' \
  'http://localhost:8000/tasks/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "operation": "square",
  "data": {"x": 10}
}'

#curl -X 'GET' \
#  'http://localhost:8000/tasks/<task_id>' \
#  -H 'accept: application/json'

curl -X 'GET' \
  'http://localhost:8000/tasks/' \
  -H 'accept: application/json'

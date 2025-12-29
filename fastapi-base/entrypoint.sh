#!/bin/sh

if [ "$DEBUG" = "true" ]; then
    pip install -r requirements-local.txt
    exec uvicorn app.main:app --host 0.0.0.0 --port 7777 
else
    pip install -r requirements-local.txt
    # Use 1 worker to enable OpenAPI schema caching (development mode)
    # For production with high traffic, increase workers and disable docs
    exec gunicorn app.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 4 --timeout 120 --keep-alive 5 --bind 0.0.0.0:7777
fi

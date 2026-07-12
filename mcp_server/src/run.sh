#!/bin/bash
# Entrypoint for AWS Lambda Web Adapter. LWA proxies HTTP requests to $PORT.
exec python -m uvicorn app:asgi_app --host 0.0.0.0 --port ${PORT:-8080} --log-level info

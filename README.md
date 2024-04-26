# celery-curl
Do curl mainly for GPTs

# start worker
python -m celery -A celerycurl.celerytasks worker -l info --concurrency=2 -P threads

# start worker monitor
python -m celery -A celerycurl.celerytasks flower --url_prefix=flower --port=5555

# start rest api wrapper
python -m uvicorn celerycurl:fastapi.fastapp --host 0.0.0.0 --port 8080
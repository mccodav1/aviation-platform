import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
timeout = 30

# Both logs to stdout/stderr, so `docker compose logs web` shows them.
accesslog = "-"
errorlog = "-"
# Requests always arrive via nginx, so log the real client address it
# forwards rather than nginx's own container IP.
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

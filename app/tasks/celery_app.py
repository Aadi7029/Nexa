# app/tasks/celery_app.py
from celery import Celery
from ..core.config import settings

celery = Celery(
    "nexa_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        # task modules present in this project
        "app.tasks.worker_tasks",
        "app.tasks.enqueue",
        "app.tasks.wrappers",
    ],
)

celery.conf.task_default_queue = "nexa_default"


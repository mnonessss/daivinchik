import os
from datetime import timedelta

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://guest:guest@rabbitmq:5672//",
)
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://redis:6379/1",
)

celery_app = Celery(
    "dating_bot",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "recalculate-rankings-every-10-minutes": {
            "task": "tasks.recalculate_all_rankings",
            "schedule": timedelta(minutes=10),
        }
    },
)

import os
from celery import Celery
from kombu import Queue

# Celery 브로커 및 백엔드 URL 설정
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Celery 앱 생성
celery_app = Celery(
    "streamlit_platform",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.docker_tasks",
        "app.tasks.deployment_tasks",
    ],
)

# Celery 설정
celery_app.conf.update(
    # 태스크 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    # 결과 백엔드 설정
    result_expires=3600,  # 1시간 후 결과 만료
    result_backend_transport_options={
        "master_name": "mymaster",
    },
    # 워커 설정
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    # 큐 설정
    task_routes={
        "app.tasks.docker_tasks.build_image_task": {"queue": "docker_heavy"},
        "app.tasks.docker_tasks.deploy_app_task": {"queue": "docker_heavy"},
        "app.tasks.deployment_tasks.cleanup_task": {"queue": "maintenance"},
    },
    # 큐 정의
    task_queues=(
        Queue("docker_heavy", routing_key="docker_heavy"),
        Queue("maintenance", routing_key="maintenance"),
        Queue("default", routing_key="default"),
    ),
    # 기본 큐
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    # 재시도 설정
    task_retry_delay=60,  # 60초 후 재시도
    task_max_retries=3,
    # 모니터링
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# 태스크 자동 발견
celery_app.autodiscover_tasks()

if __name__ == "__main__":
    celery_app.start()

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
import logging

from routers.auth import get_current_user
from models import User

router = APIRouter(tags=["celery-monitor"])
logger = logging.getLogger(__name__)


@router.get("/workers")
async def get_celery_workers(current_user: User = Depends(get_current_user)):
    """Celery 워커 상태 조회"""
    try:
        from app.celery_app import celery_app

        # 활성 워커 조회
        inspect = celery_app.control.inspect()

        # 워커 상태 정보
        stats = inspect.stats() or {}
        active_tasks = inspect.active() or {}
        scheduled_tasks = inspect.scheduled() or {}
        reserved_tasks = inspect.reserved() or {}

        workers_info = []

        for worker_name in stats.keys():
            worker_stats = stats.get(worker_name, {})
            worker_info = {
                "name": worker_name,
                "status": "online" if worker_name in stats else "offline",
                "active_tasks": len(active_tasks.get(worker_name, [])),
                "scheduled_tasks": len(scheduled_tasks.get(worker_name, [])),
                "reserved_tasks": len(reserved_tasks.get(worker_name, [])),
                "total_tasks": worker_stats.get("total", {}),
                "pool": worker_stats.get("pool", {}),
                "rusage": worker_stats.get("rusage", {}),
            }
            workers_info.append(worker_info)

        return {
            "workers": workers_info,
            "total_workers": len(workers_info),
            "online_workers": len([w for w in workers_info if w["status"] == "online"]),
        }

    except Exception as e:
        logger.error(f"Celery 워커 상태 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"워커 상태 조회 실패: {str(e)}")


@router.get("/queues")
async def get_celery_queues(current_user: User = Depends(get_current_user)):
    """Celery 큐 상태 조회"""
    try:
        from app.celery_app import celery_app

        inspect = celery_app.control.inspect()

        # 큐별 대기 중인 태스크 수 조회
        active_queues = inspect.active_queues() or {}

        queues_info = []

        # 설정된 큐 목록
        configured_queues = ["docker_heavy", "maintenance", "default"]

        for queue_name in configured_queues:
            queue_info = {
                "name": queue_name,
                "workers": [],
                "total_tasks": 0,
            }

            # 각 워커에서 이 큐를 처리하는지 확인
            for worker_name, worker_queues in active_queues.items():
                for queue_data in worker_queues:
                    if queue_data.get("name") == queue_name:
                        queue_info["workers"].append(worker_name)

            queues_info.append(queue_info)

        return {
            "queues": queues_info,
            "total_queues": len(queues_info),
        }

    except Exception as e:
        logger.error(f"Celery 큐 상태 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"큐 상태 조회 실패: {str(e)}")


@router.get("/tasks/active")
async def get_active_tasks(current_user: User = Depends(get_current_user)):
    """현재 실행 중인 태스크 조회 (Celery inspect + Redis 결합)"""
    try:
        from app.celery_app import celery_app
        import redis
        import json
        from datetime import datetime

        # Celery inspect를 통한 활성 태스크 조회
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active() or {}

        # Redis를 통한 태스크 상태 조회
        redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

        all_tasks = []

        # Celery inspect 결과 처리
        for worker_name, tasks in active_tasks.items():
            for task in tasks:
                task_id = task.get("id")

                # Redis에서 태스크 상태 정보 조회
                task_result = None
                task_state = "UNKNOWN"
                task_meta = {}

                try:
                    # Celery 결과 키 패턴: celery-task-meta-{task_id}
                    result_key = f"celery-task-meta-{task_id}"
                    result_data = redis_client.get(result_key)

                    if result_data:
                        task_result = json.loads(result_data)
                        task_state = task_result.get("status", "UNKNOWN")
                        task_meta = task_result.get("result", {})
                except Exception as redis_error:
                    logger.warning(f"Redis에서 태스크 {task_id} 정보 조회 실패: {redis_error}")

                task_info = {
                    "id": task_id,
                    "worker": worker_name,
                    "name": task.get("name"),
                    "state": task_state,
                    "args": task.get("args", []),
                    "kwargs": task.get("kwargs", {}),
                    "time_start": task.get("time_start"),
                    "acknowledged": task.get("acknowledged"),
                    "delivery_info": task.get("delivery_info", {}),
                    "result": task_meta,
                    "runtime": None,
                }

                # 실행 시간 계산
                if task.get("time_start"):
                    try:
                        start_time = datetime.fromtimestamp(task.get("time_start"))
                        runtime = (datetime.now() - start_time).total_seconds()
                        task_info["runtime"] = runtime
                    except:
                        pass

                all_tasks.append(task_info)

        # Redis에서 추가 태스크 정보 조회 (inspect에서 놓친 것들)
        try:
            # Redis에서 모든 태스크 키 조회
            task_keys = redis_client.keys("celery-task-meta-*")

            for key in task_keys:
                task_id = key.replace("celery-task-meta-", "")

                # 이미 처리된 태스크는 건너뛰기
                if any(task["id"] == task_id for task in all_tasks):
                    continue

                try:
                    result_data = redis_client.get(key)
                    if result_data:
                        task_result = json.loads(result_data)
                        task_state = task_result.get("status", "UNKNOWN")

                        # PROGRESS 상태인 태스크만 추가 (실행 중인 것들)
                        if task_state in ["PROGRESS", "PENDING"]:
                            task_meta = task_result.get("result", {})

                            task_info = {
                                "id": task_id,
                                "worker": "unknown",
                                "name": task_result.get("task_name", "unknown"),
                                "state": task_state,
                                "args": [],
                                "kwargs": {},
                                "time_start": None,
                                "acknowledged": True,
                                "delivery_info": {},
                                "result": task_meta,
                                "runtime": None,
                            }

                            all_tasks.append(task_info)

                except Exception as task_error:
                    logger.warning(f"태스크 {task_id} 정보 처리 실패: {task_error}")

        except Exception as redis_scan_error:
            logger.warning(f"Redis 태스크 스캔 실패: {redis_scan_error}")

        return {
            "active_tasks": all_tasks,
            "total_active": len(all_tasks),
        }

    except Exception as e:
        logger.error(f"활성 태스크 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"활성 태스크 조회 실패: {str(e)}")


@router.get("/tasks/scheduled")
async def get_scheduled_tasks(current_user: User = Depends(get_current_user)):
    """예약된 태스크 조회"""
    try:
        from app.celery_app import celery_app

        inspect = celery_app.control.inspect()
        scheduled_tasks = inspect.scheduled() or {}

        all_tasks = []

        for worker_name, tasks in scheduled_tasks.items():
            for task in tasks:
                task_info = {
                    "worker": worker_name,
                    "task_id": task.get("request", {}).get("id"),
                    "name": task.get("request", {}).get("name"),
                    "eta": task.get("eta"),
                    "priority": task.get("priority"),
                }
                all_tasks.append(task_info)

        return {
            "scheduled_tasks": all_tasks,
            "total_scheduled": len(all_tasks),
        }

    except Exception as e:
        logger.error(f"예약된 태스크 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"예약된 태스크 조회 실패: {str(e)}")


@router.post("/tasks/{task_id}/revoke")
async def revoke_task(task_id: str, current_user: User = Depends(get_current_user)):
    """태스크 취소"""
    try:
        from app.celery_app import celery_app

        # 태스크 취소 (terminate=True로 강제 종료)
        celery_app.control.revoke(task_id, terminate=True)

        return {
            "message": f"태스크 {task_id}가 취소되었습니다.",
            "task_id": task_id,
        }

    except Exception as e:
        logger.error(f"태스크 취소 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"태스크 취소 실패: {str(e)}")


@router.get("/stats")
async def get_celery_stats(current_user: User = Depends(get_current_user)):
    """Celery 전체 통계"""
    try:
        from app.celery_app import celery_app

        inspect = celery_app.control.inspect()

        # 기본 통계
        stats = inspect.stats() or {}
        active_tasks = inspect.active() or {}
        scheduled_tasks = inspect.scheduled() or {}
        reserved_tasks = inspect.reserved() or {}

        total_active = sum(len(tasks) for tasks in active_tasks.values())
        total_scheduled = sum(len(tasks) for tasks in scheduled_tasks.values())
        total_reserved = sum(len(tasks) for tasks in reserved_tasks.values())

        # 워커별 통계
        worker_stats = {}
        for worker_name, worker_data in stats.items():
            worker_stats[worker_name] = {
                "total_tasks": worker_data.get("total", {}),
                "pool_processes": worker_data.get("pool", {}).get("processes", []),
                "pool_max_concurrency": worker_data.get("pool", {}).get("max-concurrency"),
                "rusage": worker_data.get("rusage", {}),
            }

        return {
            "summary": {
                "total_workers": len(stats),
                "total_active_tasks": total_active,
                "total_scheduled_tasks": total_scheduled,
                "total_reserved_tasks": total_reserved,
            },
            "workers": worker_stats,
        }

    except Exception as e:
        logger.error(f"Celery 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

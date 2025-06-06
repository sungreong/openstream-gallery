import logging
from typing import Dict, Any
from celery import current_task
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from database import get_db
from models import App, Deployment
from services.nginx_service import NginxService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.deployment_tasks.cleanup_task")
def cleanup_task(self) -> Dict[str, Any]:
    """
    사용하지 않는 Nginx 설정 정리 태스크
    """
    task_id = self.request.id
    logger.info(f"🧹 정리 태스크 시작 (Task ID: {task_id})")

    nginx_service = NginxService()

    try:
        # 데이터베이스 세션 생성
        db = next(get_db())

        # 실제 서비스 중인 앱들의 서브도메인 목록 조회
        active_apps = db.query(App).filter(App.status.in_(["running", "building", "deploying"])).all()
        active_subdomains = {app.subdomain for app in active_apps if app.subdomain}

        logger.info(f"활성 앱 서브도메인: {active_subdomains}")

        # Nginx 동적 설정 파일 목록 조회
        config_files = nginx_service.list_dynamic_configs()

        # 시스템 설정 파일 제외
        system_configs = {"default.conf", "test.conf", "upstreams.conf"}

        removed_count = 0
        for config_file in config_files:
            if config_file in system_configs:
                continue

            # 설정 파일명에서 서브도메인 추출 (예: app-name.conf -> app-name)
            subdomain = config_file.replace(".conf", "")

            if subdomain not in active_subdomains:
                logger.info(f"사용하지 않는 설정 파일 제거: {config_file}")
                if nginx_service.remove_config(config_file):
                    removed_count += 1

        # Nginx 리로드
        if removed_count > 0:
            reload_success = nginx_service.reload_nginx()
            if not reload_success:
                logger.warning("⚠️ Nginx 리로드 실패")

        result = {
            "success": True,
            "removed_count": removed_count,
            "message": f"{removed_count}개의 사용하지 않는 설정 파일을 정리했습니다.",
        }

        logger.info(f"✅ 정리 태스크 완료 (Task ID: {task_id}): {removed_count}개 파일 제거")
        return result

    except Exception as e:
        logger.error(f"❌ 정리 태스크 실패 (Task ID: {task_id}): {str(e)}")
        raise Exception(f"정리 태스크 실패: {str(e)}")


@celery_app.task(bind=True, name="app.tasks.deployment_tasks.health_check_task")
def health_check_task(self) -> Dict[str, Any]:
    """
    앱 상태 확인 및 동기화 태스크
    """
    task_id = self.request.id
    logger.info(f"🏥 헬스체크 태스크 시작 (Task ID: {task_id})")

    try:
        # 데이터베이스 세션 생성
        db = next(get_db())

        # 실행 중이라고 기록된 앱들 조회
        running_apps = db.query(App).filter(App.status == "running").all()

        updated_count = 0
        for app in running_apps:
            if not app.container_id:
                continue

            try:
                # Docker 서비스를 통해 실제 컨테이너 상태 확인
                from services.docker_service import DockerService

                docker_service = DockerService()

                import asyncio

                container_status = asyncio.run(docker_service.get_container_status(app.container_id))

                # 컨테이너가 실제로 실행 중이 아니면 상태 업데이트
                if container_status != "running":
                    logger.warning(f"앱 {app.id} ({app.name})의 컨테이너가 중지됨: {container_status}")
                    app.status = "stopped"
                    app.container_id = None
                    app.port = None
                    updated_count += 1

            except Exception as e:
                logger.error(f"앱 {app.id} 상태 확인 실패: {str(e)}")
                app.status = "error"
                updated_count += 1

        # 변경사항 저장
        if updated_count > 0:
            db.commit()

        result = {
            "success": True,
            "checked_count": len(running_apps),
            "updated_count": updated_count,
            "message": f"{len(running_apps)}개 앱 확인, {updated_count}개 앱 상태 업데이트",
        }

        logger.info(f"✅ 헬스체크 태스크 완료 (Task ID: {task_id}): {updated_count}개 앱 상태 업데이트")
        return result

    except Exception as e:
        logger.error(f"❌ 헬스체크 태스크 실패 (Task ID: {task_id}): {str(e)}")
        raise Exception(f"헬스체크 태스크 실패: {str(e)}")


@celery_app.task(bind=True, name="app.tasks.deployment_tasks.log_rotation_task")
def log_rotation_task(self, days_to_keep: int = 30) -> Dict[str, Any]:
    """
    오래된 배포 로그 정리 태스크
    """
    task_id = self.request.id
    logger.info(f"📋 로그 정리 태스크 시작 (Task ID: {task_id})")

    try:
        # 데이터베이스 세션 생성
        db = next(get_db())

        # 30일 이전의 배포 기록 삭제
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        old_deployments = db.query(Deployment).filter(Deployment.deployed_at < cutoff_date)
        deleted_count = old_deployments.count()

        if deleted_count > 0:
            old_deployments.delete()
            db.commit()

        result = {
            "success": True,
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "message": f"{deleted_count}개의 오래된 배포 기록을 정리했습니다.",
        }

        logger.info(f"✅ 로그 정리 태스크 완료 (Task ID: {task_id}): {deleted_count}개 기록 삭제")
        return result

    except Exception as e:
        logger.error(f"❌ 로그 정리 태스크 실패 (Task ID: {task_id}): {str(e)}")
        raise Exception(f"로그 정리 태스크 실패: {str(e)}")

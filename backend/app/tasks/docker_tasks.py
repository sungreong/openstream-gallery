import os
import logging
from typing import Dict, Any, Optional
from celery import current_task
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from database import get_db
from models import App, Deployment
from services.docker_service import DockerService
from services.nginx_service import NginxService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.docker_tasks.build_image_task")
def build_image_task(
    self,
    app_id: int,
    git_url: str,
    branch: str,
    main_file: str,
    base_dockerfile_type: str = "auto",
    custom_commands: str = None,
    custom_base_image: str = None,
    git_credential: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Docker 이미지 빌드 태스크 (무거운 작업)
    """
    task_id = self.request.id
    logger.info(f"🚀 이미지 빌드 태스크 시작 (Task ID: {task_id}, App ID: {app_id})")

    # 태스크 상태 업데이트
    self.update_state(
        state="PROGRESS", meta={"current": 0, "total": 100, "status": "Git 저장소 클론 중...", "app_id": app_id}
    )

    docker_service = DockerService()
    temp_dir = None

    try:
        # 데이터베이스 세션 생성
        db = next(get_db())

        # 앱 정보 조회
        app = db.query(App).filter(App.id == app_id).first()
        if not app:
            raise Exception(f"앱을 찾을 수 없습니다 (ID: {app_id})")

        # 앱 상태를 빌드 중으로 업데이트
        app.status = "building"
        db.commit()

        # 1. Git 저장소 클론 (20%)
        self.update_state(
            state="PROGRESS", meta={"current": 20, "total": 100, "status": "Git 저장소 클론 중...", "app_id": app_id}
        )

        # Git 저장소 클론 (동기 방식으로 실행)
        import asyncio

        temp_dir = asyncio.run(
            docker_service.clone_repository(git_url=git_url, branch=branch, git_credential=git_credential)
        )
        logger.info(f"✅ Git 클론 완료: {temp_dir}")

        # 2. Docker 이미지 빌드 (80%)
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 40,
                "total": 100,
                "status": "Docker 이미지 빌드 중... (시간이 오래 걸릴 수 있습니다)",
                "app_id": app_id,
            },
        )

        image_name = f"streamlit-app-{app_id}"

        # build_image 호출 시 파라미터를 명시적으로 처리
        build_kwargs = {
            "repo_path": temp_dir,
            "image_name": image_name,
            "main_file": main_file,
            "base_dockerfile_type": base_dockerfile_type,
        }

        # 선택적 파라미터 추가
        if custom_commands is not None:
            build_kwargs["custom_commands"] = custom_commands
        if custom_base_image is not None:
            build_kwargs["custom_base_image"] = custom_base_image

        build_logs = asyncio.run(docker_service.build_image(**build_kwargs))

        logger.info(f"✅ 이미지 빌드 완료: {image_name}")

        # 3. 빌드 완료 (100%)
        self.update_state(
            state="PROGRESS", meta={"current": 100, "total": 100, "status": "이미지 빌드 완료", "app_id": app_id}
        )

        # 앱 상태를 빌드 완료로 업데이트
        app.status = "built"
        app.image_name = image_name

        # 4. 자동으로 배포 태스크 시작
        logger.info(f"🚀 배포 태스크 자동 시작 (App ID: {app_id})")
        deploy_task = deploy_app_task.delay(app_id=app_id, image_name=image_name)

        # 배포 태스크 ID 저장
        app.deploy_task_id = deploy_task.id
        db.commit()

        logger.info(f"✅ 배포 태스크 시작됨 (Deploy Task ID: {deploy_task.id})")

        result = {
            "success": True,
            "app_id": app_id,
            "image_name": image_name,
            "build_logs": build_logs,
            "deploy_task_id": deploy_task.id,
            "message": "이미지 빌드가 완료되었습니다. 배포를 시작합니다.",
        }

        logger.info(f"✅ 이미지 빌드 태스크 완료 (Task ID: {task_id})")
        return result

    except Exception as e:
        logger.error(f"❌ 이미지 빌드 태스크 실패 (Task ID: {task_id}): {str(e)}")

        # 앱 상태를 실패로 업데이트
        try:
            db_error_session = next(get_db())
            app_error = db_error_session.query(App).filter(App.id == app_id).first()
            if app_error:
                app_error.status = "failed"
                db_error_session.commit()
            db_error_session.close()
        except Exception as db_error:
            logger.error(f"❌ 앱 상태 업데이트 실패: {str(db_error)}")

        # 태스크 실패 상태 업데이트
        self.update_state(
            state="FAILURE",
            meta={"current": 0, "total": 100, "status": f"빌드 실패: {str(e)}", "app_id": app_id, "error": str(e)},
        )

        raise Exception(f"이미지 빌드 실패: {str(e)}")

    finally:
        # 임시 디렉토리 정리
        if temp_dir:
            docker_service.cleanup_temp_directory(temp_dir)

        # 데이터베이스 세션 정리
        try:
            if "db" in locals():
                db.close()
        except:
            pass


@celery_app.task(bind=True, name="app.tasks.docker_tasks.deploy_app_task")
def deploy_app_task(self, app_id: int, image_name: str, env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    앱 배포 태스크 (컨테이너 실행 + Nginx 설정)
    """
    task_id = self.request.id
    logger.info(f"🚀 앱 배포 태스크 시작 (Task ID: {task_id}, App ID: {app_id})")

    # 태스크 상태 업데이트
    self.update_state(
        state="PROGRESS", meta={"current": 0, "total": 100, "status": "컨테이너 실행 준비 중...", "app_id": app_id}
    )

    docker_service = DockerService()
    nginx_service = NginxService()

    try:
        # 데이터베이스 세션 생성
        db = next(get_db())

        # 앱 정보 조회
        app = db.query(App).filter(App.id == app_id).first()
        if not app:
            raise Exception(f"앱을 찾을 수 없습니다 (ID: {app_id})")

        # 앱 상태를 배포 중으로 업데이트
        app.status = "deploying"
        db.commit()

        # 1. 컨테이너 실행 (60%)
        self.update_state(
            state="PROGRESS",
            meta={"current": 30, "total": 100, "status": "Docker 컨테이너 실행 중...", "app_id": app_id},
        )

        container_name = f"streamlit-app-{app_id}"
        port = docker_service.get_available_port()

        import asyncio

        container_id = asyncio.run(
            docker_service.run_container(
                image_name=image_name, container_name=container_name, port=port, env_vars=env_vars, app_id=app_id
            )
        )

        logger.info(f"✅ 컨테이너 실행 완료: {container_id}")

        # 2. Nginx 설정 업데이트 (80%)
        self.update_state(
            state="PROGRESS",
            meta={"current": 60, "total": 100, "status": "Nginx 설정 업데이트 중...", "app_id": app_id},
        )

        # Nginx 설정 생성
        nginx_config = nginx_service.create_app_config(
            app_name=app.subdomain, container_name=container_name, port=8501  # Streamlit 기본 포트
        )

        # Nginx 설정 파일 저장
        config_saved = nginx_service.save_config(f"{app.subdomain}.conf", nginx_config)
        if not config_saved:
            logger.warning("⚠️ Nginx 설정 저장 실패, 계속 진행...")

        # Nginx 리로드
        reload_success = nginx_service.reload_nginx()
        if not reload_success:
            logger.warning("⚠️ Nginx 리로드 실패, 수동으로 확인 필요")

        # 3. 배포 완료 (100%)
        self.update_state(
            state="PROGRESS", meta={"current": 100, "total": 100, "status": "배포 완료", "app_id": app_id}
        )

        # 앱 상태를 실행 중으로 업데이트
        from sqlalchemy import text
        from datetime import datetime

        app.status = "running"
        app.container_id = container_id
        app.container_name = container_name
        app.port = port
        app.last_deployed_at = datetime.now()
        db.commit()

        result = {
            "success": True,
            "app_id": app_id,
            "container_id": container_id,
            "port": port,
            "message": "앱이 성공적으로 배포되었습니다.",
        }

        logger.info(f"✅ 앱 배포 태스크 완료 (Task ID: {task_id})")
        return result

    except Exception as e:
        logger.error(f"❌ 앱 배포 태스크 실패 (Task ID: {task_id}): {str(e)}")

        # 앱 상태를 실패로 업데이트
        try:
            db_error_session = next(get_db())
            app_error = db_error_session.query(App).filter(App.id == app_id).first()
            if app_error:
                app_error.status = "failed"
                db_error_session.commit()
            db_error_session.close()
        except Exception as db_error:
            logger.error(f"❌ 앱 상태 업데이트 실패: {str(db_error)}")

        # 태스크 실패 상태 업데이트
        self.update_state(
            state="FAILURE",
            meta={"current": 0, "total": 100, "status": f"배포 실패: {str(e)}", "app_id": app_id, "error": str(e)},
        )

        raise Exception(f"앱 배포 실패: {str(e)}")

    finally:
        # 데이터베이스 세션 정리
        try:
            if "db" in locals():
                db.close()
        except:
            pass


@celery_app.task(bind=True, name="app.tasks.docker_tasks.stop_app_task")
def stop_app_task(self, app_id: int) -> Dict[str, Any]:
    """
    앱 중지 태스크 (컨테이너 중지 + Nginx 설정 제거)
    """
    task_id = self.request.id
    logger.info(f"🚀 앱 중지 태스크 시작 (Task ID: {task_id}, App ID: {app_id})")

    # 태스크 상태 업데이트
    self.update_state(
        state="PROGRESS", meta={"current": 0, "total": 100, "status": "앱 중지 준비 중...", "app_id": app_id}
    )

    docker_service = DockerService()
    nginx_service = NginxService()

    try:
        # 데이터베이스 세션 생성
        db = next(get_db())

        # 앱 정보 조회
        app = db.query(App).filter(App.id == app_id).first()
        if not app:
            raise Exception(f"앱을 찾을 수 없습니다 (ID: {app_id})")

        # 앱 상태를 중지 중으로 업데이트
        app.status = "stopping"
        db.commit()

        # 1. 컨테이너 중지 (60%)
        self.update_state(
            state="PROGRESS",
            meta={"current": 30, "total": 100, "status": "Docker 컨테이너 중지 중...", "app_id": app_id},
        )

        if app.container_id:
            import asyncio

            stop_success = asyncio.run(docker_service.stop_container(app.container_id))
            if stop_success:
                logger.info(f"✅ 컨테이너 중지 완료: {app.container_id}")
            else:
                logger.warning(f"⚠️ 컨테이너 중지 실패: {app.container_id}")

        # 2. Nginx 설정 제거 (80%)
        self.update_state(
            state="PROGRESS",
            meta={"current": 60, "total": 100, "status": "Nginx 설정 제거 중...", "app_id": app_id},
        )

        # Nginx 설정 파일 삭제
        if app.subdomain:
            config_removed = nginx_service.remove_config(f"{app.subdomain}.conf")
            if config_removed:
                logger.info(f"✅ Nginx 설정 제거 완료: {app.subdomain}.conf")
            else:
                logger.warning(f"⚠️ Nginx 설정 제거 실패: {app.subdomain}.conf")

            # Nginx 리로드
            reload_success = nginx_service.reload_nginx()
            if not reload_success:
                logger.warning("⚠️ Nginx 리로드 실패, 수동으로 확인 필요")

        # 3. 중지 완료 (100%)
        self.update_state(
            state="PROGRESS", meta={"current": 100, "total": 100, "status": "중지 완료", "app_id": app_id}
        )

        # 앱 상태를 중지됨으로 업데이트
        app.status = "stopped"
        app.container_id = None
        app.container_name = None
        app.port = None
        db.commit()

        result = {
            "success": True,
            "app_id": app_id,
            "message": "앱이 성공적으로 중지되었습니다.",
        }

        logger.info(f"✅ 앱 중지 태스크 완료 (Task ID: {task_id})")
        return result

    except Exception as e:
        logger.error(f"❌ 앱 중지 태스크 실패 (Task ID: {task_id}): {str(e)}")

        # 앱 상태를 실패로 업데이트
        try:
            db_error_session = next(get_db())
            app_error = db_error_session.query(App).filter(App.id == app_id).first()
            if app_error:
                app_error.status = "failed"
                db_error_session.commit()
            db_error_session.close()
        except Exception as db_error:
            logger.error(f"❌ 앱 상태 업데이트 실패: {str(db_error)}")

        # 태스크 실패 상태 업데이트
        self.update_state(
            state="FAILURE",
            meta={"current": 0, "total": 100, "status": f"중지 실패: {str(e)}", "app_id": app_id, "error": str(e)},
        )

        raise Exception(f"앱 중지 실패: {str(e)}")

    finally:
        # 데이터베이스 세션 정리
        try:
            if "db" in locals():
                db.close()
        except:
            pass


@celery_app.task(bind=True, name="app.tasks.docker_tasks.remove_app_task")
def remove_app_task(self, app_id: int) -> Dict[str, Any]:
    """
    앱 제거 태스크 (컨테이너/이미지 제거 + 앱 삭제)
    """
    task_id = self.request.id
    logger.info(f"🚀 앱 제거 태스크 시작 (Task ID: {task_id}, App ID: {app_id})")

    # 태스크 상태 업데이트
    self.update_state(
        state="PROGRESS", meta={"current": 0, "total": 100, "status": "앱 제거 준비 중...", "app_id": app_id}
    )

    docker_service = DockerService()
    nginx_service = NginxService()

    try:
        # 데이터베이스 세션 생성
        db = next(get_db())

        # 앱 정보 조회
        app = db.query(App).filter(App.id == app_id).first()
        if not app:
            raise Exception(f"앱을 찾을 수 없습니다 (ID: {app_id})")

        # 1. 컨테이너 제거 (40%)
        self.update_state(
            state="PROGRESS",
            meta={"current": 20, "total": 100, "status": "Docker 컨테이너 제거 중...", "app_id": app_id},
        )

        if app.container_id:
            import asyncio

            remove_success = asyncio.run(docker_service.remove_container(app.container_id))
            if remove_success:
                logger.info(f"✅ 컨테이너 제거 완료: {app.container_id}")
            else:
                logger.warning(f"⚠️ 컨테이너 제거 실패: {app.container_id}")

        # 2. 이미지 제거 (60%)
        self.update_state(
            state="PROGRESS",
            meta={"current": 40, "total": 100, "status": "Docker 이미지 제거 중...", "app_id": app_id},
        )

        if app.image_name:
            import asyncio

            image_remove_success = asyncio.run(docker_service.remove_image(app.image_name))
            if image_remove_success:
                logger.info(f"✅ 이미지 제거 완료: {app.image_name}")
            else:
                logger.warning(f"⚠️ 이미지 제거 실패: {app.image_name}")

        # 3. Nginx 설정 제거 (80%)
        self.update_state(
            state="PROGRESS",
            meta={"current": 60, "total": 100, "status": "Nginx 설정 제거 중...", "app_id": app_id},
        )

        if app.subdomain:
            config_removed = nginx_service.remove_config(f"{app.subdomain}.conf")
            if config_removed:
                logger.info(f"✅ Nginx 설정 제거 완료: {app.subdomain}.conf")

            # Nginx 리로드
            reload_success = nginx_service.reload_nginx()
            if not reload_success:
                logger.warning("⚠️ Nginx 리로드 실패, 수동으로 확인 필요")

        # 4. 앱 삭제 (100%)
        self.update_state(
            state="PROGRESS", meta={"current": 80, "total": 100, "status": "앱 데이터 삭제 중...", "app_id": app_id}
        )

        # 관련 배포 기록 삭제
        db.query(Deployment).filter(Deployment.app_id == app_id).delete()

        # 앱 삭제
        db.delete(app)
        db.commit()

        # 5. 제거 완료 (100%)
        self.update_state(
            state="PROGRESS", meta={"current": 100, "total": 100, "status": "제거 완료", "app_id": app_id}
        )

        result = {
            "success": True,
            "app_id": app_id,
            "message": "앱이 성공적으로 제거되었습니다.",
        }

        logger.info(f"✅ 앱 제거 태스크 완료 (Task ID: {task_id})")
        return result

    except Exception as e:
        logger.error(f"❌ 앱 제거 태스크 실패 (Task ID: {task_id}): {str(e)}")

        # 태스크 실패 상태 업데이트
        self.update_state(
            state="FAILURE",
            meta={"current": 0, "total": 100, "status": f"제거 실패: {str(e)}", "app_id": app_id, "error": str(e)},
        )

        raise Exception(f"앱 제거 실패: {str(e)}")

    finally:
        # 데이터베이스 세션 정리
        try:
            if "db" in locals():
                db.close()
        except:
            pass

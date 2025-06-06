from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import asyncio
import uuid
import re

from database import get_db
from models import User, App, Deployment, AppEnvVar, GitCredential
from schemas import AppCreate, AppUpdate, AppResponse, AppDeployRequest, AppLogsResponse, AppCreateWithAuth
from routers.auth import get_current_user
from services.docker_service import DockerService
from services.nginx_service import NginxService
from services.crypto_service import CryptoService

router = APIRouter(tags=["apps"])
docker_service = DockerService()
nginx_service = NginxService()
crypto_service = CryptoService()


def generate_subdomain(app_name: str) -> str:
    """앱 이름을 기반으로 서브도메인 생성"""
    # 특수문자 제거 및 소문자 변환
    subdomain = re.sub(r"[^a-zA-Z0-9-]", "-", app_name.lower())
    subdomain = re.sub(r"-+", "-", subdomain)  # 연속된 하이픈 제거
    subdomain = subdomain.strip("-")  # 앞뒤 하이픈 제거

    # 고유성을 위해 UUID 일부 추가
    unique_suffix = str(uuid.uuid4())[:8]
    return f"{subdomain}-{unique_suffix}"


async def deploy_app_background(app_id: int, db: Session, env_vars: dict = None):
    """백그라운드에서 앱 배포 실행"""
    import logging

    logger = logging.getLogger(__name__)

    logger.info(f"🚀 앱 배포 시작 - App ID: {app_id}")

    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        logger.error(f"❌ 앱을 찾을 수 없음 - App ID: {app_id}")
        return

    logger.info(f"📋 앱 정보 확인 완료 - 이름: {app.name}, Git URL: {app.git_url}")

    deployment = Deployment(app_id=app_id, status="in_progress")
    db.add(deployment)
    db.commit()
    logger.info(f"📝 배포 레코드 생성 완료 - Deployment ID: {deployment.id}")

    repo_path = None
    try:
        # 앱 상태를 building으로 변경
        logger.info("🔄 앱 상태를 'building'으로 변경 중...")
        app.status = "building"
        db.commit()
        logger.info("✅ 앱 상태 변경 완료")

        # Git 인증 정보 가져오기
        logger.info("🔐 Git 인증 정보 확인 중...")
        git_credential_data = None
        if hasattr(app, "git_credential_id") and app.git_credential_id:
            logger.info(f"🔑 Git 인증 정보 ID: {app.git_credential_id}")
            git_credential = db.query(GitCredential).filter(GitCredential.id == app.git_credential_id).first()

            if git_credential:
                logger.info(f"✅ Git 인증 정보 발견 - 타입: {git_credential.auth_type}")
                git_credential_data = {
                    "auth_type": git_credential.auth_type,
                    "username": git_credential.username,
                    "token": (
                        crypto_service.decrypt(git_credential.token_encrypted)
                        if git_credential.token_encrypted
                        else None
                    ),
                    "ssh_key": (
                        crypto_service.decrypt(git_credential.ssh_key_encrypted)
                        if git_credential.ssh_key_encrypted
                        else None
                    ),
                }
            else:
                logger.warning(f"⚠️ Git 인증 정보를 찾을 수 없음 - ID: {app.git_credential_id}")
        else:
            logger.info("📂 공개 저장소로 인식 (인증 정보 없음)")

        # Git 저장소 클론
        logger.info(f"📥 Git 저장소 클론 시작 - URL: {app.git_url}, 브랜치: {app.branch}")
        repo_path = await docker_service.clone_repository(app.git_url, app.branch, git_credential_data)
        logger.info(f"✅ Git 저장소 클론 완료 - 경로: {repo_path}")

        # Docker 이미지 빌드
        image_name = f"streamlit_app_{app.id}"
        logger.info(f"🔨 Docker 이미지 빌드 시작 - 이미지명: {image_name}, 메인파일: {app.main_file}")
        # 베이스 Dockerfile 타입 전달 (앱 생성 시 선택된 값 사용)
        base_dockerfile_type = getattr(app, "base_dockerfile_type", "auto")
        # print(base_dockerfile_type)
        logger.info(f"base_dockerfile_type: {base_dockerfile_type}")
        build_logs = await docker_service.build_image(repo_path, image_name, app.main_file, base_dockerfile_type)
        logger.info(f"✅ Docker 이미지 빌드 완료 - 로그 길이: {len(build_logs)} 문자")

        # 사용 가능한 포트 할당
        logger.info("🔌 포트 할당 중...")
        port = docker_service.get_available_port()
        logger.info(f"✅ 포트 할당 완료 - 포트: {port}")

        # 환경변수 준비
        logger.info("🌍 환경변수 준비 중...")
        app_env_vars = {}
        if env_vars:
            app_env_vars.update(env_vars)
            logger.info(f"📥 요청 환경변수 추가: {len(env_vars)}개")

        # 데이터베이스에 저장된 환경변수 추가
        db_env_vars = db.query(AppEnvVar).filter(AppEnvVar.app_id == app_id).all()
        for env_var in db_env_vars:
            app_env_vars[env_var.key] = env_var.value
        logger.info(f"💾 DB 환경변수 추가: {len(db_env_vars)}개, 총 환경변수: {len(app_env_vars)}개")

        # 컨테이너 실행
        container_name = f"streamlit_app_{app.id}"
        logger.info(f"🐳 Docker 컨테이너 실행 시작 - 컨테이너명: {container_name}")
        container_id = await docker_service.run_container(image_name, container_name, port, app_env_vars)
        logger.info(f"✅ Docker 컨테이너 실행 완료 - 컨테이너 ID: {container_id[:12]}...")

        # Nginx 설정 추가
        logger.info(f"🌐 Nginx 설정 추가 중 - 서브도메인: {app.subdomain}")
        await nginx_service.add_app_config(app.subdomain, container_name)
        logger.info("✅ Nginx 설정 추가 완료")

        # 앱 정보 업데이트
        logger.info("📝 앱 정보 업데이트 중...")
        app.status = "running"
        app.container_id = container_id
        app.port = port
        app.last_deployed_at = deployment.deployed_at

        # 배포 성공 기록
        deployment.status = "success"
        deployment.build_logs = build_logs

        db.commit()
        logger.info("✅ 데이터베이스 업데이트 완료")

        # 임시 디렉토리 정리
        logger.info("🧹 임시 디렉토리 정리 중...")
        # docker_service.cleanup_temp_directory(repo_path)
        logger.info("✅ 임시 디렉토리 정리 완료")

        logger.info(f"🎉 앱 배포 성공! - App ID: {app_id}, 컨테이너: {container_name}")

    except Exception as e:
        # 배포 실패 처리
        logger.error(f"❌ 앱 배포 실패 - App ID: {app_id}, 에러: {str(e)}")
        logger.exception("상세 에러 정보:")

        app.status = "error"
        deployment.status = "failed"
        deployment.error_message = str(e)
        db.commit()
        logger.info("💾 실패 상태 데이터베이스 저장 완료")

        # 임시 디렉토리 정리
        if repo_path:
            logger.info("🧹 실패 후 임시 디렉토리 정리 중...")
            # docker_service.cleanup_temp_directory(repo_path)
            logger.info("✅ 임시 디렉토리 정리 완료")


@router.get("/", response_model=List[AppResponse])
async def get_apps(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """사용자의 앱 목록 조회"""
    apps = db.query(App).filter(App.user_id == current_user.id).all()
    return apps


@router.post("/", response_model=AppResponse)
async def create_app(
    app: AppCreateWithAuth, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """새 앱 생성"""
    # Git 인증 정보 확인 (선택사항)
    if app.git_credential_id:
        git_credential = (
            db.query(GitCredential)
            .filter(GitCredential.id == app.git_credential_id, GitCredential.user_id == current_user.id)
            .first()
        )

        if not git_credential:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git 인증 정보를 찾을 수 없습니다.")

    # 서브도메인 생성
    subdomain = generate_subdomain(app.name)

    # 서브도메인 중복 확인
    existing_app = db.query(App).filter(App.subdomain == subdomain).first()
    if existing_app:
        # 중복되면 새로운 서브도메인 생성
        subdomain = generate_subdomain(f"{app.name}-{uuid.uuid4().hex[:4]}")

    db_app = App(
        name=app.name,
        description=app.description,
        git_url=app.git_url,
        branch=app.branch,
        main_file=app.main_file,
        user_id=current_user.id,
        git_credential_id=app.git_credential_id,
        base_dockerfile_type=app.base_dockerfile_type,
        subdomain=subdomain,
    )

    db.add(db_app)
    db.commit()
    db.refresh(db_app)

    return db_app


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(app_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """특정 앱 조회"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    return app


@router.put("/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: int, app_update: AppUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """앱 정보 수정 (앱이 중지된 상태에서만 가능)"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    # 앱이 실행 중이거나 빌드 중일 때는 수정 불가
    if app.status in ["running", "building"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="앱이 실행 중이거나 빌드 중일 때는 수정할 수 없습니다. 먼저 앱을 중지해주세요.",
        )

    # Git 인증 정보 확인 (변경하는 경우)
    if app_update.git_credential_id is not None and app_update.git_credential_id != 0:
        git_credential = (
            db.query(GitCredential)
            .filter(GitCredential.id == app_update.git_credential_id, GitCredential.user_id == current_user.id)
            .first()
        )

        if not git_credential:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git 인증 정보를 찾을 수 없습니다.")

    # 업데이트할 필드만 수정
    update_data = app_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(app, field, value)

    db.commit()
    db.refresh(app)

    return app


@router.delete("/{app_id}")
async def delete_app(app_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """앱 삭제"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    # 컨테이너 중지 및 제거
    if app.container_id:
        await docker_service.remove_container(app.container_id)

    # Nginx 설정 제거
    if app.subdomain:
        await nginx_service.remove_app_config(app.subdomain)

    # 데이터베이스에서 삭제
    db.delete(app)
    db.commit()

    return {"message": "App deleted successfully"}


@router.post("/{app_id}/deploy")
async def deploy_app(
    app_id: int,
    deploy_request: AppDeployRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """앱 배포 (Celery 태스크 사용)"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    if app.status in ["building", "deploying", "running"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="App is already being deployed or running")

    try:
        # Git 인증 정보 가져오기
        git_credential_data = None
        if hasattr(app, "git_credential_id") and app.git_credential_id:
            git_credential = db.query(GitCredential).filter(GitCredential.id == app.git_credential_id).first()
            if git_credential:
                git_credential_data = {
                    "auth_type": git_credential.auth_type,
                    "username": git_credential.username,
                    "token": (
                        crypto_service.decrypt(git_credential.token_encrypted)
                        if git_credential.token_encrypted
                        else None
                    ),
                    "ssh_key": (
                        crypto_service.decrypt(git_credential.ssh_key_encrypted)
                        if git_credential.ssh_key_encrypted
                        else None
                    ),
                }

        # 베이스 Dockerfile 타입
        base_dockerfile_type = getattr(app, "base_dockerfile_type", "auto")

        # 이미지 빌드 태스크 시작
        build_task_id = docker_service.build_image_async(
            app_id=app_id,
            git_url=app.git_url,
            branch=app.branch,
            main_file=app.main_file,
            base_dockerfile_type=base_dockerfile_type,
            git_credential=git_credential_data,
        )

        # 앱에 태스크 ID 저장
        app.build_task_id = build_task_id
        db.commit()

        return {
            "message": "앱 배포가 시작되었습니다. 이미지 빌드 후 자동으로 배포됩니다.",
            "app_id": app_id,
            "build_task_id": build_task_id,
            "status": "building",
            "app_url": f"/{app.subdomain}/",
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"배포 시작 실패: {str(e)}")


@router.post("/{app_id}/stop")
async def stop_app(app_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """앱 중지 (Celery 태스크 사용)"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    if app.status != "running":
        return {"message": "App is not running", "status": app.status}

    try:
        # 앱 중지 태스크 시작
        stop_task_id = docker_service.stop_app_async(app_id=app_id)

        # 앱에 태스크 ID 저장
        app.stop_task_id = stop_task_id
        app.status = "stopping"
        db.commit()

        return {
            "message": "앱 중지가 시작되었습니다.",
            "app_id": app_id,
            "stop_task_id": stop_task_id,
            "status": "stopping",
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"앱 중지 시작 실패: {str(e)}")


@router.get("/{app_id}/logs", response_model=AppLogsResponse)
async def get_app_logs(app_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """앱 로그 조회"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    if not app.container_id:
        return AppLogsResponse(logs="No container found", container_status="not_found")

    logs = await docker_service.get_container_logs(app.container_id)
    status = await docker_service.get_container_status(app.container_id)

    return AppLogsResponse(logs=logs, container_status=status)


@router.get("/{app_id}/task-status/{task_id}")
async def get_task_status(
    app_id: int, task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Celery 태스크 상태 조회"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    try:
        task_status = docker_service.get_task_status(task_id)

        # 태스크가 완료되었고 성공한 경우, 다음 단계 실행
        if task_status.get("state") == "SUCCESS" and task_status.get("ready"):
            result = task_status.get("result", {})

            # 빌드 태스크가 완료된 경우 배포 태스크 시작
            if hasattr(app, "build_task_id") and app.build_task_id == task_id:
                if result.get("success") and result.get("image_name"):
                    # 배포 태스크 시작
                    deploy_task_id = docker_service.deploy_app_async(app_id=app_id, image_name=result["image_name"])

                    # 앱에 배포 태스크 ID 저장
                    app.deploy_task_id = deploy_task_id
                    app.build_task_id = None  # 빌드 태스크 완료
                    db.commit()

                    return {
                        "build_task": task_status,
                        "deploy_task_id": deploy_task_id,
                        "message": "이미지 빌드 완료. 배포 시작 중...",
                    }

        return task_status

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"태스크 상태 조회 실패: {str(e)}"
        )


@router.post("/{app_id}/deploy-built")
async def deploy_built_app(app_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """이미 빌드된 앱 배포 (빌드 완료 후 호출)"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    if not app.image_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="App image not found")

    try:
        # 배포 태스크 시작
        deploy_task_id = docker_service.deploy_app_async(app_id=app_id, image_name=app.image_name)

        # 앱에 태스크 ID 저장
        app.deploy_task_id = deploy_task_id
        db.commit()

        return {
            "message": "앱 배포가 시작되었습니다.",
            "app_id": app_id,
            "deploy_task_id": deploy_task_id,
            "status": "deploying",
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"배포 시작 실패: {str(e)}")


@router.get("/{app_id}/container-status")
async def get_container_status(
    app_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """컨테이너 상태 조회"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    try:
        container_status = "not_found"
        container_info = {}

        if app.container_id:
            container_status = await docker_service.get_container_status(app.container_id)

            # 컨테이너 상세 정보 조회
            if docker_service.use_cli:
                # CLI를 사용한 컨테이너 정보 조회
                result = docker_service._run_docker_command(["inspect", "--format", "{{json .}}", app.container_id])

                if result.returncode == 0:
                    import json

                    container_data = json.loads(result.stdout)
                    container_info = {
                        "id": container_data.get("Id", "")[:12],
                        "name": container_data.get("Name", "").lstrip("/"),
                        "status": container_data.get("State", {}).get("Status", "unknown"),
                        "running": container_data.get("State", {}).get("Running", False),
                        "started_at": container_data.get("State", {}).get("StartedAt", ""),
                        "finished_at": container_data.get("State", {}).get("FinishedAt", ""),
                        "restart_count": container_data.get("RestartCount", 0),
                        "image": container_data.get("Config", {}).get("Image", ""),
                        "ports": container_data.get("NetworkSettings", {}).get("Ports", {}),
                        "networks": list(container_data.get("NetworkSettings", {}).get("Networks", {}).keys()),
                    }
            else:
                # SDK를 사용한 컨테이너 정보 조회
                try:
                    container = docker_service.client.containers.get(app.container_id)
                    container_info = {
                        "id": container.id[:12],
                        "name": container.name,
                        "status": container.status,
                        "running": container.status == "running",
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                        "ports": container.ports,
                        "networks": list(container.attrs.get("NetworkSettings", {}).get("Networks", {}).keys()),
                    }
                except Exception as e:
                    container_info = {"error": str(e)}

        return {
            "app_id": app_id,
            "app_status": app.status,
            "container_id": app.container_id,
            "container_status": container_status,
            "container_info": container_info,
            "image_name": app.image_name,
            "port": app.port,
            "subdomain": app.subdomain,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"컨테이너 상태 조회 실패: {str(e)}"
        )


@router.get("/{app_id}/celery-status")
async def get_celery_status(
    app_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """앱의 모든 Celery 태스크 상태 조회"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    try:
        task_statuses = {}

        # 빌드 태스크 상태
        if app.build_task_id:
            task_statuses["build_task"] = docker_service.get_task_status(app.build_task_id)
            task_statuses["build_task"]["task_type"] = "build"

        # 배포 태스크 상태
        if app.deploy_task_id:
            task_statuses["deploy_task"] = docker_service.get_task_status(app.deploy_task_id)
            task_statuses["deploy_task"]["task_type"] = "deploy"

        # 중지 태스크 상태
        if app.stop_task_id:
            task_statuses["stop_task"] = docker_service.get_task_status(app.stop_task_id)
            task_statuses["stop_task"]["task_type"] = "stop"

        return {
            "app_id": app_id,
            "app_status": app.status,
            "tasks": task_statuses,
            "active_tasks": [
                task_id for task_id in [app.build_task_id, app.deploy_task_id, app.stop_task_id] if task_id
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Celery 태스크 상태 조회 실패: {str(e)}"
        )


@router.post("/{app_id}/cancel-task/{task_type}")
async def cancel_task(
    app_id: int, task_type: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Celery 태스크 취소"""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    try:
        from app.celery_app import celery_app

        task_id = None
        if task_type == "build" and app.build_task_id:
            task_id = app.build_task_id
        elif task_type == "deploy" and app.deploy_task_id:
            task_id = app.deploy_task_id
        elif task_type == "stop" and app.stop_task_id:
            task_id = app.stop_task_id

        if not task_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"{task_type} 태스크를 찾을 수 없습니다."
            )

        # 태스크 취소
        celery_app.control.revoke(task_id, terminate=True)

        # 앱 상태 업데이트
        if task_type == "build":
            app.build_task_id = None
            app.status = "stopped"
        elif task_type == "deploy":
            app.deploy_task_id = None
            app.status = "stopped"
        elif task_type == "stop":
            app.stop_task_id = None

        db.commit()

        return {
            "message": f"{task_type} 태스크가 취소되었습니다.",
            "app_id": app_id,
            "task_type": task_type,
            "cancelled_task_id": task_id,
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"태스크 취소 실패: {str(e)}")

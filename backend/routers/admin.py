from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from pathlib import Path

from database import get_db
from models import User, App
from schemas import UserResponse, UserUpdate, AdminStats
from routers.auth import get_current_user, get_current_admin_user
from services.docker_service import DockerService

router = APIRouter(prefix="/api/admin", tags=["admin"])


# 관리자 전용 통계 정보
@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """관리자 대시보드용 통계 정보 조회"""
    total_users = db.query(User).count()
    total_apps = db.query(App).count()
    running_apps = db.query(App).filter(App.status == "running").count()

    # Docker 시스템 정보
    docker_service = DockerService()
    try:
        docker_info = docker_service.get_system_info()
    except Exception as e:
        docker_info = {"error": str(e)}

    return AdminStats(
        total_users=total_users, total_apps=total_apps, running_apps=running_apps, docker_info=docker_info
    )


# 사용자 관리
@router.get("/users", response_model=List[UserResponse])
async def get_all_users(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """모든 사용자 목록 조회"""
    users = db.query(User).all()
    return users


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """사용자 정보 수정 (관리자 권한 포함)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    # 업데이트할 필드들
    if user_update.username is not None:
        # 중복 체크
        existing_user = db.query(User).filter(User.username == user_update.username, User.id != user_id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="이미 사용 중인 사용자명입니다")
        user.username = user_update.username

    if user_update.email is not None:
        # 중복 체크
        existing_user = db.query(User).filter(User.email == user_update.email, User.id != user_id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
        user.email = user_update.email

    if user_update.is_admin is not None:
        user.is_admin = user_update.is_admin

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)
):
    """사용자 삭제"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="자기 자신은 삭제할 수 없습니다")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    # 사용자의 앱들도 함께 삭제됨 (CASCADE)
    db.delete(user)
    db.commit()
    return {"message": "사용자가 삭제되었습니다"}


# Dockerfile 관리
@router.get("/dockerfiles")
async def get_dockerfile_list(current_user: User = Depends(get_current_admin_user)):
    """베이스 Dockerfile 목록 조회"""
    dockerfiles_dir = Path("dockerfiles")
    if not dockerfiles_dir.exists():
        return {"dockerfiles": []}

    dockerfiles = []
    for dockerfile_path in dockerfiles_dir.glob("Dockerfile.*"):
        if dockerfile_path.is_file():
            dockerfile_type = dockerfile_path.name.replace("Dockerfile.", "")
            try:
                with open(dockerfile_path, "r", encoding="utf-8") as f:
                    content = f.read()
                dockerfiles.append(
                    {
                        "type": dockerfile_type,
                        "filename": dockerfile_path.name,
                        "content": content,
                        "size": len(content),
                    }
                )
            except Exception as e:
                dockerfiles.append({"type": dockerfile_type, "filename": dockerfile_path.name, "error": str(e)})

    return {"dockerfiles": dockerfiles}


@router.get("/dockerfiles/{dockerfile_type}")
async def get_dockerfile_content(dockerfile_type: str, current_user: User = Depends(get_current_admin_user)):
    """특정 Dockerfile 내용 조회"""
    dockerfile_path = Path(f"dockerfiles/Dockerfile.{dockerfile_type}")
    if not dockerfile_path.exists():
        raise HTTPException(status_code=404, detail="Dockerfile을 찾을 수 없습니다")

    try:
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"type": dockerfile_type, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 읽기 오류: {str(e)}")


@router.put("/dockerfiles/{dockerfile_type}")
async def update_dockerfile(
    dockerfile_type: str, request_body: dict = Body(...), current_user: User = Depends(get_current_admin_user)
):
    """Dockerfile 내용 수정"""
    content = request_body.get("content", "")
    dockerfile_path = Path(f"dockerfiles/Dockerfile.{dockerfile_type}")

    # 백업 생성
    if dockerfile_path.exists():
        backup_path = Path(f"dockerfiles/Dockerfile.{dockerfile_type}.backup")
        shutil.copy2(dockerfile_path, backup_path)

    try:
        # 디렉토리 생성
        dockerfile_path.parent.mkdir(parents=True, exist_ok=True)

        # 파일 저장
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"message": "Dockerfile이 성공적으로 업데이트되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 오류: {str(e)}")


@router.post("/dockerfiles/{dockerfile_type}")
async def create_dockerfile(
    dockerfile_type: str, request_body: dict = Body(...), current_user: User = Depends(get_current_admin_user)
):
    """새로운 Dockerfile 생성"""
    content = request_body.get("content", "")
    dockerfile_path = Path(f"dockerfiles/Dockerfile.{dockerfile_type}")

    if dockerfile_path.exists():
        raise HTTPException(status_code=400, detail="이미 존재하는 Dockerfile입니다")

    try:
        # 디렉토리 생성
        dockerfile_path.parent.mkdir(parents=True, exist_ok=True)

        # 파일 생성
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"message": "새로운 Dockerfile이 생성되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 생성 오류: {str(e)}")


@router.delete("/dockerfiles/{dockerfile_type}")
async def delete_dockerfile(dockerfile_type: str, current_user: User = Depends(get_current_admin_user)):
    """Dockerfile 삭제"""
    dockerfile_path = Path(f"dockerfiles/Dockerfile.{dockerfile_type}")

    if not dockerfile_path.exists():
        raise HTTPException(status_code=404, detail="Dockerfile을 찾을 수 없습니다")

    # 기본 Dockerfile들은 삭제 방지
    protected_types = ["simple", "minimal", "py311", "py310", "py309", "datascience"]
    if dockerfile_type in protected_types:
        raise HTTPException(status_code=400, detail="기본 Dockerfile은 삭제할 수 없습니다")

    try:
        dockerfile_path.unlink()
        return {"message": "Dockerfile이 삭제되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 삭제 오류: {str(e)}")


# 시스템 관리
@router.post("/system/cleanup")
async def system_cleanup(current_user: User = Depends(get_current_admin_user)):
    """시스템 정리 (사용하지 않는 Docker 이미지, 컨테이너 등)"""
    docker_service = DockerService()
    try:
        cleanup_result = docker_service.system_cleanup()
        return {"message": "시스템 정리가 완료되었습니다", "result": cleanup_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 정리 오류: {str(e)}")

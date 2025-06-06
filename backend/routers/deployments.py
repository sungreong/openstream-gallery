from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User, App, Deployment
from schemas import DeploymentResponse
from routers.auth import get_current_user

router = APIRouter(tags=["deployments"])


@router.get("/", response_model=List[DeploymentResponse])
async def get_deployments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """사용자의 모든 배포 히스토리 조회"""
    deployments = (
        db.query(Deployment)
        .join(App)
        .filter(App.user_id == current_user.id)
        .order_by(Deployment.deployed_at.desc())
        .all()
    )

    return deployments


@router.get("/app/{app_id}", response_model=List[DeploymentResponse])
async def get_app_deployments(
    app_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """특정 앱의 배포 히스토리 조회"""
    # 앱 소유권 확인
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    deployments = (
        db.query(Deployment).filter(Deployment.app_id == app_id).order_by(Deployment.deployed_at.desc()).all()
    )

    return deployments


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """특정 배포 정보 조회"""
    deployment = (
        db.query(Deployment).join(App).filter(Deployment.id == deployment_id, App.user_id == current_user.id).first()
    )

    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    return deployment

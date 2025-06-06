from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User, GitCredential
from schemas import GitCredentialCreate, GitCredentialUpdate, GitCredentialResponse
from routers.auth import get_current_user
from services.crypto_service import CryptoService

router = APIRouter(tags=["git-credentials"])
crypto_service = CryptoService()


@router.get("/", response_model=List[GitCredentialResponse])
async def get_git_credentials(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """사용자의 Git 인증 정보 목록 조회"""
    credentials = db.query(GitCredential).filter(GitCredential.user_id == current_user.id).all()
    return credentials


@router.post("/", response_model=GitCredentialResponse)
async def create_git_credential(
    credential: GitCredentialCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """새 Git 인증 정보 생성"""
    # 이름 중복 확인
    existing = (
        db.query(GitCredential)
        .filter(GitCredential.user_id == current_user.id, GitCredential.name == credential.name)
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="같은 이름의 인증 정보가 이미 존재합니다.")

    # 토큰이나 SSH 키 중 하나는 필수
    if credential.auth_type == "token" and not credential.token:
        raise HTTPException(status_code=400, detail="토큰 인증 방식에는 토큰이 필요합니다.")

    if credential.auth_type == "ssh" and not credential.ssh_key:
        raise HTTPException(status_code=400, detail="SSH 인증 방식에는 SSH 키가 필요합니다.")

    # 암호화하여 저장
    token_encrypted = crypto_service.encrypt(credential.token) if credential.token else None
    ssh_key_encrypted = crypto_service.encrypt(credential.ssh_key) if credential.ssh_key else None

    db_credential = GitCredential(
        user_id=current_user.id,
        name=credential.name,
        git_provider=credential.git_provider,
        auth_type=credential.auth_type,
        username=credential.username,
        token_encrypted=token_encrypted,
        ssh_key_encrypted=ssh_key_encrypted,
    )

    db.add(db_credential)
    db.commit()
    db.refresh(db_credential)

    return db_credential


@router.get("/{credential_id}", response_model=GitCredentialResponse)
async def get_git_credential(
    credential_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """특정 Git 인증 정보 조회"""
    credential = (
        db.query(GitCredential)
        .filter(GitCredential.id == credential_id, GitCredential.user_id == current_user.id)
        .first()
    )

    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git 인증 정보를 찾을 수 없습니다.")

    return credential


@router.put("/{credential_id}", response_model=GitCredentialResponse)
async def update_git_credential(
    credential_id: int,
    credential_update: GitCredentialUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Git 인증 정보 수정"""
    credential = (
        db.query(GitCredential)
        .filter(GitCredential.id == credential_id, GitCredential.user_id == current_user.id)
        .first()
    )

    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git 인증 정보를 찾을 수 없습니다.")

    # 이름 중복 확인 (다른 인증 정보와)
    if credential_update.name and credential_update.name != credential.name:
        existing = (
            db.query(GitCredential)
            .filter(
                GitCredential.user_id == current_user.id,
                GitCredential.name == credential_update.name,
                GitCredential.id != credential_id,
            )
            .first()
        )

        if existing:
            raise HTTPException(status_code=400, detail="같은 이름의 인증 정보가 이미 존재합니다.")

    # 업데이트할 필드들
    update_data = credential_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        if field == "token" and value:
            credential.token_encrypted = crypto_service.encrypt(value)
        elif field == "ssh_key" and value:
            credential.ssh_key_encrypted = crypto_service.encrypt(value)
        elif field not in ["token", "ssh_key"]:
            setattr(credential, field, value)

    db.commit()
    db.refresh(credential)

    return credential


@router.delete("/{credential_id}")
async def delete_git_credential(
    credential_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Git 인증 정보 삭제"""
    credential = (
        db.query(GitCredential)
        .filter(GitCredential.id == credential_id, GitCredential.user_id == current_user.id)
        .first()
    )

    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git 인증 정보를 찾을 수 없습니다.")

    db.delete(credential)
    db.commit()

    return {"message": "Git 인증 정보가 삭제되었습니다."}

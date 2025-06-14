from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime


# 사용자 스키마
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


# 앱 스키마
class AppBase(BaseModel):
    name: str
    description: Optional[str] = None
    git_url: str
    branch: str = "main"
    main_file: str = "streamlit_app.py"


class AppCreate(AppBase):
    pass


class AppUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    git_url: Optional[str] = None
    branch: Optional[str] = None
    main_file: Optional[str] = None
    base_dockerfile_type: Optional[str] = None
    custom_base_image: Optional[str] = None
    custom_dockerfile_commands: Optional[str] = None
    git_credential_id: Optional[int] = None


class AppResponse(AppBase):
    id: int
    user_id: int
    status: str
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    port: Optional[int] = None
    subdomain: Optional[str] = None
    base_dockerfile_type: str = "auto"
    custom_base_image: Optional[str] = None
    custom_dockerfile_commands: Optional[str] = None
    git_credential_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    last_deployed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 배포 스키마
class DeploymentBase(BaseModel):
    commit_hash: Optional[str] = None
    status: str
    build_logs: Optional[str] = None
    error_message: Optional[str] = None


class DeploymentCreate(DeploymentBase):
    app_id: int


class DeploymentResponse(DeploymentBase):
    id: int
    app_id: int
    deployed_at: datetime

    class Config:
        from_attributes = True


# 환경변수 스키마
class EnvVarBase(BaseModel):
    key: str
    value: str


class EnvVarCreate(EnvVarBase):
    pass


class EnvVarResponse(EnvVarBase):
    id: int
    app_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# 앱 배포 요청 스키마
class AppDeployRequest(BaseModel):
    env_vars: Optional[Dict[str, str]] = None


# 앱 로그 응답 스키마
class AppLogsResponse(BaseModel):
    logs: str
    container_status: str


# Git 인증 정보 스키마
class GitCredentialBase(BaseModel):
    name: str
    git_provider: str  # github, gitlab, bitbucket
    auth_type: str  # token, ssh
    username: Optional[str] = None


class GitCredentialCreate(GitCredentialBase):
    token: Optional[str] = None  # 평문 토큰 (암호화되어 저장됨)
    ssh_key: Optional[str] = None  # 평문 SSH 키 (암호화되어 저장됨)


class GitCredentialUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    token: Optional[str] = None
    ssh_key: Optional[str] = None


class GitCredentialResponse(GitCredentialBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 앱 생성 시 Git 인증 정보 선택
class AppCreateWithAuth(AppBase):
    git_credential_id: Optional[int] = None
    base_dockerfile_type: str = "auto"  # auto, minimal, py311, py310
    custom_base_image: Optional[str] = None  # 사용자 정의 베이스 Docker 이미지
    custom_dockerfile_commands: Optional[str] = None  # 사용자 정의 Docker 명령어들

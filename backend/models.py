from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    apps = relationship("App", back_populates="user")


class App(Base):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    git_url = Column(String(500), nullable=False)
    branch = Column(String(100), default="main")
    main_file = Column(String(200), default="streamlit_app.py")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    git_credential_id = Column(Integer, ForeignKey("git_credentials.id"), nullable=True)
    base_dockerfile_type = Column(String(20), default="auto")  # auto, minimal, py311, py310
    custom_base_image = Column(String(200))  # 사용자 정의 베이스 Docker 이미지
    custom_dockerfile_commands = Column(Text)  # 사용자 정의 Docker 명령어들
    status = Column(String(20), default="stopped")  # stopped, building, deploying, running, error, stopping
    container_id = Column(String(100))
    image_name = Column(String(200))  # Docker 이미지 이름
    port = Column(Integer)
    subdomain = Column(String(100), unique=True)
    build_task_id = Column(String(100))  # Celery 빌드 태스크 ID
    deploy_task_id = Column(String(100))  # Celery 배포 태스크 ID
    stop_task_id = Column(String(100))  # Celery 중지 태스크 ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_deployed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="apps")
    deployments = relationship("Deployment", back_populates="app")
    env_vars = relationship("AppEnvVar", back_populates="app")
    git_credential = relationship("GitCredential")


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    commit_hash = Column(String(40))
    status = Column(String(20), nullable=False)  # success, failed, in_progress
    build_logs = Column(Text)
    error_message = Column(Text)
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())

    app = relationship("App", back_populates="deployments")


class AppEnvVar(Base):
    __tablename__ = "app_env_vars"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    app = relationship("App", back_populates="env_vars")


class GitCredential(Base):
    __tablename__ = "git_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)  # 사용자가 지정하는 이름
    git_provider = Column(String(50), nullable=False)  # github, gitlab, bitbucket 등
    auth_type = Column(String(20), nullable=False)  # token, ssh
    username = Column(String(100))  # HTTPS 인증용
    token_encrypted = Column(Text)  # 암호화된 토큰
    ssh_key_encrypted = Column(Text)  # 암호화된 SSH 키
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="git_credentials")


# User 모델에 관계 추가
User.git_credentials = relationship("GitCredential", back_populates="user")

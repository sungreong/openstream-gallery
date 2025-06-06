from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
import logging
from dotenv import load_dotenv

from database import get_db, engine
from models import Base
from routers import apps, auth, deployments, git_credentials, dockerfiles, nginx, celery_monitor
from services.docker_service import DockerService
from services.nginx_service import NginxService

load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Streamlit Platform API",
    description="Self-hosted Streamlit application deployment platform",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(apps.router, prefix="/api/apps", tags=["applications"])
app.include_router(deployments.router, prefix="/api/deployments", tags=["deployments"])
app.include_router(git_credentials.router, prefix="/api/git-credentials", tags=["git-credentials"])
app.include_router(dockerfiles.router, prefix="/api/dockerfiles", tags=["dockerfiles"])
app.include_router(nginx.router, prefix="/api/nginx", tags=["nginx"])
app.include_router(celery_monitor.router, prefix="/api/celery", tags=["celery-monitor"])

# 서비스 인스턴스 생성
logger.info("Docker 서비스 초기화 시작...")
docker_service = DockerService()
logger.info("Docker 서비스 초기화 완료")

logger.info("Nginx 서비스 초기화 시작...")
nginx_service = NginxService()
logger.info("Nginx 서비스 초기화 완료")


@app.get("/")
async def root():
    return {"message": "Streamlit Platform API"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    # 필요한 디렉토리 생성
    os.makedirs("/app/storage", exist_ok=True)
    os.makedirs("/app/nginx_config", exist_ok=True)

    # Nginx 기본 설정 생성
    await nginx_service.initialize_config()


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행되는 이벤트"""
    pass

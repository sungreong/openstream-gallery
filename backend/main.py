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

# 서비스 인스턴스 변수 (startup에서 초기화)
docker_service = None
nginx_service = None


def create_admin_user():
    """Admin 계정 생성/업데이트 함수"""
    print("=== ADMIN 계정 생성 시작 ===")
    logger.info("=== ADMIN 계정 생성 시작 ===")

    try:
        print("Admin 계정 생성 프로세스 시작...")
        logger.info("Admin 계정 생성 프로세스 시작...")

        db = next(get_db())
        from routers.auth import get_password_hash
        from models import User

        print("Admin 계정 확인 시작...")
        logger.info("Admin 계정 확인 시작...")

        # 기존 admin 계정 확인
        admin = db.query(User).filter(User.username == "admin").first()

        if not admin:
            # admin 계정이 없으면 생성
            print("Admin 계정이 없습니다. 새로 생성합니다.")
            logger.info("Admin 계정이 없습니다. 새로 생성합니다.")
            admin_password_hash = get_password_hash("admin123")
            admin = User(username="admin", email="admin@example.com", password_hash=admin_password_hash)
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Admin 계정 생성 완료 - ID: {admin.id}")
            logger.info(f"Admin 계정 생성 완료 - ID: {admin.id}")
        else:
            # admin 계정이 있으면 비밀번호를 admin123으로 확실히 설정
            print(f"기존 Admin 계정 발견 - ID: {admin.id}")
            logger.info(f"기존 Admin 계정 발견 - ID: {admin.id}")
            admin.password_hash = get_password_hash("admin123")
            db.commit()
            print("Admin 계정 비밀번호 업데이트 완료")
            logger.info("Admin 계정 비밀번호 업데이트 완료")

        # 검증: admin 계정이 제대로 생성되었는지 확인
        admin_check = db.query(User).filter(User.username == "admin").first()
        if admin_check:
            print(f"Admin 계정 검증 성공 - Username: {admin_check.username}, Email: {admin_check.email}")
            logger.info(f"Admin 계정 검증 성공 - Username: {admin_check.username}, Email: {admin_check.email}")
        else:
            print("Admin 계정 검증 실패!")
            logger.error("Admin 계정 검증 실패!")

        db.close()

    except Exception as e:
        print(f"Admin 계정 설정 중 오류 발생: {str(e)}")
        logger.error(f"Admin 계정 설정 중 오류 발생: {str(e)}")
        import traceback

        print(f"상세 오류: {traceback.format_exc()}")
        logger.error(f"상세 오류: {traceback.format_exc()}")

    print("=== ADMIN 계정 생성 완료 ===")
    logger.info("=== ADMIN 계정 생성 완료 ===")


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


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    global docker_service, nginx_service

    print("=== STARTUP EVENT 시작 ===")
    logger.info("=== STARTUP EVENT 시작 ===")

    try:
        # 필요한 디렉토리 생성
        print("필요한 디렉토리 생성 중...")
        logger.info("필요한 디렉토리 생성 중...")
        os.makedirs("/app/storage", exist_ok=True)
        os.makedirs("/app/nginx_config", exist_ok=True)

        # Docker 서비스 초기화
        print("Docker 서비스 초기화 시작...")
        logger.info("Docker 서비스 초기화 시작...")
        docker_service = DockerService()
        print("Docker 서비스 초기화 완료")
        logger.info("Docker 서비스 초기화 완료")

        # Nginx 서비스 초기화
        print("Nginx 서비스 초기화 시작...")
        logger.info("Nginx 서비스 초기화 시작...")
        nginx_service = NginxService()
        print("Nginx 서비스 초기화 완료")
        logger.info("Nginx 서비스 초기화 완료")

        # Nginx 기본 설정 생성
        print("Nginx 기본 설정 생성 중...")
        logger.info("Nginx 기본 설정 생성 중...")
        await nginx_service.initialize_config()
        print("Nginx 기본 설정 생성 완료")
        logger.info("Nginx 기본 설정 생성 완료")

        # Admin 계정 생성
        create_admin_user()

    except Exception as e:
        print(f"Startup 중 오류 발생: {str(e)}")
        logger.error(f"Startup 중 오류 발생: {str(e)}")
        import traceback

        print(f"상세 오류: {traceback.format_exc()}")
        logger.error(f"상세 오류: {traceback.format_exc()}")

    print("=== STARTUP EVENT 완료 ===")
    logger.info("=== STARTUP EVENT 완료 ===")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행되는 이벤트"""
    print("=== SHUTDOWN EVENT ===")
    logger.info("=== SHUTDOWN EVENT ===")


@app.get("/")
async def root():
    return {"message": "Streamlit Platform API"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

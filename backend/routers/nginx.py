from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
import logging
from pydantic import BaseModel

from services.nginx_service import NginxService
from services.docker_service import DockerService
from database import get_db
from sqlalchemy.orm import Session
from models import App

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nginx"])


# Pydantic 모델들
class CleanupRequest(BaseModel):
    active_apps: List[str]


class RemoveConfigRequest(BaseModel):
    subdomain: str


@router.get("/dynamic")
async def get_dynamic_configs():
    """
    Dynamic 폴더 내 모든 설정 파일 정보 조회
    """
    try:
        nginx_service = NginxService()
        configs = await nginx_service.get_dynamic_configs()

        return {
            "success": True,
            "data": configs,
            "message": f"총 {configs['total_count']}개의 설정 파일 (앱: {configs['app_count']}개, 시스템: {len(configs['system_files'])}개)",
        }

    except Exception as e:
        logger.error(f"Dynamic 설정 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dynamic 설정 조회 실패: {str(e)}")


@router.get("/dynamic/apps")
async def get_app_configs():
    """
    현재 설정된 앱 목록만 반환
    """
    try:
        nginx_service = NginxService()
        app_configs = await nginx_service.get_app_configs()

        return {
            "success": True,
            "data": {"app_configs": app_configs, "count": len(app_configs)},
            "message": f"{len(app_configs)}개의 앱 설정이 있습니다.",
        }

    except Exception as e:
        logger.error(f"앱 설정 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"앱 설정 목록 조회 실패: {str(e)}")


@router.post("/cleanup")
async def cleanup_unused_configs(request: CleanupRequest):
    """
    실제 서비스 중인 앱들만 남기고 나머지 설정 파일 삭제 후 reload
    """
    try:
        nginx_service = NginxService()
        result = await nginx_service.cleanup_unused_configs(request.active_apps)

        if result["success"]:
            return {"success": True, "data": result, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"설정 파일 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"설정 파일 정리 실패: {str(e)}")


@router.post("/cleanup/auto")
async def auto_cleanup_configs(db: Session = Depends(get_db)):
    """
    데이터베이스의 활성 앱들을 기준으로 자동 정리
    """
    try:
        # 데이터베이스에서 활성 앱 목록 조회
        active_apps_query = db.query(App).filter(App.status == "running").all()
        active_apps = [app.subdomain for app in active_apps_query]

        logger.info(f"📋 데이터베이스에서 조회한 활성 앱: {active_apps}")

        nginx_service = NginxService()
        result = await nginx_service.cleanup_unused_configs(active_apps)

        if result["success"]:
            return {"success": True, "data": result, "message": f"자동 정리 완료: {result['message']}"}
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"자동 설정 파일 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"자동 설정 파일 정리 실패: {str(e)}")


@router.post("/cleanup/validate")
async def validate_and_cleanup_configs():
    """
    모든 설정 파일을 검증하고 문제가 있는 파일들을 자동 삭제
    """
    try:
        nginx_service = NginxService()
        result = await nginx_service.validate_and_cleanup_configs()

        if result["success"]:
            return {"success": True, "data": result, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"설정 파일 검증 및 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"설정 파일 검증 및 정리 실패: {str(e)}")


@router.get("/configs/status")
async def get_all_app_configs_status():
    """
    모든 앱 설정 파일의 상태 확인
    """
    try:
        nginx_service = NginxService()
        result = await nginx_service.get_all_app_configs_status()

        if result["success"]:
            return {"success": True, "data": result}
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"앱 설정 상태 확인 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"앱 설정 상태 확인 실패: {str(e)}")


@router.get("/configs/status/{app_name}")
async def get_app_config_status(app_name: str):
    """
    특정 앱 설정 파일의 상태 확인
    """
    try:
        nginx_service = NginxService()
        result = await nginx_service.get_app_config_status(app_name)
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"앱 설정 상태 확인 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"앱 설정 상태 확인 실패: {str(e)}")


@router.delete("/apps/{app_name}/complete")
async def remove_app_and_container(app_name: str):
    """
    앱 설정 파일과 연결된 컨테이너를 함께 삭제
    """
    try:
        nginx_service = NginxService()
        result = await nginx_service.remove_app_and_container(app_name)

        if result["success"]:
            return {"success": True, "data": result, "message": result["message"]}
        else:
            return {"success": False, "data": result, "message": result["message"]}

    except Exception as e:
        logger.error(f"앱 및 컨테이너 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"앱 및 컨테이너 삭제 실패: {str(e)}")


@router.delete("/config/{subdomain}")
async def remove_specific_config(subdomain: str):
    """
    특정 설정 파일 삭제
    """
    try:
        nginx_service = NginxService()
        result = await nginx_service.remove_specific_config(subdomain)

        if result["success"]:
            return {"success": True, "data": result, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"특정 설정 파일 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"특정 설정 파일 삭제 실패: {str(e)}")


@router.post("/reload")
async def reload_nginx():
    """
    Nginx 설정 리로드
    """
    try:
        nginx_service = NginxService()
        await nginx_service.reload_nginx()

        return {"success": True, "message": "Nginx 설정이 성공적으로 리로드되었습니다."}

    except Exception as e:
        logger.error(f"Nginx 리로드 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Nginx 리로드 실패: {str(e)}")


@router.get("/test")
async def test_nginx_config():
    """
    Nginx 설정 파일 유효성 검사
    """
    try:
        nginx_service = NginxService()
        is_valid = await nginx_service.test_nginx_config()

        return {
            "success": True,
            "data": {"is_valid": is_valid},
            "message": "Nginx 설정이 유효합니다." if is_valid else "Nginx 설정에 오류가 있습니다.",
        }

    except Exception as e:
        logger.error(f"Nginx 설정 테스트 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Nginx 설정 테스트 실패: {str(e)}")

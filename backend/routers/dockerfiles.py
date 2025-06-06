from fastapi import APIRouter, HTTPException
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/base-types")
async def get_base_dockerfile_types():
    """사용 가능한 베이스 Dockerfile 타입 목록 조회"""
    try:
        base_dockerfiles = [
            {
                "type": "simple",
                "name": "간단 버전 (Python 3.11)",
                "description": "간단한 앱용 - 기본 패키지만 포함",
                "dockerfile": "Dockerfile.simple",
                "recommended_for": ["간단한 앱", "적은 의존성", "빠른 빌드"],
            },
            {
                "type": "minimal",
                "name": "최소 버전 (Python 3.11 Slim)",
                "description": "가벼운 앱용 - 기본 패키지만 포함",
                "dockerfile": "Dockerfile.minimal",
                "recommended_for": ["간단한 앱", "적은 의존성", "빠른 빌드"],
            },
            {
                "type": "py309",
                "name": "데이터사이언스 버전 (Python 3.9)",
                "description": "데이터 분석용 - 수치 계산 라이브러리 사전 설치",
                "dockerfile": "Dockerfile.py309",
                "recommended_for": ["데이터 분석", "머신러닝", "과학 계산", "numpy/pandas 사용"],
            },
            {
                "type": "py310",
                "name": "데이터사이언스 버전 (Python 3.10)",
                "description": "데이터 분석용 - 수치 계산 라이브러리 사전 설치",
                "dockerfile": "Dockerfile.py310",
                "recommended_for": ["데이터 분석", "머신러닝", "과학 계산", "numpy/pandas 사용"],
            },
            {
                "type": "py311",
                "name": "표준 버전 (Python 3.11)",
                "description": "일반적인 앱용 - 컴파일 도구 포함",
                "dockerfile": "Dockerfile.py311",
                "recommended_for": ["일반적인 앱", "중간 수준 의존성", "안정성 중시"],
            },
        ]

        return {"success": True, "base_dockerfiles": base_dockerfiles}
    except Exception as e:
        logger.error(f"베이스 Dockerfile 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"베이스 Dockerfile 목록 조회 실패: {str(e)}")


@router.get("/base-types/{dockerfile_type}")
async def get_base_dockerfile_info(dockerfile_type: str):
    """특정 베이스 Dockerfile 타입의 상세 정보 조회"""
    try:
        dockerfile_info = {
            "minimal": {
                "type": "minimal",
                "name": "최소 버전 (Python 3.11 Slim)",
                "description": "가벼운 앱용 - 기본 패키지만 포함",
                "dockerfile": "Dockerfile.minimal",
                "recommended_for": ["간단한 앱", "적은 의존성", "빠른 빌드"],
                "base_image": "python:3.11-slim",
                "features": ["기본 Python 환경", "Streamlit", "최소 시스템 패키지"],
            },
            "py311": {
                "type": "py311",
                "name": "표준 버전 (Python 3.11)",
                "description": "일반적인 앱용 - 컴파일 도구 포함",
                "dockerfile": "Dockerfile.py311",
                "recommended_for": ["일반적인 앱", "중간 수준 의존성", "안정성 중시"],
                "base_image": "python:3.11",
                "features": ["Python 3.11", "컴파일 도구", "Streamlit", "일반적인 패키지 지원"],
            },
            "py310": {
                "type": "py310",
                "name": "데이터사이언스 버전 (Python 3.10)",
                "description": "데이터 분석용 - 수치 계산 라이브러리 사전 설치",
                "dockerfile": "Dockerfile.py310",
                "recommended_for": ["데이터 분석", "머신러닝", "과학 계산", "numpy/pandas 사용"],
                "base_image": "python:3.10",
                "features": ["Python 3.10", "numpy", "pandas", "scipy", "컴파일 도구", "과학 계산 라이브러리"],
            },
            "py309": {
                "type": "py309",
                "name": "데이터사이언스 버전 (Python 3.9)",
                "description": "데이터 분석용 - 수치 계산 라이브러리 사전 설치",
                "dockerfile": "Dockerfile.py309",
                "recommended_for": ["데이터 분석", "머신러닝", "과학 계산", "numpy/pandas 사용"],
                "base_image": "python:3.9",
                "features": ["Python 3.9", "numpy", "pandas", "scipy", "컴파일 도구", "과학 계산 라이브러리"],
            },
        }

        if dockerfile_type not in dockerfile_info:
            raise HTTPException(
                status_code=404, detail=f"베이스 Dockerfile 타입을 찾을 수 없습니다: {dockerfile_type}"
            )

        return {"success": True, "dockerfile_info": dockerfile_info[dockerfile_type]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"베이스 Dockerfile 정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"베이스 Dockerfile 정보 조회 실패: {str(e)}")


@router.get("/base-content/{dockerfile_type}")
async def get_base_dockerfile_content(dockerfile_type: str):
    """특정 베이스 Dockerfile의 실제 내용 조회"""
    try:
        # 베이스 Dockerfile 파일 경로
        dockerfile_mapping = {
            "simple": "Dockerfile.simple",
            "minimal": "Dockerfile.minimal",
            "py309": "Dockerfile.py309",
            "py310": "Dockerfile.py310",
            "py311": "Dockerfile.py311",
        }

        if dockerfile_type not in dockerfile_mapping:
            raise HTTPException(
                status_code=404, detail=f"베이스 Dockerfile 타입을 찾을 수 없습니다: {dockerfile_type}"
            )

        dockerfile_filename = dockerfile_mapping[dockerfile_type]
        dockerfile_path = os.path.join("/app/dockerfiles", dockerfile_filename)

        if not os.path.exists(dockerfile_path):
            raise HTTPException(
                status_code=404, detail=f"베이스 Dockerfile 파일을 찾을 수 없습니다: {dockerfile_filename}"
            )

        # 파일 내용 읽기
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 베이스 정보도 함께 반환
        base_info = {
            "simple": {
                "name": "간단 버전 (Python 3.11)",
                "description": "간단한 앱용 - 기본 패키지만 포함",
                "base_image": "python:3.11",
                "features": ["Python 3.11", "Streamlit", "기본 패키지"],
            },
            "minimal": {
                "name": "최소 버전 (Python 3.11 Slim)",
                "description": "가벼운 앱용 - 기본 패키지만 포함",
                "base_image": "python:3.11-slim",
                "features": ["Python 3.11 Slim", "Streamlit", "최소 시스템 패키지"],
            },
            "py309": {
                "name": "데이터사이언스 버전 (Python 3.9)",
                "description": "데이터 분석용 - 수치 계산 라이브러리 사전 설치",
                "base_image": "python:3.9",
            },
            "py310": {
                "name": "데이터사이언스 버전 (Python 3.10)",
                "description": "데이터 분석용 - 수치 계산 라이브러리 사전 설치",
                "base_image": "python:3.10",
            },
            "py311": {
                "name": "표준 버전 (Python 3.11)",
                "description": "일반적인 앱용 - 컴파일 도구 포함",
                "base_image": "python:3.11",
                "features": ["Python 3.11", "컴파일 도구", "Streamlit", "일반적인 패키지 지원"],
            },
        }

        return {
            "success": True,
            "dockerfile_type": dockerfile_type,
            "filename": dockerfile_filename,
            "content": content,
            "info": base_info.get(dockerfile_type, {}),
            "lines": len(content.split("\n")),
            "size": len(content.encode("utf-8")),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"베이스 Dockerfile 내용 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"베이스 Dockerfile 내용 조회 실패: {str(e)}")

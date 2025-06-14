from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()


class DockerfilePreviewRequest(BaseModel):
    base_dockerfile_type: str = "auto"
    custom_base_image: Optional[str] = None
    custom_dockerfile_commands: Optional[str] = None
    main_file: str = "app.py"
    git_url: Optional[str] = None


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


@router.post("/preview-final")
async def preview_final_dockerfile(request: DockerfilePreviewRequest):
    """최종 Dockerfile 미리보기 생성"""
    try:
        # 사용자 정의 베이스 이미지 사용 여부 확인
        if request.custom_base_image and request.custom_base_image.strip():
            # 사용자 정의 베이스 이미지로 완전한 Dockerfile 생성
            dockerfile_content = _generate_custom_base_dockerfile_preview(
                request.custom_base_image, request.main_file, request.custom_dockerfile_commands
            )
            dockerfile_type = "custom"
            base_info = {
                "name": f"사용자 정의 ({request.custom_base_image})",
                "description": "사용자가 직접 지정한 베이스 이미지",
                "base_image": request.custom_base_image,
                "features": ["사용자 정의 베이스 이미지", "완전한 Dockerfile"],
            }
        else:
            # 기존 베이스 Dockerfile 선택 및 읽기
            if request.base_dockerfile_type == "auto":
                selected_type = "simple"
                logger.info(f"자동 선택된 베이스 Dockerfile: {selected_type}")
            else:
                selected_type = request.base_dockerfile_type
                logger.info(f"사용자 선택 베이스 Dockerfile: {selected_type}")

            base_dockerfile_content = _read_base_dockerfile_content(selected_type)

            # 앱별 추가 내용 생성
            app_specific_content = _generate_app_specific_content_preview(
                request.main_file, request.custom_dockerfile_commands, request.git_url
            )

            # 최종 Dockerfile 내용 조합
            dockerfile_content = base_dockerfile_content + "\n\n" + app_specific_content
            dockerfile_type = selected_type

            # 베이스 정보 가져오기
            base_info_mapping = {
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
                    "features": ["Python 3.9", "numpy", "pandas", "scipy", "컴파일 도구"],
                },
                "py310": {
                    "name": "데이터사이언스 버전 (Python 3.10)",
                    "description": "데이터 분석용 - 수치 계산 라이브러리 사전 설치",
                    "base_image": "python:3.10",
                    "features": ["Python 3.10", "numpy", "pandas", "scipy", "컴파일 도구"],
                },
                "py311": {
                    "name": "표준 버전 (Python 3.11)",
                    "description": "일반적인 앱용 - 컴파일 도구 포함",
                    "base_image": "python:3.11",
                    "features": ["Python 3.11", "컴파일 도구", "Streamlit", "일반적인 패키지 지원"],
                },
            }
            base_info = base_info_mapping.get(dockerfile_type, {})

        # 메타데이터 추가
        from datetime import datetime

        dockerfile_content = dockerfile_content.replace(
            "# 메타데이터",
            f"""# 메타데이터
LABEL app.main_file="{request.main_file}"
LABEL app.created="{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
LABEL app.has_custom_commands="{'true' if request.custom_dockerfile_commands else 'false'}"
LABEL app.custom_base_image="{'true' if request.custom_base_image else 'false'}\"""",
        )

        return {
            "success": True,
            "dockerfile_type": dockerfile_type,
            "content": dockerfile_content,
            "info": base_info,
            "lines": len(dockerfile_content.split("\n")),
            "size": len(dockerfile_content.encode("utf-8")),
            "sections": {
                "has_base": not (request.custom_base_image and request.custom_base_image.strip()),
                "has_custom_commands": bool(
                    request.custom_dockerfile_commands and request.custom_dockerfile_commands.strip()
                ),
                "has_app_specific": True,
            },
        }

    except Exception as e:
        logger.error(f"최종 Dockerfile 미리보기 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"최종 Dockerfile 미리보기 생성 실패: {str(e)}")


def _read_base_dockerfile_content(dockerfile_type: str) -> str:
    """베이스 Dockerfile 내용 읽기"""
    dockerfile_mapping = {
        "simple": "Dockerfile.simple",
        "minimal": "Dockerfile.minimal",
        "py309": "Dockerfile.py309",
        "py310": "Dockerfile.py310",
        "py311": "Dockerfile.py311",
    }

    dockerfile_filename = dockerfile_mapping.get(dockerfile_type, "Dockerfile.simple")
    dockerfile_path = os.path.join("/app/dockerfiles", dockerfile_filename)

    try:
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"베이스 Dockerfile 파일을 찾을 수 없음: {dockerfile_path}")
        return f"# 베이스 Dockerfile ({dockerfile_type})\nFROM python:3.11\n"


def _generate_custom_base_dockerfile_preview(
    custom_base_image: str, main_file: str, custom_commands: str = None
) -> str:
    """사용자 정의 베이스 이미지로 완전한 Dockerfile 생성"""
    dockerfile_content = f"""# 사용자 정의 베이스 이미지 Dockerfile
FROM {custom_base_image}

# 메타데이터

# 시스템 업데이트 및 기본 패키지 설치
RUN apt-get update && apt-get install -y \\
    curl \\
    wget \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 사용자 정의 명령어 (있는 경우)"""

    if custom_commands and custom_commands.strip():
        dockerfile_content += f"\n{custom_commands.strip()}\n"
    else:
        dockerfile_content += """
# Python 패키지 설치 (기본)
RUN pip install --no-cache-dir streamlit

"""

    dockerfile_content += f"""
# 앱 파일 복사
COPY . /app/

# requirements.txt가 있으면 설치
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# 포트 노출
EXPOSE 8501

# Streamlit 실행
CMD ["streamlit", "run", "{main_file}", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
"""

    return dockerfile_content


def _generate_app_specific_content_preview(main_file: str, custom_commands: str = None, git_url: str = None) -> str:
    """앱별 추가 내용 생성"""

    content = """# 앱별 설정 및 파일 복사
WORKDIR /app

# Git 저장소 클론 (실제 배포 시)"""

    if git_url:
        content += f"""
# RUN git clone {git_url} .
"""

    content += """

# 사용자 정의 명령어"""

    if custom_commands and custom_commands.strip():
        content += f"""
{custom_commands.strip()}

"""
    else:
        content += """
# (사용자 정의 명령어 없음)

"""

    content += f"""# 앱 파일 복사
COPY . /app/

# requirements.txt 설치
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# 메타데이터

# 포트 노출
EXPOSE 8501

# Streamlit 실행
CMD ["streamlit", "run", "{main_file}", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
"""

    return content

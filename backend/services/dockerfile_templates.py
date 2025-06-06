# Dockerfile 템플릿 관리
from typing import Dict, List
import logging
from .base_image_manager import BaseImageManager

logger = logging.getLogger(__name__)


class DockerfileTemplates:
    """다양한 상황에 맞는 Dockerfile 템플릿을 제공하는 클래스"""

    @staticmethod
    def get_base_template() -> str:
        """동적으로 빌드되는 기본 템플릿"""
        return """# 자동 생성된 Dockerfile for Streamlit App
# 베이스 이미지: {{ base_image }}
# 메인 파일: {{ main_file }}
# 생성 시간: {{ timestamp }}

FROM {{ base_image }}

# 메타데이터
LABEL app.type="streamlit"
LABEL app.main_file="{{ main_file }}"
LABEL app.created="{{ timestamp }}"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 기본 도구 설치
RUN apt-get update && apt-get install -y \\
    curl \\
    wget \\
    git \\
    procps \\
{% if template_type == 'datascience' %}
    build-essential \\
    gcc \\
    g++ \\
    gfortran \\
    libopenblas-dev \\
    liblapack-dev \\
    libhdf5-dev \\
    libhdf5-serial-dev \\
    pkg-config \\
    libffi-dev \\
    libssl-dev \\
{% elif template_type == 'standard' %}
    build-essential \\
    gcc \\
    g++ \\
{% endif %}
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드 및 기본 도구 설치
RUN pip install --upgrade pip setuptools wheel{% if template_type == 'datascience' %} cython{% endif %}

# 기본 환경 설정
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONUNBUFFERED=1

{% if template_type == 'datascience' %}
# 기본 수치 계산 라이브러리 먼저 설치 (안정적인 버전)
RUN pip install --no-cache-dir \\
    numpy==1.24.3 \\
    pandas==2.0.3 \\
    scipy==1.11.1

{% endif %}
# Streamlit 설치 (안정 버전)
RUN pip install --no-cache-dir streamlit==1.28.1

{% if has_requirements %}
# requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

{% endif %}
# 애플리케이션 파일 복사
COPY . .

# 불필요한 파일 제거
RUN find . -name "*.pyc" -delete && \\
    find . -name "__pycache__" -type d -exec rm -rf {} + || true

# 포트 노출
EXPOSE 8501

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout={% if template_type == 'datascience' %}15{% else %}10{% endif %}s --start-period={% if template_type == 'datascience' %}60{% elif template_type == 'minimal' %}15{% else %}30{% endif %}s --retries=3 \\
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 실행 사용자 설정 (보안)
RUN useradd -m -u 1000 streamlit && \\
    chown -R streamlit:streamlit /app
USER streamlit

# 실행 명령어
ENTRYPOINT ["streamlit", "run", "{{ main_file }}", \\
    "--server.port=8501", \\
    "--server.address=0.0.0.0", \\
    "--server.headless=true", \\
    "--server.enableCORS=false", \\
    "--server.enableXsrfProtection=false"]
"""

    @staticmethod
    def get_data_science_template() -> str:
        """데이터 사이언스 패키지가 많은 앱용 템플릿"""
        return """# 데이터 사이언스 Streamlit 앱용 Dockerfile
FROM python:3.11

# 메타데이터
LABEL maintainer="Streamlit Platform"
LABEL app.type="streamlit-datascience"
LABEL app.main_file="{{ main_file }}"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (데이터 사이언스 패키지용)
RUN apt-get update && apt-get install -y \\
    build-essential \\
    gcc \\
    g++ \\
    gfortran \\
    libopenblas-dev \\
    liblapack-dev \\
    libhdf5-dev \\
    pkg-config \\
    curl \\
    wget \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# pip 및 빌드 도구 업그레이드
RUN pip install --upgrade pip setuptools wheel cython

# 기본 수치 계산 라이브러리 먼저 설치
RUN pip install --no-cache-dir \\
    numpy==1.24.3 \\
    pandas==2.0.3 \\
    scipy==1.11.1

{% if has_requirements %}
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
{% endif %}

# Streamlit 설치
RUN pip install streamlit==1.28.1

COPY . .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \\
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

RUN useradd -m -u 1000 streamlit && chown -R streamlit:streamlit /app
USER streamlit

ENTRYPOINT ["streamlit", "run", "{{ main_file }}", \\
    "--server.port=8501", \\
    "--server.address=0.0.0.0", \\
    "--server.headless=true", \\
    "--server.enableCORS=false"]
"""

    @staticmethod
    def get_minimal_template() -> str:
        """최소한의 의존성만 있는 앱용 템플릿"""
        return """# 최소 Streamlit 앱용 Dockerfile
FROM python:3.11-slim

LABEL maintainer="Streamlit Platform"
LABEL app.type="streamlit-minimal"

WORKDIR /app

RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

{% if has_requirements %}
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
{% endif %}

RUN pip install streamlit==1.28.1

COPY . .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \\
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

RUN useradd -m -u 1000 streamlit && chown -R streamlit:streamlit /app
USER streamlit

ENTRYPOINT ["streamlit", "run", "{{ main_file }}", \\
    "--server.port=8501", \\
    "--server.address=0.0.0.0", \\
    "--server.headless=true"]
"""

    @classmethod
    def select_template(cls, problematic_packages: List[str], requirements_size: int) -> str:
        """상황에 맞는 템플릿 선택"""

        # 데이터 사이언스 패키지가 많은 경우
        data_science_packages = [
            "numpy",
            "pandas",
            "scipy",
            "matplotlib",
            "seaborn",
            "scikit-learn",
            "tensorflow",
            "torch",
            "opencv",
        ]
        has_data_science = any(
            any(ds_pkg in pkg.lower() for ds_pkg in data_science_packages) for pkg in problematic_packages
        )

        if has_data_science or len(problematic_packages) > 3:
            logger.info("📊 데이터 사이언스 템플릿 선택")
            return cls.get_data_science_template()
        elif len(problematic_packages) == 0 and requirements_size < 10:
            logger.info("🪶 최소 템플릿 선택")
            return cls.get_minimal_template()
        else:
            logger.info("🎯 기본 템플릿 선택")
            return cls.get_base_template()

    @staticmethod
    def get_base_image(problematic_packages: List[str]) -> str:
        """패키지 상황에 맞는 베이스 이미지 선택"""

        # 컴파일이 필요한 패키지가 있으면 전체 이미지 사용
        if problematic_packages:
            return "python:3.11"
        else:
            return "python:3.11-slim"

#!/usr/bin/env python3
"""
Dockerfile 생성 테스트 스크립트
베이스 Dockerfile을 읽어서 앱별 내용을 추가하는 방식을 테스트합니다.
"""

import sys
import os
import tempfile
import shutil

# 백엔드 모듈 경로 추가
sys.path.append("backend")

from services.docker_service import DockerService


def test_dockerfile_generation():
    """Dockerfile 생성 테스트"""
    print("🧪 Dockerfile 생성 테스트 시작")

    # 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp()
    print(f"📁 임시 디렉토리: {temp_dir}")

    try:
        # 테스트용 requirements.txt 생성
        requirements_content = """pandas==2.0.3
numpy==1.24.3
streamlit==1.28.1
matplotlib==3.7.1
seaborn==0.12.2"""

        with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
            f.write(requirements_content)
        print("📝 테스트용 requirements.txt 생성 완료")

        # DockerService 인스턴스 생성
        docker_service = DockerService()

        # Dockerfile 생성 테스트
        print("🔨 Dockerfile 생성 중...")
        dockerfile_path = docker_service.generate_dockerfile(temp_dir, "app.py")
        print(f"✅ Dockerfile 생성 성공: {dockerfile_path}")

        # 생성된 Dockerfile 내용 출력
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        print("\n" + "=" * 50)
        print("📄 생성된 Dockerfile 내용")
        print("=" * 50)
        print(content)
        print("=" * 50)

        # 파일 크기 정보
        file_size = len(content)
        line_count = content.count("\n")
        print(f"📊 Dockerfile 정보:")
        print(f"  - 파일 크기: {file_size} bytes")
        print(f"  - 줄 수: {line_count} lines")

        return True

    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # 정리
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("🧹 임시 파일 정리 완료")


if __name__ == "__main__":
    success = test_dockerfile_generation()
    if success:
        print("🎉 테스트 성공!")
        sys.exit(0)
    else:
        print("💥 테스트 실패!")
        sys.exit(1)

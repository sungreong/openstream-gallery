# 베이스 이미지 관리 시스템
import os
import subprocess
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseImageManager:
    """베이스 이미지 빌드 및 관리를 담당하는 클래스"""

    def __init__(self):
        self.dockerfiles_dir = "/app/dockerfiles"
        self.base_images = {
            "minimal": {
                "dockerfile": "Dockerfile.minimal",
                "image_name": "streamlit-platform-base:minimal",
                "description": "최소 의존성 베이스 이미지",
            },
            "standard": {
                "dockerfile": "Dockerfile.py311",
                "image_name": "streamlit-platform-base:py311",
                "description": "표준 Python 3.11 베이스 이미지",
            },
            "datascience": {
                "dockerfile": "Dockerfile.py310",
                "image_name": "streamlit-platform-base:datascience",
                "description": "데이터사이언스용 베이스 이미지",
            },
        }

    def _run_docker_command(self, cmd: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
        """Docker 명령어 실행"""
        full_cmd = ["docker"] + cmd
        logger.info(f"🔧 Docker 명령어 실행: {' '.join(full_cmd)}")
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                logger.debug(f"✅ Docker 명령어 성공")
            else:
                logger.warning(f"⚠️ Docker 명령어 실패 (종료코드: {result.returncode})")
                if result.stderr:
                    logger.warning(f"stderr: {result.stderr[:500]}...")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Docker 명령어 시간 초과 ({timeout}초)")
            raise Exception(f"Docker 명령어 실행 시간 초과 ({timeout}초)")
        except Exception as e:
            logger.error(f"💥 Docker 명령어 실행 실패: {str(e)}")
            raise Exception(f"Docker 명령어 실행 실패: {str(e)}")

    def check_base_image_exists(self, image_type: str) -> bool:
        """베이스 이미지가 존재하는지 확인"""
        if image_type not in self.base_images:
            return False

        image_name = self.base_images[image_type]["image_name"]
        try:
            result = self._run_docker_command(["images", "-q", image_name])
            exists = bool(result.stdout.strip())
            logger.info(f"🔍 베이스 이미지 '{image_name}' 존재 여부: {exists}")
            return exists
        except Exception as e:
            logger.warning(f"⚠️ 베이스 이미지 확인 실패: {str(e)}")
            return False

    def build_base_image(self, image_type: str) -> bool:
        """베이스 이미지 빌드"""
        if image_type not in self.base_images:
            logger.error(f"❌ 알 수 없는 이미지 타입: {image_type}")
            return False

        base_info = self.base_images[image_type]
        dockerfile_path = os.path.join(self.dockerfiles_dir, base_info["dockerfile"])

        if not os.path.exists(dockerfile_path):
            logger.error(f"❌ Dockerfile을 찾을 수 없음: {dockerfile_path}")
            return False

        logger.info(f"🔨 베이스 이미지 빌드 시작")
        logger.info(f"  - 타입: {image_type}")
        logger.info(f"  - 이미지명: {base_info['image_name']}")
        logger.info(f"  - Dockerfile: {dockerfile_path}")
        logger.info(f"  - 설명: {base_info['description']}")

        try:
            # 베이스 이미지 빌드 (타임아웃 10분)
            result = self._run_docker_command(
                [
                    "build",
                    "-f",
                    dockerfile_path,
                    "-t",
                    base_info["image_name"],
                    "--rm",
                    "--force-rm",
                    self.dockerfiles_dir,
                ],
                timeout=600,
            )

            if result.returncode == 0:
                logger.info(f"✅ 베이스 이미지 빌드 성공: {base_info['image_name']}")
                return True
            else:
                logger.error(f"❌ 베이스 이미지 빌드 실패")
                logger.error(f"stderr: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ 베이스 이미지 빌드 중 에러: {str(e)}")
            return False

    def ensure_base_image(self, image_type: str) -> str:
        """베이스 이미지가 존재하는지 확인하고, 없으면 빌드"""
        if not self.check_base_image_exists(image_type):
            logger.info(f"🏗️ 베이스 이미지가 없어서 빌드를 시작합니다: {image_type}")
            if not self.build_base_image(image_type):
                raise Exception(f"베이스 이미지 빌드 실패: {image_type}")

        return self.base_images[image_type]["image_name"]

    def select_base_image_type(self, problematic_packages: List[str], requirements_size: int) -> str:
        """패키지 상황에 맞는 베이스 이미지 타입 선택"""

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
            logger.info("📊 데이터사이언스 베이스 이미지 선택")
            return "datascience"
        elif len(problematic_packages) == 0 and requirements_size < 5:
            logger.info("🪶 최소 베이스 이미지 선택")
            return "minimal"
        else:
            logger.info("🎯 표준 베이스 이미지 선택")
            return "standard"

    def get_all_base_images(self) -> Dict[str, Dict]:
        """모든 베이스 이미지 정보 반환"""
        return self.base_images.copy()

    def cleanup_old_images(self, keep_latest: int = 2):
        """오래된 베이스 이미지 정리"""
        logger.info(f"🧹 오래된 베이스 이미지 정리 시작 (최신 {keep_latest}개 유지)")

        for image_type, base_info in self.base_images.items():
            try:
                # 해당 베이스 이미지의 모든 태그 조회
                result = self._run_docker_command(
                    [
                        "images",
                        "--format",
                        "{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}",
                        base_info["image_name"].split(":")[0],
                    ]
                )

                if result.returncode == 0 and result.stdout.strip():
                    images = result.stdout.strip().split("\n")
                    if len(images) > keep_latest:
                        # 생성 시간 기준으로 정렬하여 오래된 것들 삭제
                        images_to_remove = images[keep_latest:]
                        for image_line in images_to_remove:
                            image_name = image_line.split("\t")[0]
                            logger.info(f"🗑️ 오래된 이미지 삭제: {image_name}")
                            self._run_docker_command(["rmi", image_name])

            except Exception as e:
                logger.warning(f"⚠️ 이미지 정리 중 에러 ({image_type}): {str(e)}")

        logger.info("✅ 베이스 이미지 정리 완료")

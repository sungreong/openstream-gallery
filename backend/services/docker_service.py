import docker
import os
import shutil
import tempfile
import random
import subprocess
import json
import time
from git import Repo
from jinja2 import Template
from typing import Optional, Dict, List
import logging
from .dockerfile_templates import DockerfileTemplates

logger = logging.getLogger(__name__)


class DockerService:
    def __init__(self):
        self.client = None
        self.use_cli = True
        self._initialize_docker_client()

        # 환경변수에서 네트워크 이름 가져오기 (기본값: 자동 감지)
        self.network_name = os.getenv("DOCKER_NETWORK_NAME", "auto")
        self.base_port = 8501
        self.max_port = 9000

        # 네트워크 이름 자동 감지 또는 검증
        self._setup_network()

    def _initialize_docker_client(self):
        """Docker 클라이언트를 초기화하는 메서드"""
        # 먼저 Docker CLI가 작동하는지 확인
        try:
            result = subprocess.run(
                ["docker", "version", "--format", "json"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info("Docker CLI 연결 성공")
                self.use_cli = True
                return
        except Exception as e:
            logger.debug(f"Docker CLI 연결 실패: {str(e)}")

        # Docker SDK 연결 시도 (fallback)
        connection_methods = [
            ("환경변수", lambda: docker.from_env()),
            ("Unix socket", lambda: docker.DockerClient(base_url="unix://var/run/docker.sock")),
        ]

        for method_name, client_factory in connection_methods:
            try:
                client = client_factory()
                client.ping()
                self.client = client
                logger.info(f"Docker SDK 연결 성공 ({method_name})")
                return
            except Exception as e:
                logger.debug(f"Docker SDK 연결 실패 ({method_name}): {str(e)}")
                continue

        logger.error("모든 Docker 연결 방법이 실패했습니다. Docker 서비스가 실행 중인지 확인하세요.")

    def _setup_network(self):
        """네트워크 설정 및 검증"""
        try:
            if self.network_name == "auto":
                # 사용 가능한 네트워크 자동 감지
                self.network_name = self._detect_available_network()
                logger.info(f"🌐 자동 감지된 네트워크: {self.network_name}")
            else:
                # 지정된 네트워크 검증
                if not self._verify_network_exists(self.network_name):
                    logger.warning(
                        f"⚠️ 지정된 네트워크 '{self.network_name}'가 존재하지 않습니다. 기본 네트워크를 사용합니다."
                    )
                    self.network_name = self._detect_available_network()
                    logger.info(f"🌐 대체 네트워크: {self.network_name}")
                else:
                    logger.info(f"✅ 네트워크 확인됨: {self.network_name}")
        except Exception as e:
            logger.warning(f"⚠️ 네트워크 설정 실패: {str(e)}. 기본 네트워크를 사용합니다.")
            self.network_name = "bridge"  # Docker 기본 네트워크

    def _detect_available_network(self) -> str:
        """사용 가능한 네트워크 자동 감지"""
        try:
            # Docker Compose 네트워크 패턴 확인
            result = self._run_docker_command(["network", "ls", "--format", "{{.Name}}"])
            if result.returncode == 0:
                networks = result.stdout.strip().split("\n")

                # 우선순위: streamlit 관련 네트워크 > 프로젝트 네트워크 > bridge
                for network in networks:
                    if "streamlit" in network.lower():
                        return network

                # Docker Compose 프로젝트 네트워크 찾기
                for network in networks:
                    if "_default" in network or "open-streamlit-gallery" in network:
                        return network

                # 기본 bridge 네트워크 사용
                return "bridge"
            else:
                logger.warning("네트워크 목록 조회 실패, bridge 네트워크 사용")
                return "bridge"
        except Exception as e:
            logger.warning(f"네트워크 자동 감지 실패: {str(e)}, bridge 네트워크 사용")
            return "bridge"

    def _verify_network_exists(self, network_name: str) -> bool:
        """네트워크 존재 여부 확인"""
        try:
            result = self._run_docker_command(["network", "inspect", network_name])
            return result.returncode == 0
        except Exception:
            return False

    def _run_docker_command(
        self, cmd: List[str], timeout: int = 600, stream_output: bool = False
    ) -> subprocess.CompletedProcess:
        """Docker CLI 명령어를 실행"""
        full_cmd = ["docker"] + cmd
        logger.info(f"🔧 Docker 명령어 실행: {' '.join(full_cmd)}")

        if stream_output:
            # 실시간 출력을 위한 스트리밍 실행
            return self._run_docker_command_streaming(full_cmd, timeout)
        else:
            # 기존 방식 (출력 캡처)
            try:
                result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
                if result.returncode == 0:
                    logger.debug(f"✅ Docker 명령어 성공 (종료코드: {result.returncode})")
                else:
                    logger.warning(f"⚠️ Docker 명령어 실패 (종료코드: {result.returncode})")
                    if result.stderr:
                        logger.warning(f"stderr: {result.stderr[:500]}...")
                return result
            except subprocess.TimeoutExpired:
                logger.error(f"⏰ Docker 명령어 시간 초과 ({timeout}초): {' '.join(full_cmd)}")
                raise Exception(f"Docker 명령어 실행 시간 초과 ({timeout}초)")
            except Exception as e:
                logger.error(f"💥 Docker 명령어 실행 실패: {str(e)}")
                raise Exception(f"Docker 명령어 실행 실패: {str(e)}")

    def _run_docker_command_streaming(self, cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
        """Docker 명령어를 실시간 출력과 함께 실행"""
        try:
            logger.info(f"🚀 실시간 스트리밍 모드로 실행 중...")

            # 프로세스 시작 (버퍼링 없음으로 즉시 출력)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # stderr를 stdout으로 리다이렉트
                text=True,
                bufsize=0,  # 버퍼링 없음 (즉시 출력)
                universal_newlines=True,
            )

            output_lines = []

            # 실시간으로 출력 읽기
            start_time = time.time()

            while True:
                # 타임아웃 체크
                if time.time() - start_time > timeout:
                    process.kill()
                    raise subprocess.TimeoutExpired(cmd, timeout)

                line = process.stdout.readline()
                if line:
                    line = line.rstrip()
                    output_lines.append(line)
                    # 실시간 로깅 (Docker 빌드/실행 진행 상황을 더 명확하게)
                    if line.strip():
                        # Docker 빌드 단계별 진행 상황을 더 명확하게 표시
                        if "Step" in line or "RUN" in line or "COPY" in line or "FROM" in line:
                            logger.info(f"🏗️ {line}")
                        elif "Successfully built" in line or "Successfully tagged" in line:
                            logger.info(f"✅ {line}")
                        elif "ERROR" in line.upper() or "FAILED" in line.upper():
                            logger.error(f"❌ {line}")
                        elif "WARNING" in line.upper():
                            logger.warning(f"⚠️ {line}")
                        else:
                            logger.info(f"🔨 {line}")
                elif process.poll() is not None:
                    # 프로세스가 종료되었으면 남은 출력 읽기
                    remaining = process.stdout.read()
                    if remaining:
                        for remaining_line in remaining.split("\n"):
                            if remaining_line.strip():
                                output_lines.append(remaining_line)
                                logger.info(f"🔨 {remaining_line}")
                    break
                else:
                    # 짧은 대기 후 다시 시도 (CPU 사용량 줄이기)
                    time.sleep(0.1)

            # 프로세스 완료 대기
            return_code = process.wait(timeout=timeout)

            # 결과 객체 생성
            class StreamResult:
                def __init__(self, returncode, stdout, stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            full_output = "\n".join(output_lines)
            result = StreamResult(return_code, full_output)

            if return_code == 0:
                logger.info(f"✅ 스트리밍 명령어 성공 완료")
            else:
                logger.error(f"❌ 스트리밍 명령어 실패 (종료코드: {return_code})")

            return result

        except subprocess.TimeoutExpired:
            logger.error(f"⏰ 스트리밍 명령어 시간 초과 ({timeout}초)")
            if "process" in locals():
                process.kill()
            raise Exception(f"Docker 명령어 실행 시간 초과 ({timeout}초)")
        except Exception as e:
            logger.error(f"💥 스트리밍 명령어 실행 실패: {str(e)}")
            if "process" in locals():
                process.kill()
            raise Exception(f"Docker 명령어 실행 실패: {str(e)}")

    def _ensure_docker_connection(self):
        """Docker 연결을 확인"""
        if not self.use_cli and self.client is None:
            raise Exception("Docker 클라이언트가 연결되지 않았습니다. Docker 서비스가 실행 중인지 확인하세요.")

        if self.use_cli:
            # CLI 연결 테스트
            try:
                result = self._run_docker_command(["version"])
                if result.returncode != 0:
                    raise Exception(f"Docker CLI 연결 실패: {result.stderr}")
            except Exception as e:
                raise Exception(f"Docker CLI 연결 확인 실패: {str(e)}")
        else:
            # SDK 연결 테스트
            try:
                self.client.ping()
            except Exception as e:
                logger.warning(f"Docker SDK 연결이 끊어졌습니다. 재연결을 시도합니다: {str(e)}")
                self._initialize_docker_client()
                if not self.use_cli and self.client is None:
                    raise Exception("Docker 재연결에 실패했습니다.")

    def get_available_port(self) -> int:
        """사용 가능한 포트 번호를 반환 (내부적으로만 사용, 실제로는 필요 없음)"""
        # 포트를 외부에 노출하지 않으므로 더 이상 포트 충돌을 걱정할 필요 없음
        # 하지만 기존 코드 호환성을 위해 더미 포트 반환
        return 8501

    async def clone_repository(self, git_url: str, branch: str = "main", git_credential: dict = None) -> str:
        """Git 저장소를 클론하고 임시 디렉토리 경로를 반환"""
        temp_dir = tempfile.mkdtemp()
        logger.info(f"📁 임시 디렉토리 생성: {temp_dir}")

        try:
            if git_credential:
                # 인증 정보가 있는 경우
                if git_credential["auth_type"] == "token":
                    # HTTPS 토큰 인증
                    username = git_credential.get("username", "token")
                    token = git_credential["token"]

                    # URL에 인증 정보 추가
                    if git_url.startswith("https://"):
                        auth_url = git_url.replace("https://", f"https://{username}:{token}@")
                    else:
                        auth_url = git_url

                    logger.info(f"🔐 토큰 인증으로 Git 클론 시작...")
                    repo = Repo.clone_from(auth_url, temp_dir, branch=branch)

                elif git_credential["auth_type"] == "ssh":
                    # SSH 키 인증
                    ssh_key = git_credential["ssh_key"]

                    # SSH 키를 임시 파일로 저장
                    ssh_key_path = os.path.join(temp_dir, "ssh_key")
                    with open(ssh_key_path, "w") as f:
                        f.write(ssh_key)
                    os.chmod(ssh_key_path, 0o600)

                    # SSH 명령어 설정
                    ssh_cmd = f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no"

                    # 환경변수 설정하여 클론
                    import os

                    env = os.environ.copy()
                    env["GIT_SSH_COMMAND"] = ssh_cmd

                    logger.info(f"🔑 SSH 키 인증으로 Git 클론 시작...")
                    repo = Repo.clone_from(git_url, temp_dir, branch=branch, env=env)

                    # SSH 키 파일 삭제
                    os.remove(ssh_key_path)
                else:
                    # 공개 저장소
                    logger.info(f"🌐 공개 저장소로 Git 클론 시작...")
                    repo = Repo.clone_from(git_url, temp_dir, branch=branch)
            else:
                # 인증 정보가 없는 경우 (공개 저장소)
                logger.info(f"🌐 공개 저장소로 Git 클론 시작...")
                repo = Repo.clone_from(git_url, temp_dir, branch=branch)

            # 클론된 디렉토리 내용 확인
            self._log_directory_contents(temp_dir)

            return temp_dir
        except Exception as e:
            logger.error(f"❌ Git 클론 실패: {str(e)}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Git 저장소 클론 실패: {str(e)}")

    def _log_directory_contents(self, directory: str, max_files: int = 20):
        """디렉토리 내용을 로그에 출력"""
        try:
            logger.info(f"📂 디렉토리 내용 확인: {directory}")
            files = []
            for root, dirs, filenames in os.walk(directory):
                level = root.replace(directory, "").count(os.sep)
                indent = "  " * level
                rel_root = os.path.relpath(root, directory)
                if rel_root == ".":
                    logger.info(f"{indent}📁 .")
                else:
                    logger.info(f"{indent}📁 {rel_root}/")

                subindent = "  " * (level + 1)
                for filename in filenames[:10]:  # 각 디렉토리당 최대 10개 파일만
                    logger.info(f"{subindent}📄 {filename}")
                    files.append(filename)
                    if len(files) >= max_files:
                        break

                if len(filenames) > 10:
                    logger.info(f"{subindent}... 및 {len(filenames) - 10}개 파일 더")

                if len(files) >= max_files:
                    break

            # 주요 파일 확인
            important_files = ["requirements.txt", "app.py", "main.py", "streamlit_app.py", "Dockerfile", "README.md"]
            found_files = []
            for file in important_files:
                if os.path.exists(os.path.join(directory, file)):
                    found_files.append(file)

            if found_files:
                logger.info(f"🎯 주요 파일 발견: {', '.join(found_files)}")
            else:
                logger.warning("⚠️ 주요 파일을 찾을 수 없습니다")

        except Exception as e:
            logger.warning(f"⚠️ 디렉토리 내용 확인 실패: {str(e)}")

    def generate_dockerfile(self, repo_path: str, main_file: str, base_dockerfile_type: str = "auto") -> str:
        """동적으로 Dockerfile을 생성 (개선된 템플릿 시스템 사용)"""

        # requirements.txt 파일 존재 여부 및 내용 분석
        requirements_path = os.path.join(repo_path, "requirements.txt")
        has_requirements = os.path.exists(requirements_path)
        requirements_lines = []
        problematic_packages = []

        if has_requirements:
            logger.info(f"📋 requirements.txt 파일 발견")
            try:
                with open(requirements_path, "r", encoding="utf-8") as f:
                    requirements_lines = [
                        line.strip() for line in f.readlines() if line.strip() and not line.startswith("#")
                    ]
                logger.info(f"📦 requirements.txt에서 {len(requirements_lines)}개 패키지 발견")
            except Exception as e:
                logger.warning(f"⚠️ requirements.txt 읽기 실패: {str(e)}")
                requirements_lines = []
        else:
            logger.info(f"📋 requirements.txt 파일 없음")

        # 베이스 Dockerfile 선택 및 읽기 (간단 버전)
        if base_dockerfile_type == "auto":
            selected_type = "simple"  # 기본값으로 간단한 버전 사용 (numpy 문제 방지)
            logger.info(f"🤖 자동 선택된 베이스 Dockerfile: {selected_type}")
        else:
            selected_type = base_dockerfile_type
            logger.info(f"👤 사용자 선택 베이스 Dockerfile: {selected_type}")

        base_dockerfile_content = self._read_base_dockerfile(selected_type)

        # 앱별 추가 내용 생성 (간단 버전)
        app_specific_content = self._generate_app_specific_content(main_file, has_requirements, problematic_packages)

        # 최종 Dockerfile 내용 조합
        from datetime import datetime

        # 베이스 Dockerfile + 앱별 내용 조합
        dockerfile_content = base_dockerfile_content + "\n\n" + app_specific_content

        # 메타데이터 추가
        dockerfile_content = dockerfile_content.replace(
            "# 메타데이터",
            f"""# 메타데이터
LABEL app.main_file="{main_file}"
LABEL app.created="{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
LABEL app.requirements_count="{len(requirements_lines)}"
LABEL app.problematic_packages="{len(problematic_packages)}\"""",
        )

        # Dockerfile 저장
        dockerfile_path = os.path.join(repo_path, "Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile_content)

        logger.info(f"📝 Dockerfile 생성 완료")
        logger.info(f"  - 베이스 Dockerfile: {selected_type}")
        logger.info(f"  - 메인 파일: {main_file}")
        logger.info(f"  - requirements.txt: {'있음' if has_requirements else '없음'}")
        logger.info(f"  - 패키지 수: {len(requirements_lines)}개")
        logger.info(f"  - 컴파일 패키지: {len(problematic_packages)}개")

        return dockerfile_path

    def _select_base_dockerfile_type(self, problematic_packages: list, requirements_size: int) -> str:
        """패키지 상황에 맞는 베이스 Dockerfile 타입 선택"""

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
            logger.info("📊 데이터사이언스 베이스 Dockerfile 선택")
            return "py310"  # Dockerfile.py310
        elif len(problematic_packages) == 0 and requirements_size < 5:
            logger.info("🪶 최소 베이스 Dockerfile 선택")
            return "minimal"  # Dockerfile.minimal
        else:
            logger.info("🎯 표준 베이스 Dockerfile 선택")
            return "py311"  # Dockerfile.py311

    def _read_base_dockerfile(self, dockerfile_type: str) -> str:
        """베이스 Dockerfile 내용을 읽어옴"""
        dockerfile_map = {
            "py309": "Dockerfile.py309",
            "py311": "Dockerfile.py311",
            "py310": "Dockerfile.py310",
            "minimal": "Dockerfile.minimal",
            "simple": "Dockerfile.simple",
        }

        dockerfile_name = dockerfile_map.get(dockerfile_type, "Dockerfile.simple")
        dockerfile_path = f"/app/dockerfiles/{dockerfile_name}"

        try:
            with open(dockerfile_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"✅ 베이스 Dockerfile 읽기 성공: {dockerfile_name}")
            return content
        except FileNotFoundError:
            logger.warning(f"⚠️ 베이스 Dockerfile을 찾을 수 없음: {dockerfile_path}")
            # 폴백: 기본 템플릿 사용
            return self._get_fallback_dockerfile()
        except Exception as e:
            logger.error(f"❌ 베이스 Dockerfile 읽기 실패: {str(e)}")
            return self._get_fallback_dockerfile()

    def _get_fallback_dockerfile(self) -> str:
        """베이스 Dockerfile을 읽을 수 없을 때 사용할 폴백 Dockerfile (매우 간단)"""
        return """# 폴백 Dockerfile (간단 버전)
FROM python:3.11

# 작업 디렉토리 설정
WORKDIR /app

# 기본 도구만 설치
RUN apt-get update && apt-get install -y curl git && rm -rf /var/lib/apt/lists/*

# pip 업그레이드
RUN pip install --upgrade pip

# Streamlit 설치
RUN pip install --no-cache-dir streamlit

# 포트 노출
EXPOSE 8501

# 실행 사용자 설정
RUN useradd -m -u 1000 streamlit && chown -R streamlit:streamlit /app"""

    def _generate_app_specific_content(
        self, main_file: str, has_requirements: bool, problematic_packages: list
    ) -> str:
        """앱별 추가 내용 생성 (간단 버전)"""
        content_parts = []

        if has_requirements:
            content_parts.append(
                """
# requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt"""
            )

        content_parts.append(
            """
# 애플리케이션 파일 복사
COPY . .

# 불필요한 파일 제거
RUN find . -name "*.pyc" -delete && \\
    find . -name "__pycache__" -type d -exec rm -rf {} + || true

# 실행 사용자로 전환
USER streamlit"""
        )

        # f-string에서 백슬래시 문제를 피하기 위해 변수로 분리
        backslash = "\\"
        content_parts.append(
            f"""
# 실행 명령어
ENTRYPOINT ["streamlit", "run", "{main_file}", {backslash}
    "--server.port=8501", {backslash}
    "--server.address=0.0.0.0", {backslash}
    "--server.headless=true", {backslash}
    "--server.enableCORS=false", {backslash}
    "--server.enableXsrfProtection=false"]"""
        )

        return "\n".join(content_parts)

    async def build_image(
        self, repo_path: str, image_name: str, main_file: str, base_dockerfile_type: str = "auto"
    ) -> str:
        """Docker 이미지를 빌드"""
        self._ensure_docker_connection()

        try:
            # Dockerfile 생성
            logger.info(f"📝 Dockerfile 생성 중... (메인파일: {main_file}, 베이스타입: {base_dockerfile_type})")
            dockerfile_path = self.generate_dockerfile(repo_path, main_file, base_dockerfile_type)
            logger.info(f"✅ Dockerfile 생성 완료: {dockerfile_path}")

            # 생성된 Dockerfile 내용 일부 로깅
            try:
                with open(dockerfile_path, "r") as f:
                    dockerfile_content = f.read()
                    lines = dockerfile_content.split("\n")[:10]  # 처음 10줄만
                    logger.info("📄 생성된 Dockerfile 내용 (처음 10줄):")
                    for i, line in enumerate(lines, 1):
                        if line.strip():
                            logger.info(f"  {i:2d}: {line}")
            except Exception as e:
                logger.warning(f"⚠️ Dockerfile 내용 로깅 실패: {str(e)}")

            if self.use_cli:
                # CLI를 사용한 이미지 빌드 (실시간 스트리밍)
                logger.info(f"🔨 Docker 이미지 빌드 시작 (CLI 방식 - 실시간 출력)")
                logger.info(f"📦 이미지명: {image_name}")
                logger.info(f"📁 빌드 컨텍스트: {repo_path}")

                # 빌드 시간이 오래 걸릴 수 있으므로 타임아웃을 늘림 (10분)
                # --progress=auto로 설정하여 불필요한 출력 줄임
                logger.info(f"🔨 Docker 빌드 명령: docker build -t {image_name} --rm --force-rm {repo_path}")
                result = self._run_docker_command(
                    ["build", "--progress=auto", "-t", image_name, "--rm", "--force-rm", repo_path],
                    timeout=600,
                    stream_output=False,  # 스트리밍 비활성화로 블로킹 방지
                )

                if result.returncode != 0:
                    logger.error(f"❌ Docker 빌드 실패 (종료코드: {result.returncode})")
                    logger.error(f"stderr: {result.stderr}")
                    logger.error(f"stdout: {result.stdout}")
                    raise Exception(f"이미지 빌드 실패: {result.stderr}")

                logger.info(f"✅ Docker 이미지 빌드 성공!")
                build_output = result.stdout + result.stderr

                # 빌드 로그 요약
                lines = build_output.split("\n")
                logger.info(f"📊 빌드 로그 요약: 총 {len(lines)}줄")
                if len(lines) > 20:
                    logger.info("🔍 빌드 로그 마지막 10줄:")
                    for line in lines[-10:]:
                        if line.strip():
                            logger.info(f"  {line}")

                return build_output
            else:
                # SDK를 사용한 이미지 빌드
                logger.info(f"🔨 Docker 이미지 빌드 시작 (SDK 방식)")
                image, build_logs = self.client.images.build(path=repo_path, tag=image_name, rm=True, forcerm=True)

                # 빌드 로그 수집
                logs = []
                for log in build_logs:
                    if "stream" in log:
                        logs.append(log["stream"].strip())

                logger.info(f"✅ Docker 이미지 빌드 성공!")
                return "\\n".join(logs)

        except Exception as e:
            logger.error(f"❌ Docker 이미지 빌드 실패: {str(e)}")
            raise Exception(f"이미지 빌드 실패: {str(e)}")

    async def run_container(
        self, image_name: str, container_name: str, port: int, env_vars: Dict[str, str] = None
    ) -> str:
        """컨테이너를 실행"""
        self._ensure_docker_connection()

        try:
            logger.info(f"🐳 컨테이너 실행 준비")
            logger.info(f"📦 이미지: {image_name}")
            logger.info(f"🏷️ 컨테이너명: {container_name}")
            logger.info(f"🌐 네트워크: {self.network_name}")

            if env_vars:
                logger.info(f"🌍 환경변수: {len(env_vars)}개")
                for key, value in list(env_vars.items())[:5]:  # 처음 5개만 로깅
                    logger.info(f"  {key}={value[:50]}{'...' if len(value) > 50 else ''}")
                if len(env_vars) > 5:
                    logger.info(f"  ... 및 {len(env_vars) - 5}개 더")

            if self.use_cli:
                # CLI를 사용한 컨테이너 관리
                # 기존 컨테이너가 있으면 제거
                logger.info(f"🔍 기존 컨테이너 확인 중...")
                result = self._run_docker_command(
                    ["ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"]
                )
                if container_name in result.stdout:
                    logger.info(f"🛑 기존 컨테이너 발견, 중지 및 제거 중...")
                    self._run_docker_command(["stop", container_name])
                    self._run_docker_command(["rm", container_name])
                    logger.info(f"✅ 기존 컨테이너 제거 완료")
                else:
                    logger.info(f"✅ 기존 컨테이너 없음")

                # 환경변수 설정
                env_args = []
                if env_vars:
                    for key, value in env_vars.items():
                        env_args.extend(["-e", f"{key}={value}"])

                # 컨테이너 실행 (네트워크 포함)
                cmd = (
                    [
                        "run",
                        "-d",
                        "--name",
                        container_name,
                        "--network",
                        self.network_name,
                        "--restart",
                        "unless-stopped",
                        "--expose",
                        "8501",
                    ]
                    + env_args
                    + [image_name]
                )

                logger.info(f"🚀 컨테이너 실행 중...")
                result = self._run_docker_command(cmd)

                # 네트워크 연결 실패 시 기본 네트워크로 재시도
                if result.returncode != 0 and "network" in result.stderr.lower():
                    logger.warning(f"⚠️ 네트워크 '{self.network_name}' 연결 실패, 기본 네트워크로 재시도...")

                    # 기본 네트워크로 재시도
                    cmd_fallback = (
                        [
                            "run",
                            "-d",
                            "--name",
                            container_name,
                            "--restart",
                            "unless-stopped",
                            "--expose",
                            "8501",
                            "-p",
                            f"{port}:8501",  # 기본 네트워크에서는 포트 바인딩 필요
                        ]
                        + env_args
                        + [image_name]
                    )

                    logger.info(f"🔄 기본 네트워크로 컨테이너 재실행 중...")
                    result = self._run_docker_command(cmd_fallback)

                if result.returncode != 0:
                    logger.error(f"❌ 컨테이너 실행 실패 (종료코드: {result.returncode})")
                    logger.error(f"stderr: {result.stderr}")
                    logger.error(f"stdout: {result.stdout}")
                    raise Exception(f"컨테이너 실행 실패: {result.stderr}")

                container_id = result.stdout.strip()
                logger.info(f"✅ 컨테이너 실행 성공! ID: {container_id[:12]}...")

                # 컨테이너 상태 확인
                status_result = self._run_docker_command(["inspect", "--format", "{{.State.Status}}", container_id])
                if status_result.returncode == 0:
                    status = status_result.stdout.strip()
                    logger.info(f"📊 컨테이너 상태: {status}")

                # 컨테이너 초기 상태 확인 (블로킹 없이)
                logger.info(f"🔍 컨테이너 초기 상태 확인 중...")
                try:
                    time.sleep(2)  # 컨테이너가 시작될 시간을 줌

                    # 간단한 로그 확인 (블로킹 없이)
                    log_result = self._run_docker_command(["logs", "--tail", "10", container_id], timeout=5)
                    if log_result.returncode == 0 and log_result.stdout.strip():
                        logger.info(f"📋 초기 로그 확인: {log_result.stdout.strip()[:100]}...")
                    else:
                        logger.info(f"📋 컨테이너 시작됨 (로그 대기 중)")
                except Exception as log_e:
                    logger.warning(f"⚠️ 초기 로그 확인 실패 (무시됨): {str(log_e)}")

                return container_id
            else:
                # SDK를 사용한 컨테이너 관리
                logger.info(f"🔍 기존 컨테이너 확인 중... (SDK 방식)")
                # 기존 컨테이너가 있으면 제거
                try:
                    existing_container = self.client.containers.get(container_name)
                    logger.info(f"🛑 기존 컨테이너 발견, 중지 및 제거 중...")
                    existing_container.stop()
                    existing_container.remove()
                    logger.info(f"✅ 기존 컨테이너 제거 완료")
                except docker.errors.NotFound:
                    logger.info(f"✅ 기존 컨테이너 없음")

                # 환경변수 설정
                environment = env_vars or {}

                logger.info(f"🚀 컨테이너 실행 중... (SDK 방식)")
                # 컨테이너 실행 (포트를 외부에 노출하지 않음)
                container = self.client.containers.run(
                    image_name,
                    name=container_name,
                    environment=environment,
                    network=self.network_name,
                    detach=True,
                    restart_policy={"Name": "unless-stopped"},
                    # 내부 포트만 노출 (외부 포트 바인딩 없음)
                    expose=[8501],
                )

                logger.info(f"✅ 컨테이너 실행 성공! ID: {container.id[:12]}...")
                logger.info(f"📊 컨테이너 상태: {container.status}")
                return container.id

        except Exception as e:
            logger.error(f"❌ 컨테이너 실행 실패: {str(e)}")
            raise Exception(f"컨테이너 실행 실패: {str(e)}")

    async def stop_container(self, container_id: str) -> bool:
        """컨테이너를 중지"""
        try:
            if self.use_cli:
                result = self._run_docker_command(["stop", container_id])
                return result.returncode == 0
            else:
                container = self.client.containers.get(container_id)
                container.stop()
                return True
        except Exception as e:
            logger.error(f"컨테이너 중지 실패: {str(e)}")
            return False

    async def remove_container(self, container_id: str) -> bool:
        """컨테이너를 제거"""
        try:
            if self.use_cli:
                # 컨테이너 중지 후 제거
                self._run_docker_command(["stop", container_id])
                result = self._run_docker_command(["rm", container_id])
                return result.returncode == 0
            else:
                container = self.client.containers.get(container_id)
                container.stop()
                container.remove()
                return True
        except Exception as e:
            logger.error(f"컨테이너 제거 실패: {str(e)}")
            return False

    async def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """컨테이너 로그를 가져옴"""
        try:
            if self.use_cli:
                result = self._run_docker_command(["logs", "--tail", str(tail), "--timestamps", container_id])
                if result.returncode == 0:
                    return result.stdout + result.stderr
                else:
                    return f"로그 가져오기 실패: {result.stderr}"
            else:
                container = self.client.containers.get(container_id)
                logs = container.logs(tail=tail, timestamps=True)
                return logs.decode("utf-8")
        except Exception as e:
            return f"로그 가져오기 실패: {str(e)}"

    async def get_container_status(self, container_id: str) -> str:
        """컨테이너 상태를 확인"""
        try:
            if self.use_cli:
                result = self._run_docker_command(["inspect", "--format", "{{.State.Status}}", container_id])
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    return "not_found"
            else:
                container = self.client.containers.get(container_id)
                return container.status
        except Exception:
            return "not_found"

    def cleanup_temp_directory(self, temp_dir: str):
        """임시 디렉토리 정리"""
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"임시 디렉토리 정리 실패: {str(e)}")

    # Celery 태스크 호출 메서드들
    def build_image_async(
        self,
        app_id: int,
        git_url: str,
        branch: str,
        main_file: str,
        base_dockerfile_type: str = "auto",
        git_credential: Optional[Dict] = None,
    ) -> str:
        """
        비동기 이미지 빌드 태스크 시작
        Returns: Celery task ID
        """
        try:
            from app.tasks.docker_tasks import build_image_task

            task = build_image_task.delay(
                app_id=app_id,
                git_url=git_url,
                branch=branch,
                main_file=main_file,
                base_dockerfile_type=base_dockerfile_type,
                git_credential=git_credential,
            )

            logger.info(f"🚀 비동기 이미지 빌드 태스크 시작: {task.id} (App ID: {app_id})")
            return task.id

        except Exception as e:
            logger.error(f"❌ 비동기 이미지 빌드 태스크 시작 실패: {str(e)}")
            raise Exception(f"비동기 이미지 빌드 시작 실패: {str(e)}")

    def deploy_app_async(self, app_id: int, image_name: str, env_vars: Optional[Dict[str, str]] = None) -> str:
        """
        비동기 앱 배포 태스크 시작
        Returns: Celery task ID
        """
        try:
            from app.tasks.docker_tasks import deploy_app_task

            task = deploy_app_task.delay(app_id=app_id, image_name=image_name, env_vars=env_vars)

            logger.info(f"🚀 비동기 앱 배포 태스크 시작: {task.id} (App ID: {app_id})")
            return task.id

        except Exception as e:
            logger.error(f"❌ 비동기 앱 배포 태스크 시작 실패: {str(e)}")
            raise Exception(f"비동기 앱 배포 시작 실패: {str(e)}")

    def stop_app_async(self, app_id: int) -> str:
        """
        비동기 앱 중지 태스크 시작
        Returns: Celery task ID
        """
        try:
            from app.tasks.docker_tasks import stop_app_task

            task = stop_app_task.delay(app_id=app_id)

            logger.info(f"🛑 비동기 앱 중지 태스크 시작: {task.id} (App ID: {app_id})")
            return task.id

        except Exception as e:
            logger.error(f"❌ 비동기 앱 중지 태스크 시작 실패: {str(e)}")
            raise Exception(f"비동기 앱 중지 시작 실패: {str(e)}")

    def remove_app_async(self, app_id: int) -> str:
        """
        비동기 앱 제거 태스크 시작
        Returns: Celery task ID
        """
        try:
            from app.tasks.docker_tasks import remove_app_task

            task = remove_app_task.delay(app_id=app_id)

            logger.info(f"🗑️ 비동기 앱 제거 태스크 시작: {task.id} (App ID: {app_id})")
            return task.id

        except Exception as e:
            logger.error(f"❌ 비동기 앱 제거 태스크 시작 실패: {str(e)}")
            raise Exception(f"비동기 앱 제거 시작 실패: {str(e)}")

    def get_task_status(self, task_id: str) -> Dict:
        """
        Celery 태스크 상태 조회
        """
        try:
            from app.celery_app import celery_app

            task = celery_app.AsyncResult(task_id)

            result = {
                "task_id": task_id,
                "state": task.state,
                "ready": task.ready(),
                "successful": task.successful() if task.ready() else None,
                "failed": task.failed() if task.ready() else None,
            }

            # 태스크 메타데이터 (진행률 등)
            if task.state == "PROGRESS":
                result["meta"] = task.info
            elif task.state == "SUCCESS":
                result["result"] = task.result
            elif task.state == "FAILURE":
                result["error"] = str(task.info)
                result["meta"] = task.info if isinstance(task.info, dict) else {}

            return result

        except Exception as e:
            logger.error(f"❌ 태스크 상태 조회 실패: {str(e)}")
            return {"task_id": task_id, "state": "UNKNOWN", "error": str(e)}

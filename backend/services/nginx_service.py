import os
import subprocess
from jinja2 import Template
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class NginxService:
    def __init__(self):
        # Docker Compose에서 nginx_config 볼륨이 /app/nginx_config에 마운트됨
        # 이 경로는 Nginx 컨테이너의 /etc/nginx/conf.d/dynamic/와 연결됨
        self.config_dir = "/app/nginx_config"
        self.template_dir = "/app/templates"

        # 시스템 설정 파일들 (삭제하면 안 되는 파일들)
        self.system_configs = {"default.conf", "test.conf", "upstreams.conf"}

        # 설정 디렉토리가 없으면 생성
        os.makedirs(self.config_dir, exist_ok=True)

    async def initialize_config(self):
        """Nginx 기본 설정 초기화"""
        try:
            # 기본 upstream 설정 파일 생성
            upstream_config = """
# 동적으로 생성되는 upstream 설정들
# 이 파일은 자동으로 관리됩니다.
"""
            upstream_file = os.path.join(self.config_dir, "upstreams.conf")
            with open(upstream_file, "w") as f:
                f.write(upstream_config)

            # 기본 서버 설정 파일 생성
            await self.generate_main_server_config()

            logger.info("Nginx 기본 설정이 초기화되었습니다.")

        except Exception as e:
            logger.error(f"Nginx 설정 초기화 실패: {str(e)}")

    async def generate_main_server_config(self):
        """메인 서버 설정 생성 - 빈 파일로 초기화"""
        # 기존 default.conf가 이미 server 블록을 포함하고 있으므로
        # 동적 설정 파일은 빈 파일로 시작
        server_config = """# 동적으로 생성되는 앱 설정들
# 이 파일은 자동으로 관리됩니다.
"""
        server_file = os.path.join(self.config_dir, "default.conf")
        with open(server_file, "w") as f:
            f.write(server_config)

    def create_app_config(self, app_name: str, container_name: str, port: int = 8501) -> str:
        """앱을 위한 Nginx 설정 내용 생성 (파일 저장하지 않음)"""
        try:
            logger.info(f"🌐 Nginx 설정 내용 생성 - 앱: {app_name}, 컨테이너: {container_name}, 포트: {port}")

            app_config_template = """# {{ app_name }} 앱 설정
location /{{ app_name }}/ {
    proxy_pass http://{{ container_name }}:{{ port }}/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Script-Name /{{ app_name }};
    
    # Streamlit WebSocket 지원
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    
    # sub_filter를 사용하여 Streamlit의 내부 링크 수정
    sub_filter_once off;
    sub_filter_types text/html text/css text/javascript application/javascript;
    sub_filter 'src="/' 'src="/{{ app_name }}/';
    sub_filter 'href="/' 'href="/{{ app_name }}/';
    sub_filter 'action="/' 'action="/{{ app_name }}/';
    sub_filter '"/_stcore/' '"/{{ app_name }}/_stcore/';
    sub_filter '"/_stcore' '"/{{ app_name }}/_stcore';
    sub_filter 'window.location.pathname' 'window.location.pathname.replace("/{{ app_name }}", "")';
}

# WebSocket을 위한 별도 location
location /{{ app_name }}/_stcore/stream {
    proxy_pass http://{{ container_name }}:{{ port }}/_stcore/stream;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
}

# 정적 파일들을 위한 추가 설정
location ~ ^/{{ app_name }}/(.*\\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot))$ {
    proxy_pass http://{{ container_name }}:{{ port }}/$1;
    proxy_set_header Host $host;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
"""

            template = Template(app_config_template)
            config_content = template.render(app_name=app_name, container_name=container_name, port=port)

            logger.info(f"✅ Nginx 설정 내용 생성 완료 - 앱: {app_name}")
            return config_content

        except Exception as e:
            logger.error(f"❌ Nginx 설정 내용 생성 실패: {str(e)}")
            raise Exception(f"Nginx 설정 내용 생성 실패: {str(e)}")

    def save_config(self, filename: str, config_content: str) -> bool:
        """설정 내용을 파일로 저장"""
        try:
            config_file = os.path.join(self.config_dir, filename)
            logger.info(f"📝 설정 파일 저장: {config_file}")

            with open(config_file, "w") as f:
                f.write(config_content)

            logger.info(f"✅ 설정 파일 저장 완료: {config_file}")

            # 설정 파일이 제대로 생성되었는지 확인
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    content = f.read()
                    logger.info(f"📄 저장된 설정 파일 내용 (처음 3줄):")
                    for i, line in enumerate(content.split("\n")[:3], 1):
                        if line.strip():
                            logger.info(f"  {i}: {line}")
                return True
            else:
                logger.error(f"❌ 설정 파일이 생성되지 않았습니다: {config_file}")
                return False

        except Exception as e:
            logger.error(f"❌ 설정 파일 저장 실패: {str(e)}")
            return False

    def reload_nginx(self) -> bool:
        """Nginx 설정 리로드 (동기 버전)"""
        try:
            logger.info("🔄 Nginx 설정 리로드 시작...")

            # 컨테이너 상태 먼저 확인
            container_check = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", "streamlit_platform_nginx"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if container_check.returncode != 0:
                logger.warning("⚠️ Nginx 컨테이너를 찾을 수 없습니다. 리로드를 건너뜁니다.")
                return False

            container_status = container_check.stdout.strip()
            logger.info(f"📊 Nginx 컨테이너 상태: {container_status}")

            # 컨테이너가 재시작 중이거나 실행 중이 아니면 건너뜀
            if container_status in ["restarting", "paused", "exited"]:
                logger.warning(f"⚠️ Nginx 컨테이너가 {container_status} 상태입니다. 리로드를 건너뜁니다.")
                return False

            # Docker 컨테이너 내에서 nginx reload 실행
            result = subprocess.run(
                ["docker", "exec", "streamlit_platform_nginx", "nginx", "-s", "reload"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info("✅ Nginx 설정이 성공적으로 리로드되었습니다.")
                if result.stdout:
                    logger.info(f"📋 Nginx 출력: {result.stdout}")
                return True
            else:
                # 컨테이너 재시작 관련 에러인지 확인
                if "is restarting" in result.stderr or "wait until the container is running" in result.stderr:
                    logger.warning("⚠️ Nginx 컨테이너가 재시작 중입니다. 리로드를 건너뜁니다.")
                    return False
                else:
                    logger.error(f"❌ Nginx 리로드 실패 (종료코드: {result.returncode})")
                    logger.error(f"stderr: {result.stderr}")
                    if result.stdout:
                        logger.error(f"stdout: {result.stdout}")
                    return False

        except subprocess.TimeoutExpired:
            logger.error("⏰ Nginx 리로드 시간 초과")
            return False
        except Exception as e:
            # 컨테이너 재시작 관련 에러인지 확인
            if "is restarting" in str(e) or "wait until the container is running" in str(e):
                logger.warning(f"⚠️ Nginx 컨테이너 재시작 중: {str(e)}")
                return False
            else:
                logger.error(f"💥 Nginx 리로드 중 오류 발생: {str(e)}")
                return False

    def remove_config(self, filename: str) -> bool:
        """설정 파일 제거"""
        try:
            config_file = os.path.join(self.config_dir, filename)
            if os.path.exists(config_file):
                os.remove(config_file)
                logger.info(f"✅ 설정 파일 제거 완료: {config_file}")
                return True
            else:
                logger.warning(f"⚠️ 제거할 설정 파일이 없습니다: {config_file}")
                return False

        except Exception as e:
            logger.error(f"❌ 설정 파일 제거 실패: {str(e)}")
            return False

    async def add_app_config(self, subdomain: str, container_name: str):
        """새로운 앱을 위한 Nginx 설정 추가"""
        try:
            logger.info(f"🌐 Nginx 설정 생성 시작 - 서브도메인: {subdomain}, 컨테이너: {container_name}")

            app_config_template = """# {{ subdomain }} 앱 설정
location /{{ subdomain }}/ {
    proxy_pass http://{{ container_name }}:8501/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Script-Name /{{ subdomain }};
    
    # Streamlit WebSocket 지원
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    
    # sub_filter를 사용하여 Streamlit의 내부 링크 수정
    sub_filter_once off;
    sub_filter_types text/html text/css text/javascript application/javascript;
    sub_filter 'src="/' 'src="/{{ subdomain }}/';
    sub_filter 'href="/' 'href="/{{ subdomain }}/';
    sub_filter 'action="/' 'action="/{{ subdomain }}/';
    sub_filter '"/_stcore/' '"/{{ subdomain }}/_stcore/';
    sub_filter '"/_stcore' '"/{{ subdomain }}/_stcore';
    sub_filter 'window.location.pathname' 'window.location.pathname.replace("/{{ subdomain }}", "")';
}

# WebSocket을 위한 별도 location
location /{{ subdomain }}/_stcore/stream {
    proxy_pass http://{{ container_name }}:8501/_stcore/stream;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
}

# 정적 파일들을 위한 추가 설정
location ~ ^/{{ subdomain }}/(.*\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot))$ {
    proxy_pass http://{{ container_name }}:8501/$1;
    proxy_set_header Host $host;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
"""

            template = Template(app_config_template)
            config_content = template.render(subdomain=subdomain, container_name=container_name)

            config_file = os.path.join(self.config_dir, f"{subdomain}.conf")
            logger.info(f"📝 설정 파일 생성: {config_file}")

            with open(config_file, "w") as f:
                f.write(config_content)

            logger.info(f"✅ 설정 파일 생성 완료: {config_file}")

            # 설정 파일이 제대로 생성되었는지 확인
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    content = f.read()
                    logger.info(f"📄 생성된 설정 파일 내용 (처음 3줄):")
                    for i, line in enumerate(content.split("\n")[:3], 1):
                        if line.strip():
                            logger.info(f"  {i}: {line}")

            # Nginx 설정 테스트 후 리로드
            logger.info("🔍 Nginx 설정 유효성 검사 중...")
            if await self.test_nginx_config():
                logger.info("✅ Nginx 설정 유효성 검사 통과")
                await self.reload_nginx()
            else:
                logger.error("❌ Nginx 설정 유효성 검사 실패")
                # 설정 파일 제거
                if os.path.exists(config_file):
                    os.remove(config_file)
                raise Exception("Nginx 설정 유효성 검사 실패")

            logger.info(f"🎉 앱 {subdomain}의 Nginx 설정이 성공적으로 추가되었습니다.")

        except Exception as e:
            logger.error(f"❌ 앱 설정 추가 실패: {str(e)}")
            raise Exception(f"Nginx 설정 추가 실패: {str(e)}")

    async def remove_app_config(self, subdomain: str):
        """앱의 Nginx 설정 제거"""
        try:
            config_file = os.path.join(self.config_dir, f"{subdomain}.conf")
            if os.path.exists(config_file):
                os.remove(config_file)

                # Nginx 설정 리로드
                await self.reload_nginx()

                logger.info(f"앱 {subdomain}의 Nginx 설정이 제거되었습니다.")

        except Exception as e:
            logger.error(f"앱 설정 제거 실패: {str(e)}")

    async def reload_nginx(self):
        """Nginx 설정 리로드"""
        try:
            logger.info("🔄 Nginx 설정 리로드 시작...")

            # 컨테이너 상태 먼저 확인
            container_check = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", "streamlit_platform_nginx"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if container_check.returncode != 0:
                logger.warning("⚠️ Nginx 컨테이너를 찾을 수 없습니다. 리로드를 건너뜁니다.")
                return False

            container_status = container_check.stdout.strip()
            logger.info(f"📊 Nginx 컨테이너 상태: {container_status}")

            # 컨테이너가 재시작 중이거나 실행 중이 아니면 잠시 대기
            if container_status in ["restarting", "paused", "exited"]:
                logger.warning(f"⚠️ Nginx 컨테이너가 {container_status} 상태입니다. 리로드를 건너뜁니다.")
                return False

            # Docker 컨테이너 내에서 nginx reload 실행
            result = subprocess.run(
                ["docker", "exec", "streamlit_platform_nginx", "nginx", "-s", "reload"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info("✅ Nginx 설정이 성공적으로 리로드되었습니다.")
                if result.stdout:
                    logger.info(f"📋 Nginx 출력: {result.stdout}")
                return True
            else:
                # 컨테이너 재시작 관련 에러인지 확인
                if "is restarting" in result.stderr or "wait until the container is running" in result.stderr:
                    logger.warning("⚠️ Nginx 컨테이너가 재시작 중입니다. 리로드를 건너뜁니다.")
                    return False
                else:
                    logger.error(f"❌ Nginx 리로드 실패 (종료코드: {result.returncode})")
                    logger.error(f"stderr: {result.stderr}")
                    if result.stdout:
                        logger.error(f"stdout: {result.stdout}")
                    raise Exception(f"Nginx 리로드 실패: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("⏰ Nginx 리로드 시간 초과")
            return False
        except Exception as e:
            # 컨테이너 재시작 관련 에러인지 확인
            if "is restarting" in str(e) or "wait until the container is running" in str(e):
                logger.warning(f"⚠️ Nginx 컨테이너 재시작 중: {str(e)}")
                return False
            else:
                logger.error(f"💥 Nginx 리로드 중 오류 발생: {str(e)}")
                raise

    async def test_nginx_config(self) -> bool:
        """Nginx 설정 파일 유효성 검사"""
        try:
            logger.info("🧪 Nginx 설정 유효성 검사 실행 중...")

            # 컨테이너 상태 먼저 확인
            container_check = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", "streamlit_platform_nginx"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if container_check.returncode != 0:
                logger.warning("⚠️ Nginx 컨테이너를 찾을 수 없습니다. 설정 검사를 건너뜁니다.")
                return True  # 컨테이너가 없으면 검사를 통과한 것으로 처리

            container_status = container_check.stdout.strip()
            logger.info(f"📊 Nginx 컨테이너 상태: {container_status}")

            # 컨테이너가 재시작 중이거나 실행 중이 아니면 건너뜀
            if container_status in ["restarting", "paused", "exited"]:
                logger.warning(f"⚠️ Nginx 컨테이너가 {container_status} 상태입니다. 설정 검사를 건너뜁니다.")
                return True  # 검사를 통과한 것으로 처리

            result = subprocess.run(
                ["docker", "exec", "streamlit_platform_nginx", "nginx", "-t"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info("✅ Nginx 설정 유효성 검사 성공")
                if result.stderr:  # nginx -t는 성공 메시지를 stderr로 출력
                    logger.info(f"📋 Nginx 테스트 결과: {result.stderr}")
                return True
            else:
                # 컨테이너 재시작 관련 에러인지 확인
                if "is restarting" in result.stderr or "wait until the container is running" in result.stderr:
                    logger.warning("⚠️ Nginx 컨테이너가 재시작 중입니다. 설정 검사를 건너뜁니다.")
                    return True  # 검사를 통과한 것으로 처리
                else:
                    logger.error(f"❌ Nginx 설정 유효성 검사 실패 (종료코드: {result.returncode})")
                    logger.error(f"stderr: {result.stderr}")
                    if result.stdout:
                        logger.error(f"stdout: {result.stdout}")
                    return False

        except Exception as e:
            # 컨테이너 재시작 관련 에러인지 확인
            if "is restarting" in str(e) or "wait until the container is running" in str(e):
                logger.warning(f"⚠️ Nginx 컨테이너 재시작 중: {str(e)}")
                return True  # 검사를 통과한 것으로 처리
            else:
                logger.error(f"💥 Nginx 설정 테스트 실패: {str(e)}")
                return False

    async def get_app_configs(self) -> List[str]:
        """현재 설정된 앱 목록 반환"""
        try:
            configs = []
            for filename in os.listdir(self.config_dir):
                if filename.endswith(".conf") and filename not in self.system_configs:
                    subdomain = filename.replace(".conf", "")
                    configs.append(subdomain)
            return configs

        except Exception as e:
            logger.error(f"앱 설정 목록 조회 실패: {str(e)}")
            return []

    async def get_dynamic_configs(self) -> Dict[str, List[str]]:
        """dynamic 폴더 내 모든 설정 파일 정보 반환"""
        try:
            all_files = []
            app_configs = []
            system_files = []

            if os.path.exists(self.config_dir):
                for filename in os.listdir(self.config_dir):
                    if filename.endswith(".conf"):
                        all_files.append(filename)
                        if filename in self.system_configs:
                            system_files.append(filename)
                        else:
                            app_configs.append(filename.replace(".conf", ""))

            return {
                "all_files": all_files,
                "app_configs": app_configs,
                "system_files": system_files,
                "total_count": len(all_files),
                "app_count": len(app_configs),
            }

        except Exception as e:
            logger.error(f"dynamic 설정 목록 조회 실패: {str(e)}")
            return {"all_files": [], "app_configs": [], "system_files": [], "total_count": 0, "app_count": 0}

    async def cleanup_unused_configs(self, active_apps: List[str]) -> Dict[str, any]:
        """실제 서비스 중인 앱들만 남기고 나머지 설정 파일 삭제 후 reload"""
        try:
            logger.info(f"🧹 사용하지 않는 Nginx 설정 정리 시작...")
            logger.info(f"📋 활성 앱 목록: {active_apps}")

            # 현재 설정 파일들 조회
            current_configs = await self.get_dynamic_configs()
            current_app_configs = current_configs["app_configs"]

            # 삭제할 설정 파일들 찾기
            configs_to_remove = []
            for config in current_app_configs:
                if config not in active_apps:
                    configs_to_remove.append(config)

            logger.info(f"🗑️ 삭제할 설정 파일들: {configs_to_remove}")

            # 설정 파일들 삭제
            removed_files = []
            for config in configs_to_remove:
                config_file = os.path.join(self.config_dir, f"{config}.conf")
                if os.path.exists(config_file):
                    try:
                        os.remove(config_file)
                        removed_files.append(f"{config}.conf")
                        logger.info(f"✅ 삭제 완료: {config}.conf")
                    except Exception as e:
                        logger.error(f"❌ 파일 삭제 실패 {config}.conf: {str(e)}")

            # Nginx 설정 테스트 후 리로드
            if removed_files:
                logger.info("🔍 Nginx 설정 유효성 검사 중...")
                if await self.test_nginx_config():
                    logger.info("✅ Nginx 설정 유효성 검사 통과")
                    await self.reload_nginx()
                    logger.info("🎉 사용하지 않는 설정 파일 정리 완료")
                else:
                    logger.error("❌ Nginx 설정 유효성 검사 실패")
                    return {
                        "success": False,
                        "message": "Nginx 설정 유효성 검사 실패",
                        "removed_files": [],
                        "error": "설정 파일 삭제 후 Nginx 설정이 유효하지 않음",
                    }
            else:
                logger.info("📝 삭제할 설정 파일이 없습니다.")

            return {
                "success": True,
                "message": f"{len(removed_files)}개의 사용하지 않는 설정 파일을 정리했습니다.",
                "removed_files": removed_files,
                "active_apps": active_apps,
                "remaining_configs": [app for app in current_app_configs if app in active_apps],
            }

        except Exception as e:
            logger.error(f"❌ 설정 파일 정리 실패: {str(e)}")
            return {"success": False, "message": "설정 파일 정리 중 오류 발생", "removed_files": [], "error": str(e)}

    async def remove_specific_config(self, subdomain: str) -> Dict[str, any]:
        """특정 서브도메인의 설정 파일 삭제"""
        try:
            config_file = f"{subdomain}.conf"
            config_path = os.path.join(self.config_dir, config_file)

            if not os.path.exists(config_path):
                return {"success": False, "message": f"설정 파일을 찾을 수 없습니다: {config_file}"}

            # 시스템 설정 파일 보호
            if config_file in self.system_configs:
                return {"success": False, "message": f"시스템 설정 파일은 삭제할 수 없습니다: {config_file}"}

            os.remove(config_path)
            logger.info(f"🗑️ 설정 파일 삭제 완료: {config_file}")

            # Nginx 리로드
            reload_success = await self.reload_nginx()
            if not reload_success:
                logger.warning("⚠️ Nginx 리로드 실패, 하지만 파일 삭제는 완료됨")

            return {
                "success": True,
                "message": f"설정 파일이 삭제되었습니다: {config_file}",
                "nginx_reloaded": reload_success,
            }

        except Exception as e:
            logger.error(f"❌ 설정 파일 삭제 실패: {str(e)}")
            return {"success": False, "message": f"설정 파일 삭제 실패: {str(e)}"}

    async def validate_and_cleanup_configs(self) -> Dict[str, any]:
        """
        모든 설정 파일을 개별적으로 검증하고 문제가 있는 파일들을 자동 삭제
        """
        try:
            logger.info("🔍 설정 파일 검증 및 자동 정리 시작...")

            # 동적 설정 파일 목록 조회
            configs = await self.get_dynamic_configs()
            app_configs = configs.get("app_configs", [])

            if not app_configs:
                return {
                    "success": True,
                    "message": "검증할 설정 파일이 없습니다.",
                    "removed_files": [],
                    "total_checked": 0,
                }

            removed_files = []
            validation_results = []

            for app_name in app_configs:
                config_file = f"{app_name}.conf"
                logger.info(f"🔍 설정 파일 검증 중: {config_file}")

                # 개별 파일 검증
                validation_result = await self._validate_single_config(config_file)
                validation_results.append(
                    {
                        "file": config_file,
                        "app_name": app_name,
                        "valid": validation_result["valid"],
                        "reason": validation_result.get("reason", ""),
                    }
                )

                # 검증 실패 시 파일 삭제
                if not validation_result["valid"]:
                    logger.warning(
                        f"⚠️ 문제 발견: {config_file} - {validation_result.get('reason', '알 수 없는 오류')}"
                    )

                    try:
                        config_path = os.path.join(self.config_dir, config_file)
                        os.remove(config_path)
                        removed_files.append(config_file)
                        logger.info(f"🗑️ 문제 파일 삭제 완료: {config_file}")
                    except Exception as e:
                        logger.error(f"❌ 파일 삭제 실패: {config_file} - {str(e)}")
                else:
                    logger.info(f"✅ 설정 파일 정상: {config_file}")

            # 파일이 삭제되었으면 Nginx 리로드
            nginx_reloaded = False
            if removed_files:
                logger.info(f"🔄 {len(removed_files)}개 파일 삭제로 인한 Nginx 리로드...")
                nginx_reloaded = await self.reload_nginx()
                if not nginx_reloaded:
                    logger.warning("⚠️ Nginx 리로드 실패")

            return {
                "success": True,
                "message": f"검증 완료. {len(removed_files)}개 문제 파일 삭제됨",
                "total_checked": len(app_configs),
                "removed_files": removed_files,
                "validation_results": validation_results,
                "nginx_reloaded": nginx_reloaded,
            }

        except Exception as e:
            logger.error(f"❌ 설정 파일 검증 및 정리 실패: {str(e)}")
            return {"success": False, "message": f"설정 파일 검증 실패: {str(e)}"}

    async def _validate_single_config(self, config_file: str) -> Dict[str, any]:
        """
        개별 설정 파일 검증
        """
        try:
            config_path = os.path.join(self.config_dir, config_file)

            # 1. 파일 존재 여부 확인
            if not os.path.exists(config_path):
                return {"valid": False, "reason": "파일이 존재하지 않음"}

            # 2. 파일 읽기 가능 여부 확인
            try:
                with open(config_path, "r") as f:
                    content = f.read()
                if not content.strip():
                    return {"valid": False, "reason": "빈 파일"}
            except Exception as e:
                return {"valid": False, "reason": f"파일 읽기 실패: {str(e)}"}

            # 3. 기본 Nginx 문법 검사 (간단한 체크)
            if not self._basic_nginx_syntax_check(content):
                return {"valid": False, "reason": "Nginx 문법 오류"}

            # 4. upstream 연결 가능성 검사
            upstream_check = await self._check_upstream_connectivity(content, config_file)
            if not upstream_check["valid"]:
                return {"valid": False, "reason": upstream_check["reason"]}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "reason": f"검증 중 오류: {str(e)}"}

    def _basic_nginx_syntax_check(self, content: str) -> bool:
        """
        기본적인 Nginx 설정 문법 검사
        """
        try:
            # 기본적인 문법 요소들 확인
            required_elements = [
                "location",  # location 블록이 있어야 함
                "proxy_pass",  # proxy_pass 지시어가 있어야 함
            ]

            for element in required_elements:
                if element not in content:
                    logger.warning(f"⚠️ 필수 요소 누락: {element}")
                    return False

            # 중괄호 균형 검사
            open_braces = content.count("{")
            close_braces = content.count("}")
            if open_braces != close_braces:
                logger.warning(f"⚠️ 중괄호 불균형: {{ {open_braces}개, }} {close_braces}개")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ 문법 검사 실패: {str(e)}")
            return False

    async def _check_upstream_connectivity(self, content: str, config_file: str) -> Dict[str, any]:
        """
        upstream 서버 연결 가능성 검사
        """
        try:
            import re

            # proxy_pass에서 upstream 서버 추출
            proxy_pass_pattern = r"proxy_pass\s+http://([^:/]+):(\d+)"
            matches = re.findall(proxy_pass_pattern, content)

            if not matches:
                return {"valid": False, "reason": "proxy_pass 설정을 찾을 수 없음"}

            for host, port in matches:
                # Docker 컨테이너 존재 여부 확인
                container_exists = await self._check_docker_container_exists(host)
                if not container_exists:
                    return {"valid": False, "reason": f"upstream 컨테이너가 존재하지 않음: {host}"}

                # 컨테이너가 실행 중인지 확인
                container_running = await self._check_docker_container_running(host)
                if not container_running:
                    return {"valid": False, "reason": f"upstream 컨테이너가 실행 중이 아님: {host}"}

            return {"valid": True}

        except Exception as e:
            logger.error(f"❌ upstream 연결성 검사 실패: {str(e)}")
            return {"valid": False, "reason": f"upstream 검사 실패: {str(e)}"}

    async def _check_docker_container_exists(self, container_name: str) -> bool:
        """
        Docker 컨테이너 존재 여부 확인
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                containers = result.stdout.strip().split("\n")
                return container_name in containers

            return False

        except Exception as e:
            logger.error(f"❌ 컨테이너 존재 확인 실패: {str(e)}")
            return False

    async def _check_docker_container_running(self, container_name: str) -> bool:
        """
        Docker 컨테이너 실행 상태 확인
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                running_containers = result.stdout.strip().split("\n")
                return container_name in running_containers

            return False

        except Exception as e:
            logger.error(f"❌ 컨테이너 실행 상태 확인 실패: {str(e)}")
            return False

    async def get_app_config_status(self, app_name: str) -> Dict[str, any]:
        """
        특정 앱 설정 파일의 상태 확인
        """
        try:
            config_file = f"{app_name}.conf"
            config_path = os.path.join(self.config_dir, config_file)

            # 기본 정보
            status = {
                "app_name": app_name,
                "config_file": config_file,
                "exists": os.path.exists(config_path),
                "valid": False,
                "container_exists": False,
                "container_running": False,
                "issues": [],
            }

            if not status["exists"]:
                status["issues"].append("설정 파일이 존재하지 않음")
                return status

            # 파일 검증
            validation_result = await self._validate_single_config(config_file)
            status["valid"] = validation_result["valid"]

            if not validation_result["valid"]:
                status["issues"].append(validation_result.get("reason", "알 수 없는 오류"))

            # 컨테이너 상태 확인
            container_name = f"streamlit_app_{app_name.split('-')[0]}"  # 앱 이름에서 컨테이너명 추정

            # 더 정확한 컨테이너 이름 찾기
            container_name = await self._find_container_name_for_app(app_name)

            if container_name:
                status["container_name"] = container_name
                status["container_exists"] = await self._check_docker_container_exists(container_name)
                status["container_running"] = await self._check_docker_container_running(container_name)

                if not status["container_exists"]:
                    status["issues"].append(f"컨테이너가 존재하지 않음: {container_name}")
                elif not status["container_running"]:
                    status["issues"].append(f"컨테이너가 실행 중이 아님: {container_name}")
            else:
                status["issues"].append("연결된 컨테이너를 찾을 수 없음")

            # 전체 상태 판정
            status["healthy"] = (
                status["exists"] and status["valid"] and status["container_exists"] and status["container_running"]
            )

            return status

        except Exception as e:
            logger.error(f"❌ 앱 설정 상태 확인 실패: {str(e)}")
            return {
                "app_name": app_name,
                "config_file": f"{app_name}.conf",
                "exists": False,
                "valid": False,
                "container_exists": False,
                "container_running": False,
                "healthy": False,
                "issues": [f"상태 확인 실패: {str(e)}"],
            }

    async def _find_container_name_for_app(self, app_name: str) -> str:
        """
        앱 이름으로부터 실제 컨테이너 이름 찾기 (데이터베이스 우선 조회)
        """
        try:
            # 1. 데이터베이스에서 컨테이너 이름 조회 (subdomain으로 검색)
            from database import get_db
            from models import App

            db = next(get_db())
            try:
                app = db.query(App).filter(App.subdomain == app_name).first()
                if app and app.container_name:
                    logger.info(f"✅ 데이터베이스에서 컨테이너 이름 찾음: {app.container_name}")
                    return app.container_name
            finally:
                db.close()

            # 2. 데이터베이스에서 찾지 못한 경우 기존 방식으로 fallback
            logger.info(f"⚠️ 데이터베이스에서 컨테이너 이름을 찾지 못함, Docker에서 직접 검색: {app_name}")

            # 가능한 컨테이너 이름 패턴들
            possible_names = [
                f"streamlit_app_{app_name}",
                f"streamlit-app-{app_name}",
                f"streamlit_app_{app_name.split('-')[0]}",
                f"streamlit-app-{app_name.split('-')[0]}",
                app_name,
                app_name.replace("-", "_"),
            ]

            # Docker에서 실제 컨테이너 목록 조회
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                existing_containers = result.stdout.strip().split("\n")

                # 정확히 일치하는 이름 찾기
                for name in possible_names:
                    if name in existing_containers:
                        logger.info(f"✅ Docker에서 정확히 일치하는 컨테이너 찾음: {name}")
                        return name

                # 부분 일치하는 이름 찾기
                for container in existing_containers:
                    if app_name in container or any(name in container for name in possible_names):
                        logger.info(f"✅ Docker에서 부분 일치하는 컨테이너 찾음: {container}")
                        return container

            logger.warning(f"⚠️ 컨테이너를 찾을 수 없음: {app_name}")
            return ""

        except Exception as e:
            logger.error(f"❌ 컨테이너 이름 찾기 실패: {str(e)}")
            return ""

    async def get_all_app_configs_status(self) -> Dict[str, any]:
        """
        모든 앱 설정 파일의 상태 확인
        """
        try:
            configs = await self.get_dynamic_configs()
            app_configs = configs.get("app_configs", [])

            statuses = []
            for app_name in app_configs:
                status = await self.get_app_config_status(app_name)
                statuses.append(status)

            # 통계 계산
            total = len(statuses)
            healthy = len([s for s in statuses if s.get("healthy", False)])
            with_issues = len([s for s in statuses if s.get("issues", [])])

            return {
                "success": True,
                "total_configs": total,
                "healthy_configs": healthy,
                "configs_with_issues": with_issues,
                "statuses": statuses,
            }

        except Exception as e:
            logger.error(f"❌ 전체 앱 설정 상태 확인 실패: {str(e)}")
            return {"success": False, "message": f"상태 확인 실패: {str(e)}"}

    async def remove_app_and_container(self, app_name: str) -> Dict[str, any]:
        """
        앱 설정 파일과 연결된 컨테이너를 함께 삭제
        """
        try:
            logger.info(f"🗑️ 앱 및 컨테이너 삭제 시작: {app_name}")

            # 먼저 앱 상태 확인
            status = await self.get_app_config_status(app_name)

            results = {
                "app_name": app_name,
                "config_removed": False,
                "container_stopped": False,
                "container_removed": False,
                "nginx_reloaded": False,
                "errors": [],
            }

            # 1. 설정 파일 삭제
            if status.get("exists", False):
                try:
                    config_path = os.path.join(self.config_dir, f"{app_name}.conf")
                    os.remove(config_path)
                    results["config_removed"] = True
                    logger.info(f"✅ 설정 파일 삭제 완료: {app_name}.conf")
                except Exception as e:
                    error_msg = f"설정 파일 삭제 실패: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(f"❌ {error_msg}")

            # 2. 컨테이너 중지 및 삭제
            container_name = status.get("container_name")
            if container_name:
                try:
                    # 컨테이너 중지
                    if status.get("container_running", False):
                        stop_result = subprocess.run(
                            ["docker", "stop", container_name], capture_output=True, text=True, timeout=30
                        )
                        if stop_result.returncode == 0:
                            results["container_stopped"] = True
                            logger.info(f"✅ 컨테이너 중지 완료: {container_name}")
                        else:
                            error_msg = f"컨테이너 중지 실패: {stop_result.stderr}"
                            results["errors"].append(error_msg)
                            logger.error(f"❌ {error_msg}")

                    # 컨테이너 삭제
                    if status.get("container_exists", False):
                        remove_result = subprocess.run(
                            ["docker", "rm", container_name], capture_output=True, text=True, timeout=30
                        )
                        if remove_result.returncode == 0:
                            results["container_removed"] = True
                            logger.info(f"✅ 컨테이너 삭제 완료: {container_name}")
                        else:
                            error_msg = f"컨테이너 삭제 실패: {remove_result.stderr}"
                            results["errors"].append(error_msg)
                            logger.error(f"❌ {error_msg}")

                except Exception as e:
                    error_msg = f"컨테이너 작업 실패: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(f"❌ {error_msg}")

            # 3. Nginx 리로드
            if results["config_removed"]:
                try:
                    nginx_reloaded = await self.reload_nginx()
                    results["nginx_reloaded"] = nginx_reloaded
                    if nginx_reloaded:
                        logger.info("✅ Nginx 리로드 완료")
                    else:
                        results["errors"].append("Nginx 리로드 실패")
                        logger.warning("⚠️ Nginx 리로드 실패")
                except Exception as e:
                    error_msg = f"Nginx 리로드 실패: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(f"❌ {error_msg}")

            # 결과 판정
            success = results["config_removed"] and len(results["errors"]) == 0

            return {
                "success": success,
                "message": f"앱 삭제 {'완료' if success else '부분 완료'}: {app_name}",
                "details": results,
            }

        except Exception as e:
            logger.error(f"❌ 앱 및 컨테이너 삭제 실패: {str(e)}")
            return {"success": False, "message": f"삭제 실패: {str(e)}"}

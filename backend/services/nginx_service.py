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
                logger.error(f"❌ Nginx 리로드 실패 (종료코드: {result.returncode})")
                logger.error(f"stderr: {result.stderr}")
                if result.stdout:
                    logger.error(f"stdout: {result.stdout}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("⏰ Nginx 리로드 시간 초과")
            return False
        except Exception as e:
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
            else:
                logger.error(f"❌ Nginx 리로드 실패 (종료코드: {result.returncode})")
                logger.error(f"stderr: {result.stderr}")
                if result.stdout:
                    logger.error(f"stdout: {result.stdout}")
                raise Exception(f"Nginx 리로드 실패: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("⏰ Nginx 리로드 시간 초과")
            raise Exception("Nginx 리로드 시간 초과")
        except Exception as e:
            logger.error(f"💥 Nginx 리로드 중 오류 발생: {str(e)}")
            raise

    async def test_nginx_config(self) -> bool:
        """Nginx 설정 파일 유효성 검사"""
        try:
            logger.info("🧪 Nginx 설정 유효성 검사 실행 중...")

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
                logger.error(f"❌ Nginx 설정 유효성 검사 실패 (종료코드: {result.returncode})")
                logger.error(f"stderr: {result.stderr}")
                if result.stdout:
                    logger.error(f"stdout: {result.stdout}")
                return False

        except Exception as e:
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
        """특정 설정 파일 삭제"""
        try:
            logger.info(f"🗑️ 특정 설정 파일 삭제 시작: {subdomain}")

            # 시스템 파일 보호
            if f"{subdomain}.conf" in self.system_configs:
                logger.warning(f"⚠️ 시스템 설정 파일은 삭제할 수 없습니다: {subdomain}.conf")
                return {
                    "success": False,
                    "message": f"시스템 설정 파일은 삭제할 수 없습니다: {subdomain}.conf",
                    "error": "시스템 파일 보호",
                }

            config_file = os.path.join(self.config_dir, f"{subdomain}.conf")

            if not os.path.exists(config_file):
                logger.warning(f"⚠️ 설정 파일이 존재하지 않습니다: {subdomain}.conf")
                return {
                    "success": False,
                    "message": f"설정 파일이 존재하지 않습니다: {subdomain}.conf",
                    "error": "파일 없음",
                }

            # 파일 삭제
            os.remove(config_file)
            logger.info(f"✅ 설정 파일 삭제 완료: {subdomain}.conf")

            # Nginx 설정 테스트 후 리로드
            logger.info("🔍 Nginx 설정 유효성 검사 중...")
            if await self.test_nginx_config():
                logger.info("✅ Nginx 설정 유효성 검사 통과")
                await self.reload_nginx()
                logger.info(f"🎉 {subdomain} 설정 파일 삭제 완료")
            else:
                logger.error("❌ Nginx 설정 유효성 검사 실패")
                return {
                    "success": False,
                    "message": "Nginx 설정 유효성 검사 실패",
                    "error": "설정 파일 삭제 후 Nginx 설정이 유효하지 않음",
                }

            return {
                "success": True,
                "message": f"{subdomain} 설정 파일이 성공적으로 삭제되었습니다.",
                "removed_file": f"{subdomain}.conf",
            }

        except Exception as e:
            logger.error(f"❌ 특정 설정 파일 삭제 실패: {str(e)}")
            return {"success": False, "message": f"{subdomain} 설정 파일 삭제 중 오류 발생", "error": str(e)}

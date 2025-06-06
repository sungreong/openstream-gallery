#!/usr/bin/env python3
"""
백엔드 API 테스트 스크립트
순서대로 API 기능을 테스트합니다.
"""

import requests
import json
import time
from typing import Dict, Any


class BackendAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.user_id = None
        self.app_id = None

    def print_response(self, response: requests.Response, test_name: str):
        """응답을 예쁘게 출력"""
        print(f"\n{'='*50}")
        print(f"테스트: {test_name}")
        print(f"URL: {response.url}")
        print(f"상태 코드: {response.status_code}")
        print(f"응답 시간: {response.elapsed.total_seconds():.2f}초")

        try:
            response_json = response.json()
            print(f"응답 내용:\n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
        except:
            print(f"응답 내용: {response.text}")
        print(f"{'='*50}")

        return response.status_code < 400

    def test_health_check(self):
        """헬스 체크 테스트"""
        try:
            response = self.session.get(f"{self.base_url}/")
            return self.print_response(response, "헬스 체크")
        except Exception as e:
            print(f"헬스 체크 실패: {e}")
            return False

    def test_api_health(self):
        """API 헬스 체크 테스트"""
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            return self.print_response(response, "API 헬스 체크")
        except Exception as e:
            print(f"API 헬스 체크 실패: {e}")
            return False

    def test_user_registration(self):
        """사용자 등록 테스트"""
        user_data = {"username": "testuser", "email": "test@example.com", "password": "testpassword123"}

        try:
            response = self.session.post(f"{self.base_url}/api/auth/register", json=user_data)
            success = self.print_response(response, "사용자 등록")

            if success and response.status_code == 200:
                data = response.json()
                self.user_id = data.get("id")

            return success
        except Exception as e:
            print(f"사용자 등록 실패: {e}")
            return False

    def test_user_login(self):
        """사용자 로그인 테스트"""
        login_data = {"username": "testuser", "password": "testpassword123"}

        try:
            response = self.session.post(f"{self.base_url}/api/auth/login", data=login_data)  # form data로 전송
            success = self.print_response(response, "사용자 로그인")

            if success and response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                # 세션에 토큰 추가
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})

            return success
        except Exception as e:
            print(f"사용자 로그인 실패: {e}")
            return False

    def test_get_current_user(self):
        """현재 사용자 정보 조회 테스트"""
        try:
            response = self.session.get(f"{self.base_url}/api/auth/me")
            return self.print_response(response, "현재 사용자 정보 조회")
        except Exception as e:
            print(f"사용자 정보 조회 실패: {e}")
            return False

    def test_create_app(self):
        """앱 생성 테스트"""
        app_data = {
            "name": "ZoneCleaner Test App",
            "description": "GitHub에서 가져온 테스트 앱",
            "git_url": "https://github.com/sungreong/ZoneCleaner",
            "branch": "main",
            "main_file": "app.py",
        }

        try:
            response = self.session.post(f"{self.base_url}/api/apps/", json=app_data)
            success = self.print_response(response, "앱 생성")

            if success and response.status_code == 200:
                data = response.json()
                self.app_id = data.get("id")

            return success
        except Exception as e:
            print(f"앱 생성 실패: {e}")
            return False

    def test_get_apps(self):
        """앱 목록 조회 테스트"""
        try:
            response = self.session.get(f"{self.base_url}/api/apps/")
            return self.print_response(response, "앱 목록 조회")
        except Exception as e:
            print(f"앱 목록 조회 실패: {e}")
            return False

    def test_deploy_app(self):
        """앱 배포 테스트"""
        if not self.app_id:
            print("앱 ID가 없어서 배포 테스트를 건너뜁니다.")
            return False

        deploy_data = {"git_url": "https://github.com/sungreong/ZoneCleaner", "branch": "main", "main_file": "app.py"}

        try:
            response = self.session.post(f"{self.base_url}/api/apps/{self.app_id}/deploy", json=deploy_data)
            success = self.print_response(response, "앱 배포")

            if success:
                print("배포가 시작되었습니다. 잠시 기다린 후 상태를 확인합니다...")
                time.sleep(5)  # 배포 시간 대기

            return success
        except Exception as e:
            print(f"앱 배포 실패: {e}")
            return False

    def test_get_app_detail(self):
        """앱 상세 정보 조회 테스트"""
        if not self.app_id:
            print("앱 ID가 없어서 상세 정보 조회를 건너뜁니다.")
            return False

        try:
            response = self.session.get(f"{self.base_url}/api/apps/{self.app_id}")
            return self.print_response(response, "앱 상세 정보 조회")
        except Exception as e:
            print(f"앱 상세 정보 조회 실패: {e}")
            return False

    def test_get_app_logs(self):
        """앱 로그 조회 테스트"""
        if not self.app_id:
            print("앱 ID가 없어서 로그 조회를 건너뜁니다.")
            return False

        try:
            response = self.session.get(f"{self.base_url}/api/apps/{self.app_id}/logs")
            return self.print_response(response, "앱 로그 조회")
        except Exception as e:
            print(f"앱 로그 조회 실패: {e}")
            return False

    def test_stop_app(self):
        """앱 중지 테스트"""
        if not self.app_id:
            print("앱 ID가 없어서 앱 중지를 건너뜁니다.")
            return False

        try:
            response = self.session.post(f"{self.base_url}/api/apps/{self.app_id}/stop")
            return self.print_response(response, "앱 중지")
        except Exception as e:
            print(f"앱 중지 실패: {e}")
            return False

    def run_all_tests(self):
        """모든 테스트를 순서대로 실행"""
        print("🚀 백엔드 API 테스트를 시작합니다...")

        tests = [
            ("헬스 체크", self.test_health_check),
            ("API 헬스 체크", self.test_api_health),
            ("사용자 등록", self.test_user_registration),
            ("사용자 로그인", self.test_user_login),
            ("현재 사용자 정보 조회", self.test_get_current_user),
            ("앱 생성", self.test_create_app),
            ("앱 목록 조회", self.test_get_apps),
            ("앱 배포", self.test_deploy_app),
            ("앱 상세 정보 조회", self.test_get_app_detail),
            ("앱 로그 조회", self.test_get_app_logs),
            ("앱 중지", self.test_stop_app),
        ]

        results = []
        for test_name, test_func in tests:
            print(f"\n🔍 {test_name} 테스트 실행 중...")
            try:
                success = test_func()
                results.append((test_name, success))
                if not success:
                    print(f"❌ {test_name} 테스트 실패")
                else:
                    print(f"✅ {test_name} 테스트 성공")
            except Exception as e:
                print(f"❌ {test_name} 테스트 중 예외 발생: {e}")
                results.append((test_name, False))

        # 결과 요약
        print(f"\n{'='*60}")
        print("📊 테스트 결과 요약")
        print(f"{'='*60}")

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for test_name, success in results:
            status = "✅ 성공" if success else "❌ 실패"
            print(f"{test_name}: {status}")

        print(f"\n총 {total}개 테스트 중 {passed}개 성공 ({passed/total*100:.1f}%)")

        if passed == total:
            print("🎉 모든 테스트가 성공했습니다!")
        else:
            print(f"⚠️  {total - passed}개의 테스트가 실패했습니다.")


if __name__ == "__main__":
    # 사용법
    print("백엔드 API 테스트 도구")
    print("사용법: python test_backend_api.py")
    print("백엔드 서버가 http://localhost:8000에서 실행 중이어야 합니다.\n")

    tester = BackendAPITester()
    tester.run_all_tests()

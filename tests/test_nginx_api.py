#!/usr/bin/env python3
"""
Nginx API 테스트 스크립트
"""

import requests
import json
import sys

# API 기본 URL
BASE_URL = "http://localhost:8000/api/nginx"


def test_get_dynamic_configs():
    """Dynamic 폴더 내 모든 설정 파일 정보 조회 테스트"""
    print("🔍 Dynamic 설정 파일 조회 테스트...")

    try:
        response = requests.get(f"{BASE_URL}/dynamic")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 성공!")
            print(f"📋 응답 데이터:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 실패: {response.text}")

    except Exception as e:
        print(f"❌ 오류: {str(e)}")

    print("-" * 50)


def test_get_app_configs():
    """앱 설정 목록 조회 테스트"""
    print("🔍 앱 설정 목록 조회 테스트...")

    try:
        response = requests.get(f"{BASE_URL}/dynamic/apps")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 성공!")
            print(f"📋 응답 데이터:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 실패: {response.text}")

    except Exception as e:
        print(f"❌ 오류: {str(e)}")

    print("-" * 50)


def test_nginx_config_test():
    """Nginx 설정 유효성 검사 테스트"""
    print("🧪 Nginx 설정 유효성 검사 테스트...")

    try:
        response = requests.get(f"{BASE_URL}/test")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 성공!")
            print(f"📋 응답 데이터:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 실패: {response.text}")

    except Exception as e:
        print(f"❌ 오류: {str(e)}")

    print("-" * 50)


def test_cleanup_configs():
    """설정 파일 정리 테스트"""
    print("🧹 설정 파일 정리 테스트...")

    # 예시 활성 앱 목록 (실제 환경에 맞게 수정)
    active_apps = ["llm-tokenizer-a03a41a3"]  # 실제 존재하는 앱 이름으로 수정

    try:
        response = requests.post(f"{BASE_URL}/cleanup", json={"active_apps": active_apps})
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 성공!")
            print(f"📋 응답 데이터:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 실패: {response.text}")

    except Exception as e:
        print(f"❌ 오류: {str(e)}")

    print("-" * 50)


def test_auto_cleanup():
    """자동 설정 파일 정리 테스트"""
    print("🤖 자동 설정 파일 정리 테스트...")

    try:
        response = requests.post(f"{BASE_URL}/cleanup/auto")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 성공!")
            print(f"📋 응답 데이터:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 실패: {response.text}")

    except Exception as e:
        print(f"❌ 오류: {str(e)}")

    print("-" * 50)


def test_remove_specific_config():
    """특정 설정 파일 삭제 테스트"""
    print("🗑️ 특정 설정 파일 삭제 테스트...")

    # 테스트용 서브도메인 (실제 존재하지 않는 것으로 테스트)
    test_subdomain = "test-app-to-delete"

    try:
        response = requests.delete(f"{BASE_URL}/config/{test_subdomain}")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 성공!")
            print(f"📋 응답 데이터:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 실패 (예상됨): {response.text}")

    except Exception as e:
        print(f"❌ 오류: {str(e)}")

    print("-" * 50)


def main():
    """메인 테스트 함수"""
    print("🚀 Nginx API 테스트 시작")
    print("=" * 50)

    # 기본 조회 테스트
    test_get_dynamic_configs()
    test_get_app_configs()
    test_nginx_config_test()

    # 관리 기능 테스트 (주의: 실제 설정에 영향을 줄 수 있음)
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        print("⚠️ 전체 테스트 모드 (실제 설정 변경 포함)")
        test_cleanup_configs()
        test_auto_cleanup()
        test_remove_specific_config()
    else:
        print("💡 전체 테스트를 원하면 --full 옵션을 사용하세요")
        print("   (주의: 실제 Nginx 설정이 변경될 수 있습니다)")

    print("=" * 50)
    print("🎉 테스트 완료")


if __name__ == "__main__":
    main()

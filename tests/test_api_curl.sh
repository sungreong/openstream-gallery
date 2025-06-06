#!/bin/bash

# 백엔드 API 테스트 - cURL 버전
# 사용법: ./test_api_curl.sh

BASE_URL="http://localhost:8000"
TOKEN=""
APP_ID=""

echo "🚀 백엔드 API 테스트 시작 (cURL 버전)"
echo "=================================="

# 1. 헬스 체크
echo -e "\n1️⃣ 헬스 체크"
curl -X GET "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s

# 2. API 헬스 체크
echo -e "\n2️⃣ API 헬스 체크"
curl -X GET "$BASE_URL/api/health" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s

# 3. 사용자 등록
echo -e "\n3️⃣ 사용자 등록"
curl -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123"
  }' \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s

# 4. 사용자 로그인
echo -e "\n4️⃣ 사용자 로그인"
LOGIN_RESPONSE=$(curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword123" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$LOGIN_RESPONSE"

# 토큰 추출 (jq가 설치되어 있는 경우)
if command -v jq &> /dev/null; then
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')
    echo "추출된 토큰: ${TOKEN:0:20}..."
fi

# 5. 현재 사용자 정보 조회
echo -e "\n5️⃣ 현재 사용자 정보 조회"
if [ -n "$TOKEN" ]; then
    curl -X GET "$BASE_URL/api/auth/me" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
      -s
else
    echo "토큰이 없어서 건너뜁니다."
fi

# 6. 앱 생성
echo -e "\n6️⃣ 앱 생성"
if [ -n "$TOKEN" ]; then
    APP_RESPONSE=$(curl -X POST "$BASE_URL/api/apps/" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "ZoneCleaner Test App",
        "description": "GitHub에서 가져온 테스트 앱",
        "git_url": "https://github.com/sungreong/ZoneCleaner",
        "branch": "main",
        "main_file": "app.py"
      }' \
      -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
      -s)
    
    echo "$APP_RESPONSE"
    
    # 앱 ID 추출
    if command -v jq &> /dev/null; then
        APP_ID=$(echo "$APP_RESPONSE" | jq -r '.id // empty')
        echo "생성된 앱 ID: $APP_ID"
    fi
else
    echo "토큰이 없어서 건너뜁니다."
fi

# 7. 앱 목록 조회
echo -e "\n7️⃣ 앱 목록 조회"
if [ -n "$TOKEN" ]; then
    curl -X GET "$BASE_URL/api/apps/" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
      -s
else
    echo "토큰이 없어서 건너뜁니다."
fi

# 8. 앱 배포
echo -e "\n8️⃣ 앱 배포"
if [ -n "$TOKEN" ] && [ -n "$APP_ID" ]; then
    curl -X POST "$BASE_URL/api/apps/$APP_ID/deploy" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "git_url": "https://github.com/sungreong/ZoneCleaner",
        "branch": "main",
        "main_file": "app.py"
      }' \
      -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
      -s
    
    echo "배포 시작됨. 5초 대기..."
    sleep 5
else
    echo "토큰 또는 앱 ID가 없어서 건너뜁니다."
fi

# 9. 앱 상세 정보 조회
echo -e "\n9️⃣ 앱 상세 정보 조회"
if [ -n "$TOKEN" ] && [ -n "$APP_ID" ]; then
    curl -X GET "$BASE_URL/api/apps/$APP_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
      -s
else
    echo "토큰 또는 앱 ID가 없어서 건너뜁니다."
fi

# 10. 앱 로그 조회
echo -e "\n🔟 앱 로그 조회"
if [ -n "$TOKEN" ] && [ -n "$APP_ID" ]; then
    curl -X GET "$BASE_URL/api/apps/$APP_ID/logs" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
      -s
else
    echo "토큰 또는 앱 ID가 없어서 건너뜁니다."
fi

echo -e "\n✅ 모든 테스트 완료!"
echo "==================================" 